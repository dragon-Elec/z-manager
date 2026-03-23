# z-manager/core/device_management/configurator.py
"""
The Orchestrator.
Manages configuration lifecycle, persistence (zram-generator.conf), and service coordination.
Bridges the gap between the persistent plan and the live kernel state.
"""
from __future__ import annotations
import logging
from typing import Dict, Any, Optional, List, Tuple

from core.utils.common import (
    run,
    SystemCommandError,
    ValidationError,
    NotBlockDeviceError,
)
from core.utils.block import (
    is_block_device,
    check_device_safety,
)
from core.utils.io import (
    pkexec_write,
    atomic_write_to_file,
)
from core.utils.privilege import (
    pkexec_daemon_reload,
    pkexec_systemctl,
    systemd_daemon_reload,
    systemd_try_restart,
    systemd_restart,
)
from core.config import CONFIG_PATH, read_zram_config
from core.config_writer import (
    update_zram_config, 
    update_global_config, 
    remove_device_from_config
)
from .types import (
    UnitResult, 
    PersistResult, 
    OrchestrationResult, 
    Action, 
    WritebackResult
)
from .prober import is_device_active, read_params_best_effort, _get_sysfs
from .provisioner import reconfigure_device_sysfs

_LOGGER = logging.getLogger(__name__)

# --- Configuration Actions ---

def apply_device_config(device_name: str, config_updates: Dict[str, Any], restart_service: bool = False, reload_daemon: bool = True) -> UnitResult:
    """Orchestrates writing a config to disk and optionally applying it via systemd."""
    try:
        ok, err, rendered = update_zram_config(device_name, config_updates)
        if not ok: return UnitResult(False, f"Config generation failed: {err}")

        ok_write, err_write = pkexec_write(CONFIG_PATH, rendered)
        if not ok_write: return UnitResult(False, f"Write failed: {err_write}")

        if reload_daemon:
            ok_reload, err_reload = pkexec_daemon_reload()
            if not ok_reload: return UnitResult(False, f"Daemon reload failed: {err_reload}")

        if restart_service:
            restart_res = restart_unit_for_device(device_name)
            if not restart_res.success:
                return UnitResult(False, f"Service restart failed: {restart_res.message}")

            return UnitResult(True, "Configuration applied successfully.")
        
        return UnitResult(True, "Configuration saved. Restart required to apply.")
    except Exception as e:
        return UnitResult(False, str(e))


def apply_global_config(updates: Dict[str, Any]) -> UnitResult:
    """Applies global configuration updates to [zram-generator] section."""
    try:
        ok, err, rendered = update_global_config(updates)
        if not ok: return UnitResult(False, f"Config generation failed: {err}")
            
        ok_w, err_w = atomic_write_to_file(CONFIG_PATH, rendered, backup=True)
        if not ok_w: return UnitResult(False, f"Write failed: {err_w}")
            
        systemd_daemon_reload()
        return UnitResult(True, "Global configuration updated.")
    except Exception as e:
        return UnitResult(False, str(e))


def remove_device_config(device_name: str, apply_now: bool = True) -> UnitResult:
    """Removes a device configuration and optionally stops its service."""
    try:
        if apply_now:
            svc = f"systemd-zram-setup@{device_name}.service"
            pkexec_systemctl("stop", svc)  # Best effort
        
        ok, err, rendered = remove_device_from_config(device_name)
        if not ok: return UnitResult(False, f"Config update failed: {err}")
            
        ok_w, err_w = pkexec_write(CONFIG_PATH, rendered)
        if not ok_w: return UnitResult(False, f"Write failed: {err_w}")
             
        if apply_now:
            pkexec_daemon_reload()
        
        return UnitResult(True, f"Device {device_name} removed.")
    except Exception as e:
        return UnitResult(False, str(e))


# --- Live Writeback Actions ---

def set_writeback(device_name: str, writeback_device: str, force: bool = False, create_if_missing: bool = True, default_size: str = "1G", new_size: Optional[str] = None) -> WritebackResult:
    """Configures writeback for an existing or new zram device live."""
    if not is_block_device(writeback_device):
        raise NotBlockDeviceError(f"{writeback_device} is not a block device")

    is_safe, reason = check_device_safety(writeback_device)
    if not is_safe:
        raise ValidationError(f"Writeback device safety check failed: {reason}")

    active = is_device_active(device_name)
    if active and not force:
        raise ValidationError(f"{device_name} is active; use force=True to reset and apply writeback")

    dev_path = f"/dev/{device_name}"
    if not create_if_missing and not is_block_device(dev_path):
        raise NotBlockDeviceError(f"Device {device_name} does not exist; set create_if_missing=True to auto-create")

    if active:
        run(["swapoff", f"/dev/{device_name}"], check=False)
        run(["umount", f"/dev/{device_name}"], check=False)

    params = read_params_best_effort(device_name, default_size)
    size = new_size or params.get("disksize") or default_size
    algorithm = params.get("algorithm")
    streams = params.get("streams")
    
    try:
        reconfigure_device_sysfs(device_name, size, algorithm, streams, writeback_device)
        return WritebackResult(True, device_name, "set-writeback", {
            "writeback_device": writeback_device, 
            "preserved": {"size": size, "algorithm": algorithm, "streams": streams}
        })
    except Exception as e:
        return WritebackResult(False, device_name, "set-writeback", {"error": str(e)})


def clear_writeback(device_name: str, force: bool = False, create_if_missing: bool = True, default_size: str = "1G", new_size: Optional[str] = None) -> WritebackResult:
    """Clears writeback by resetting and recreating the device without a backing store."""
    active = is_device_active(device_name)
    if active and not force:
        raise ValidationError(f"{device_name} is active; use force=True to reset and clear writeback")

    dev_path = f"/dev/{device_name}"
    if not create_if_missing and not is_block_device(dev_path):
        raise NotBlockDeviceError(f"Device {device_name} does not exist; set create_if_missing=True to auto-create")

    if active:
        run(["swapoff", f"/dev/{device_name}"], check=False)
        run(["umount", f"/dev/{device_name}"], check=False)

    params = read_params_best_effort(device_name, default_size)
    size = new_size or params.get("disksize") or default_size
    algorithm = params.get("algorithm")
    streams = params.get("streams")

    try:
        reconfigure_device_sysfs(device_name, size, algorithm, streams, None)
        return WritebackResult(True, device_name, "clear-writeback", {
            "preserved": {"size": size, "algorithm": algorithm, "streams": streams}
        })
    except Exception as e:
        return WritebackResult(False, device_name, "clear-writeback", {"error": str(e)})


def persist_writeback(device_name: str, writeback_device: Optional[str], apply_now: bool = True) -> PersistResult:
    """Persists writeback-device configuration for a ZRAM device."""
    try:
        cfg = read_zram_config()
        updates: Dict[str, Any] = {}
        
        if device_name not in cfg or 'zram-size' not in cfg[device_name]:
            updates['zram-size'] = '1G'

        if writeback_device:
            if not is_block_device(writeback_device):
                raise NotBlockDeviceError(f"{writeback_device} not a block device")
            updates["writeback-device"] = writeback_device
        else:
            updates["writeback-device"] = None

        ok, err, rendered = update_zram_config(device_name, updates)
        if not ok: raise ValidationError(err)

        write_ok, write_err = atomic_write_to_file(CONFIG_PATH, rendered, backup=True)
        if not write_ok: raise ValidationError(write_err)

        applied = False
        msg = "Persisted"
        if apply_now:
            systemd_daemon_reload()
            ok_restart, restart_err = systemd_try_restart(f"systemd-zram-setup@{device_name}.service")
            applied = ok_restart
            if applied:
                msg = "Persisted and applied"
            else:
                msg = f"Persisted, but restart failed: {restart_err or ''}".strip()

        return PersistResult(True, device_name, applied, msg)
    except Exception as e:
        return PersistResult(False, device_name, False, str(e))


# --- Service & Orchestration Logic ---

def restart_unit_for_device(device_name: str) -> UnitResult:
    """Restarts the systemd-zram-setup@zramN service."""
    svc = f"systemd-zram-setup@{device_name}.service"
    try:
        systemd_restart(svc)
        return UnitResult(True, "restarted", svc)
    except SystemCommandError as e:
        return UnitResult(False, str(e), svc)


def restart_device_unit(device_name: str, mode: str = "try") -> UnitResult:
    """Robust restart with different policies (try, force, none)."""
    svc = f"systemd-zram-setup@{device_name}.service"
    match mode:
        case "none": return UnitResult(True, "no-op", svc)
        case "try":
            ok, err = systemd_try_restart(svc)
            return UnitResult(ok, "restarted" if ok else (err or "restart failed"), svc)
        case "force":
            try:
                systemd_restart(svc)
                return UnitResult(True, "restarted", svc)
            except SystemCommandError as e:
                return UnitResult(False, str(e), svc)
        case _: return UnitResult(False, f"Unknown restart mode: {mode}", svc)


def ensure_writeback_state(device_name: str, desired_writeback: Optional[str], force: bool = False, restart_mode: str = "try") -> OrchestrationResult:
    """
    Idempotently ensures the live device matches the desired writeback state.
    - If device is active and change is needed, requires force=True.
    - Preserves current size/algorithm/streams best-effort.
    """
    actions: List[Action] = []
    
    # 1. Validate desired target if provided
    if desired_writeback:
        if not is_block_device(desired_writeback):
            actions.append(Action("validate-writeback-device", False, f"{desired_writeback} is not a block device"))
            return OrchestrationResult(False, device_name, desired_writeback, actions, "validation failed")
        
        safe, reason = check_device_safety(desired_writeback)
        if not safe:
            actions.append(Action("safety-check", False, reason))
            return OrchestrationResult(False, device_name, desired_writeback, actions, "safety check failed")

    dev_path = f"/dev/{device_name}"
    if not is_block_device(dev_path) and desired_writeback is None:
        actions.append(Action("noop-no-device", True, "Device does not exist and no writeback desired"))
        unit_res = restart_device_unit(device_name, mode="none")
        actions.append(Action("restart(none)", unit_res.success, unit_res.message))
        return OrchestrationResult(True, device_name, desired_writeback, actions, "no changes required")

    # 2. Get live state and handle "none" normalization
    current = _get_sysfs(device_name, "backing_dev") or ""
    
    def state_is_correct(curr: str, desired: Optional[str]) -> bool:
        if desired is None:
            return not bool(curr) or curr == "none"
        return curr == desired

    # 3. Check if state is already correct
    if state_is_correct(current, desired_writeback):
        actions.append(Action("noop-already-desired", True, f"backing_dev already '{current or 'None'}'"))
        unit_res = restart_device_unit(device_name, mode=restart_mode)
        actions.append(Action(f"restart({restart_mode})", unit_res.success, unit_res.message))
        return OrchestrationResult(all(a.success for a in actions), device_name, desired_writeback, actions, "no changes required")

    # 4. Apply the change
    active = is_device_active(device_name)
    if active and not force:
        actions.append(Action("precondition", False, f"{device_name} is active; use force to recreate"))
        return OrchestrationResult(False, device_name, desired_writeback, actions, "failed to apply live changes")

    params = read_params_best_effort(device_name)
    try:
        reconfigure_device_sysfs(device_name, params["disksize"], params["algorithm"], params["streams"], desired_writeback)
        actions.append(Action("reconfigure", True, "reconfigured via sysfs"))
        
        unit_res = restart_device_unit(device_name, mode=restart_mode)
        actions.append(Action(f"restart({restart_mode})", unit_res.success, unit_res.message))
        return OrchestrationResult(all(a.success for a in actions), device_name, desired_writeback, actions, "applied")
    except Exception as e:
        actions.append(Action("reconfigure", False, str(e)))
        return OrchestrationResult(False, device_name, desired_writeback, actions, "failed to apply live changes")
