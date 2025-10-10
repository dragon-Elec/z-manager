# zman/core/zdevice_ctl.py

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

from core.config import CONFIG_PATH
from core.os_utils import (
    run,
    SystemCommandError,
    ValidationError,
    NotBlockDeviceError,
    is_block_device,
    read_file,
    sysfs_write,
    zram_sysfs_dir,
    sysfs_reset_device,
    parse_zramctl_table,
    systemd_daemon_reload,
    systemd_try_restart,
    systemd_restart,
    atomic_write_to_file,
)


# ============ Domain Models ============

@dataclass(frozen=True)
class DeviceInfo:
    name: str
    disksize: Optional[str] = None
    data_size: Optional[str] = None
    compr_size: Optional[str] = None
    ratio: Optional[str] = None
    streams: Optional[int] = None
    algorithm: Optional[str] = None


@dataclass(frozen=True)
class WritebackStatus:
    device: str
    backing_dev: Optional[str]
    mem_used_total: Optional[str]
    orig_data_size: Optional[str]
    compr_data_size: Optional[str]
    num_writeback: Optional[str]
    writeback_failed: Optional[str]


@dataclass(frozen=True)
class UnitResult:
    success: bool
    message: str = ""
    service: Optional[str] = None


@dataclass(frozen=True)
class WritebackResult:
    success: bool
    device: str
    action: str
    details: Dict[str, Any]


@dataclass(frozen=True)
class PersistResult:
    success: bool
    device: str
    applied: bool
    message: str = ""

@dataclass(frozen=True)
class Action:
    name: str
    success: bool
    message: str = ""

@dataclass(frozen=True)
class OrchestrationResult:
    success: bool
    device: str
    desired_writeback: Optional[str]
    actions: List[Action]
    message: str = ""


# ============ Internal helpers ============


def _ensure_device_exists(device_name: str) -> None:
    """
    Ensures the /dev/zramN node and its /sys/block/zramN counterpart exist.
    Uses `zramctl --find` as it's the most reliable user-space tool for
    ensuring the /dev node is also created.
    Raises RuntimeError if the specific device cannot be created.
    """
    dev_path = f"/dev/{device_name}"
    if os.path.exists(dev_path):
        return  # Device already exists, nothing to do.

    try:
        # 1. Ensure the kernel module is loaded.
        run(["modprobe", "zram"], check=True)

        # 2. Use `zramctl --find`. This is non-deterministic and will create the
        #    *next available* device. In a clean state where `device_name` is missing,
        #    this should create it.
        run(["zramctl", "--find"], check=True)

        # 3. CRITICAL VERIFICATION STEP:
        #    After asking for a new device, we must check if the *specific one*
        #    we wanted was actually created.
        if not os.path.exists(dev_path):
            raise RuntimeError(
                f"'{device_name}' was not created. `zramctl --find` may have "
                f"created a different device (e.g., zram1) if '{device_name}' "
                "was unavailable or already in a transient state."
            )

    except (SystemCommandError, IOError, OSError) as e:
        raise RuntimeError(f"Failed to ensure existence of device '{device_name}': {e}")


def _reconfigure_device_sysfs(device_name: str, size: str, algorithm: Optional[str], streams: Optional[int], backing_dev: Optional[str]) -> None:
    """
    Single source of truth for reconfiguring a zram device using sysfs.
    This function is designed to be robust and handle various system states.
    Raises ValidationError or RuntimeError on failure.
    """
    # --- Use the robust helper to ensure the device exists ---
    _ensure_device_exists(device_name)

    dev_path = f"/dev/{device_name}"
    sysfs_path = zram_sysfs_dir(device_name)

    # Now we can safely assume the device and sysfs path exist.
    if not os.path.isdir(sysfs_path):
        raise ValidationError(f"Device '{device_name}' exists but its sysfs directory '{sysfs_path}' does not. Kernel state is inconsistent.")

    # Check if the device is already configured. A non-zero disksize indicates it is.
    # The 'reset' is only necessary for RE-configuration, not initial configuration.
    current_size = read_file(f"{sysfs_path}/disksize")
    if current_size is None:
        # This is a weird state - the directory exists but the disksize file doesn't.
        raise ValidationError(f"Cannot read disksize for '{device_name}'. The device may be in a bad state.")

    if current_size != "0":
        # It's an active or configured device, so it must be reset first.
        sysfs_reset_device(dev_path)

    # --- From here, we know the device disksize is 0 ---

    # --- Improvement 2: Feature Detection for Writeback ---
    if backing_dev:
        backing_dev_path = f"{sysfs_path}/backing_dev"
        if not os.path.exists(backing_dev_path):
            raise NotImplementedError(
                f"Cannot set writeback device: your kernel does not support it "
                f"(sysfs node '{backing_dev_path}' is missing)."
            )
        try:
            sysfs_write(backing_dev_path, backing_dev)
        except (IOError, OSError) as e:
            raise ValidationError(f"Failed to set backing_dev '{backing_dev}': {e}")

    # 3. Set algorithm
    if algorithm:
        try:
            sysfs_write(f"{sysfs_path}/comp_algorithm", algorithm)
        except (IOError, OSError) as e:
            raise ValidationError(f"Failed to set comp_algorithm '{algorithm}': {e}")

    # 4. Set streams
    if streams:
        try:
            sysfs_write(f"{sysfs_path}/max_comp_streams", str(streams))
        except (IOError, OSError) as e:
            raise ValidationError(f"Failed to set max_comp_streams '{streams}': {e}")

    # 5. Set size. This must be the final step.
    try:
        sysfs_write(f"{sysfs_path}/disksize", size)
    except (IOError, OSError) as e:
        raise ValidationError(f"Failed to set disksize '{size}': {e}")


def _get_sysfs(device_name: str, node: str) -> Optional[str]:
    base = zram_sysfs_dir(device_name)
    return read_file(f"{base}/{node}")


def _device_active(device_name: str) -> bool:
    # A device is considered "active" if it's in /proc/swaps or mounted
    # Check swaps:
    try:
        swaps = run(["cat", "/proc/swaps"]).out
        if f"/dev/{device_name}" in swaps:
            return True
    except (SystemCommandError, OSError):
        pass
    # Mount check:
    try:
        mounts = run(["mount"]).out
        if f"/dev/{device_name}" in mounts:
            return True
    except (SystemCommandError, OSError):
        pass
    return False


def is_device_active(device_name: str) -> bool:
    """Public API to check if /dev/zramN is active (swap or mounted)."""
    return _device_active(device_name)


def _read_params_best_effort(device_name: str, default_size: str = "1G") -> Dict[str, Any]:
    """
    Best-effort read of current params to preserve when recreating:
    - disksize (from zramctl table)
    - algorithm (from zramctl table)
    - streams (from zramctl table)
    Returns default_size if no device found.
    """
    info_list = parse_zramctl_table()
    for info in info_list:
        if info.get("name") == device_name:
            return {
                "disksize": info.get("disksize"),
                "algorithm": info.get("algorithm"),
                "streams": info.get("streams"),
            }
    return {"disksize": default_size, "algorithm": None, "streams": None}


# ============ Public API ============

def list_devices() -> List[DeviceInfo]:
    infos = parse_zramctl_table()
    out: List[DeviceInfo] = []
    for d in infos:
        out.append(DeviceInfo(
            name=d.get("name", "unknown"),
            disksize=d.get("disksize"),
            data_size=d.get("data-size"),
            compr_size=d.get("compr-size"),
            ratio=d.get("ratio"),
            streams=d.get("streams"),
            algorithm=d.get("algorithm"),
        ))
    return out


def get_writeback_status(device_name: str) -> WritebackStatus:
    dev_path = f"/dev/{device_name}"
    if not is_block_device(dev_path):
        raise NotBlockDeviceError(f"zram device {device_name} does not exist")

    return WritebackStatus(
        device=device_name,
        backing_dev=_get_sysfs(device_name, "backing_dev"),
        mem_used_total=_get_sysfs(device_name, "mem_used_total"),
        orig_data_size=_get_sysfs(device_name, "orig_data_size"),
        compr_data_size=_get_sysfs(device_name, "compr_data_size"),
        num_writeback=_get_sysfs(device_name, "num_writeback"),
        writeback_failed=_get_sysfs(device_name, "writeback_failed"),
    )

def set_writeback(device_name: str, writeback_device: str, force: bool = False, create_if_missing: bool = True, default_size: str = "1G", new_size: Optional[str] = None) -> WritebackResult:
    """
    Configure writeback for an existing zram device, or create if missing and create_if_missing=True.
    If active, requires force=True to reset/recreate. Preserves current size/algorithm/streams best-effort;
    uses default_size if creating new.
    """
    if not is_block_device(writeback_device):
        raise NotBlockDeviceError(f"{writeback_device} is not a block device")

    active = _device_active(device_name)
    if active and not force:
        raise ValidationError(f"{device_name} is active; use force=True to reset and apply writeback")

    dev_path = f"/dev/{device_name}"
    if not create_if_missing and not is_block_device(dev_path):
        raise NotBlockDeviceError(f"Device {device_name} does not exist; set create_if_missing=True to auto-create")

    if active:
        # Best-effort deactivation for force mode
        run(["swapoff", f"/dev/{device_name}"], check=False)
        run(["umount", f"/dev/{device_name}"], check=False)

    params = _read_params_best_effort(device_name, default_size)
    size = new_size or params.get("disksize") or default_size
    algorithm = params.get("algorithm")
    streams = params.get("streams")

    try:
        _reconfigure_device_sysfs(device_name, size, algorithm, streams, writeback_device)
    except (ValidationError, RuntimeError) as e:
        return WritebackResult(success=False, device=device_name, action="set-writeback", details={"error": str(e)})

    return WritebackResult(
        success=True,
        device=device_name,
        action="set-writeback",
        details={"writeback_device": writeback_device, "preserved": {"size": size, "algorithm": algorithm, "streams": params.get("streams")}},
    )


def clear_writeback(device_name: str, force: bool = False, create_if_missing: bool = True, default_size: str = "1G", new_size: Optional[str] = None) -> WritebackResult:
    """
    Clear writeback by resetting and recreating device without --writeback-device.
    Creates if missing and create_if_missing=True; uses default_size if creating new.
    """
    active = _device_active(device_name)
    if active and not force:
        raise ValidationError(f"{device_name} is active; use force=True to reset and clear writeback")

    dev_path = f"/dev/{device_name}"
    if not create_if_missing and not is_block_device(dev_path):
        raise NotBlockDeviceError(f"Device {device_name} does not exist; set create_if_missing=True to auto-create")

    if active:
        # Best-effort deactivation for force mode
        run(["swapoff", f"/dev/{device_name}"], check=False)
        run(["umount", f"/dev/{device_name}"], check=False)

    params = _read_params_best_effort(device_name, default_size)
    size = new_size or params.get("disksize") or default_size
    algorithm = params.get("algorithm")
    streams = params.get("streams")

    try:
        _reconfigure_device_sysfs(device_name, size, algorithm, streams, backing_dev=None)
    except (ValidationError, RuntimeError) as e:
        return WritebackResult(success=False, device=device_name, action="clear-writeback", details={"error": str(e)})

    return WritebackResult(
        success=True,
        device=device_name,
        action="clear-writeback",
        details={"preserved": {"size": size, "algorithm": algorithm, "streams": params.get("streams")}},
    )


def restart_unit_for_device(device_name: str) -> UnitResult:
    """
    Restart the systemd unit systemd-zram-setup@zramN.service for the device.
    """
    dev_path = f"/dev/{device_name}"
    if not is_block_device(dev_path):
        return UnitResult(success=False, message=f"Device {device_name} does not exist", service=None)
    svc = f"systemd-zram-setup@{device_name}.service"
    try:
        systemd_restart(svc)
        return UnitResult(success=True, message="restarted", service=svc)
    except SystemCommandError as e:
        return UnitResult(success=False, message=str(e), service=svc)


def reset_device(device_name: str, confirm: bool = False) -> UnitResult:
    """
    Reset a zram device using the safe sysfs method, which preserves the device node.
    confirm parameter exists for CLI UX; core does not prompt.
    """
    dev_path = f"/dev/{device_name}"
    if not is_block_device(dev_path):
        return UnitResult(success=False, message=f"Cannot reset non-existent device {device_name}")

    try:
        sysfs_reset_device(dev_path)
        return UnitResult(success=True, message="reset")
    except (SystemCommandError, RuntimeError) as e:
        return UnitResult(success=False, message=str(e))


def persist_writeback(device_name: str, writeback_device: Optional[str], apply_now: bool = True) -> PersistResult:
    """
    Persist writeback-device using systemd zram-generator.conf.
    This function does not edit files directly here to keep core/devices focused;
    we invoke config handler via a subprocess to keep dependencies minimal, or this
    can be swapped to a python import if config API is made core-safe.
    """
    # Prefer Python import if available and side-effect free
    try:
        # Late import to avoid circular deps if project refactors later
        from core.config import update_zram_config
        updates: Dict[str, Any] = {}
        if writeback_device is None:
            updates["writeback-device"] = None
        else:
            if not is_block_device(writeback_device):
                raise NotBlockDeviceError(f"{writeback_device} is not a block device")
            updates["writeback-device"] = writeback_device

        ok, err, rendered_config = update_zram_config(device_name, updates)
        if not ok:
            raise ValidationError(err or "Failed to update zram-generator.conf")

        # Atomically write the rendered config to the canonical path
        write_ok, write_err = atomic_write_to_file(CONFIG_PATH, rendered_config)
        if not write_ok:
            raise ValidationError(write_err or "Failed to write config file")

        applied = False
        msg = "Persisted"
        if apply_now:
            systemd_daemon_reload()
            svc = f"systemd-zram-setup@{device_name}.service"
            ok2, err2 = systemd_try_restart(svc)
            applied = ok2
            if not ok2:
                msg = f"Persisted, but restart failed: {err2 or ''}".strip()

        return PersistResult(success=True, device=device_name, applied=applied, message=msg)
    except (SystemCommandError, ValidationError, NotBlockDeviceError) as e:
        return PersistResult(success=False, device=device_name, applied=False, message=str(e))
    except Exception as e:
        return PersistResult(success=False, device=device_name, applied=False, message=f"Unexpected error: {e}")

# ============ Orchestration API ============

def _get_live_writeback_device(device_name: str) -> str:
    """Reads sysfs to get the current backing device for a zram device."""
    dev_path = f"/dev/{device_name}"
    if not is_block_device(dev_path):
        return ""
    current_backing = _get_sysfs(device_name, "backing_dev")
    # Some kernels use an empty string when none; normalize to empty string.
    return current_backing if current_backing is not None else ""

def _is_writeback_state_correct(current_backing_device: str, desired_writeback_device: Optional[str]) -> bool:
    """Compares the live state to the desired state."""
    if desired_writeback_device is None:
        # We want no writeback, so state is correct if there is no current backing device
        return not bool(current_backing_device) or current_backing_device == "none"
    else:
        # We want a specific writeback device
        return current_backing_device == desired_writeback_device

def _apply_live_writeback_change(
    device_name: str,
    desired_writeback: Optional[str],
    force: bool,
    active: bool,
) -> Tuple[bool, List[Action]]:
    """
    Performs the zramctl --reset and zramctl --create operations.
    Returns a tuple of (success, list_of_actions).
    """
    actions: List[Action] = []

    if active and not force:
        actions.append(Action(name="precondition", success=False, message=f"{device_name} is active; use force to recreate"))
        return False, actions

    params = _read_params_best_effort(device_name)
    size = params.get("disksize") or "1G"
    algorithm = params.get("algorithm")
    streams = params.get("streams")

    try:
        _reconfigure_device_sysfs(device_name, size, algorithm, streams, desired_writeback)
        actions.append(Action(name="reconfigure", success=True, message="reconfigured via sysfs"))
        return True, actions
    except (ValidationError, RuntimeError) as e:
        actions.append(Action(name="reconfigure", success=False, message=str(e)))
        return False, actions

def restart_device_unit(device_name: str, mode: str = "try") -> UnitResult:
    """
    Restart the systemd unit for a device with a policy:
      - mode = "try": best-effort restart (no exception bubbling), reports success flag.
      - mode = "force": hard restart (raises if systemctl fails), converted to UnitResult.
      - mode = "none": no-op, returns success True.
    """
    svc = f"systemd-zram-setup@{device_name}.service"
    if mode == "none":
        return UnitResult(success=True, message="no-op", service=svc)
    if mode == "try":
        ok, err = systemd_try_restart(svc)
        if ok:
            return UnitResult(success=True, message="restarted", service=svc)
        return UnitResult(success=False, message=err or "restart failed", service=svc)
    if mode == "force":
        try:
            systemd_restart(svc)
            return UnitResult(success=True, message="restarted", service=svc)
        except SystemCommandError as e:
            return UnitResult(success=False, message=str(e), service=svc)
    # Unknown mode: treat as failure
    return UnitResult(success=False, message=f"unknown restart mode: {mode}", service=svc)


def ensure_writeback_state(
    device_name: str,
    desired_writeback: Optional[str],
    force: bool = False,
    restart_mode: str = "try",
) -> OrchestrationResult:
    """
    Idempotently ensure device writeback configuration equals desired_writeback.
    - If device is active and change is needed, requires force=True (resets/recreate).
    - Preserves current size/algorithm/streams best-effort.
    Returns OrchestrationResult with step-by-step actions.
    """
    actions: List[Action] = []

    # 1. Validate desired target if provided
    if desired_writeback:
        if not is_block_device(desired_writeback):
            return OrchestrationResult(
                success=False,
                device=device_name,
                desired_writeback=desired_writeback,
                actions=[Action(name="validate-writeback-device", success=False, message=f"{desired_writeback} is not a block device")],
                message="validation failed",
            )

    dev_path = f"/dev/{device_name}"
    exists = is_block_device(dev_path)
    if not exists and desired_writeback is None:
        # No device and no writeback desired: no-op
        actions.append(Action(name="noop-no-device", success=True, message="Device does not exist and no writeback desired"))
        unit_res = restart_device_unit(device_name, mode="none")
        actions.append(Action(name="restart(none)", success=unit_res.success, message=unit_res.message))
        return OrchestrationResult(
            success=all(a.success for a in actions),
            device=device_name,
            desired_writeback=desired_writeback,
            actions=actions,
            message="no changes required",
        )

    # 2. Get live state
    current_backing = _get_live_writeback_device(device_name)

    # 3. Check if state is already correct
    if _is_writeback_state_correct(current_backing, desired_writeback):
        actions.append(Action(name="noop-already-desired", success=True, message=f"backing_dev already '{current_backing or 'None'}'"))
        unit_res = restart_device_unit(device_name, mode=restart_mode)
        actions.append(Action(name=f"restart({restart_mode})", success=unit_res.success, message=unit_res.message))
        return OrchestrationResult(
            success=all(a.success for a in actions),
            device=device_name,
            desired_writeback=desired_writeback,
            actions=actions,
            message="no changes required",
        )

    # 4. Apply the change
    active = _device_active(device_name)
    success, apply_actions = _apply_live_writeback_change(device_name, desired_writeback, force, active)
    actions.extend(apply_actions)

    if not success:
        return OrchestrationResult(
            success=False,
            device=device_name,
            desired_writeback=desired_writeback,
            actions=actions,
            message="failed to apply live changes",
        )

    # 5. Optional restart
    unit_res = restart_device_unit(device_name, mode=restart_mode)
    actions.append(Action(name=f"restart({restart_mode})", success=unit_res.success, message=unit_res.message))

    return OrchestrationResult(
        success=all(a.success for a in actions),
        device=device_name,
        desired_writeback=desired_writeback,
        actions=actions,
        message="applied",
    )
