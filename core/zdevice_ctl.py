# zman/core/zdevice_ctl.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

from core.os_utils import (
    run,
    SystemCommandError,
    ValidationError,
    NotBlockDeviceError,
    is_block_device,
    read_file,
    sysfs_write,
    zram_sysfs_dir,
    zramctl_reset,
    zramctl_create,
    parse_zramctl_table,
    systemd_daemon_reload,
    systemd_try_restart,
    systemd_restart,
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


def set_writeback(device_name: str, writeback_device: str, force: bool = False, create_if_missing: bool = True, default_size: str = "1G") -> WritebackResult:
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

    if active:
        # Best-effort deactivation for force mode
        run(["swapoff", f"/dev/{device_name}"], check=False)
        run(["umount", f"/dev/{device_name}"], check=False)
    dev_path = f"/dev/{device_name}"
    if not create_if_missing and not is_block_device(dev_path):
        raise NotBlockDeviceError(f"Device {device_name} does not exist; set create_if_missing=True to auto-create")

    params = _read_params_best_effort(device_name, default_size)
    size = params.get("disksize") or default_size
    algorithm = params.get("algorithm")
    streams = params.get("streams")

    dev_path = f"/dev/{device_name}"

    # 1. Reset the device. This sets disksize to 0.
    try:
        zramctl_reset(dev_path)
    except SystemCommandError as e:
        raise ValidationError(f"Failed to reset device {device_name}: {e}")

    # 2. Set the backing device via sysfs (MUST be done while size is 0)
    write_path = f"/sys/block/{device_name}/backing_dev"
    ok, err = sysfs_write(write_path, writeback_device)
    if not ok:
        raise ValidationError(f"Failed to set writeback via sysfs for {device_name}: {err}")

    # 3. Now, apply the rest of the configuration
    zramctl_create(dev_path, size=size, algorithm=algorithm, streams=streams)

    return WritebackResult(
        success=True,
        device=device_name,
        action="set-writeback",
        details={"writeback_device": writeback_device, "preserved": {"size": size, "algorithm": algorithm, "streams": streams}},
    )


def clear_writeback(device_name: str, force: bool = False, create_if_missing: bool = True, default_size: str = "1G") -> WritebackResult:
    """
    Clear writeback by resetting and recreating device without --writeback-device.
    Creates if missing and create_if_missing=True; uses default_size if creating new.
    """
    active = _device_active(device_name)
    if active and not force:
        raise ValidationError(f"{device_name} is active; use force=True to reset and clear writeback")

    if active:
        # Best-effort deactivation for force mode
        run(["swapoff", f"/dev/{device_name}"], check=False)
        run(["umount", f"/dev/{device_name}"], check=False)
    dev_path = f"/dev/{device_name}"
    if not create_if_missing and not is_block_device(dev_path):
        raise NotBlockDeviceError(f"Device {device_name} does not exist; set create_if_missing=True to auto-create")

    params = _read_params_best_effort(device_name, default_size)
    size = params.get("disksize") or default_size
    algorithm = params.get("algorithm")
    streams = params.get("streams")

    dev_path = f"/dev/{device_name}"
    if is_block_device(dev_path):
        try:
            zramctl_reset(dev_path)
        except SystemCommandError as e:
            raise ValidationError(f"Failed to reset device {device_name}: {e}")
    # recreate
    zramctl_create(dev_path, size=size, algorithm=algorithm, streams=streams)

    # clear writeback via sysfs by writing "none"
    write_path = f"/sys/block/{device_name}/backing_dev"
    ok, err = sysfs_write(write_path, "none")
    if not ok:
        raise ValidationError(f"Failed to clear writeback via sysfs for {device_name}: {err}")

    return WritebackResult(
        success=True,
        device=device_name,
        action="clear-writeback",
        details={"preserved": {"size": size, "algorithm": algorithm, "streams": streams}},
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
    Reset a zram device via `zramctl --reset /dev/zramN`.
    confirm parameter exists for CLI UX; core does not prompt.
    """
    dev_path = f"/dev/{device_name}"
    if not is_block_device(dev_path):
        return UnitResult(success=False, message=f"Cannot reset non-existent device {device_name}")

    try:
        zramctl_reset(dev_path)
        return UnitResult(success=True, message="reset")
    except SystemCommandError as e:
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

        ok, err, _rendered = update_zram_config(device_name, updates)
        if not ok:
            raise ValidationError(err or "Failed to update zram-generator.conf")

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
        return not bool(current_backing_device)
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

    dev_path = f"/dev/{device_name}"

    # 1. Reset
    if is_block_device(dev_path):
        try:
            zramctl_reset(dev_path)
            actions.append(Action(name="reset", success=True, message="zramctl --reset via sysfs"))
        except SystemCommandError as e:
            actions.append(Action(name="reset", success=False, message=str(e)))
            return False, actions

    # 2. Set writeback via sysfs
    write_path = f"/sys/block/{device_name}/backing_dev"
    write_value = desired_writeback if desired_writeback is not None else "none"
    ok, err = sysfs_write(write_path, write_value)
    if not ok:
        actions.append(Action(name="set-writeback-sysfs", success=False, message=err))
        return False, actions
    actions.append(Action(name="set-writeback-sysfs", success=True, message=f"wrote '{write_value}' to backing_dev"))

    # 3. Recreate/set size
    try:
        zramctl_create(
            dev_path,
            size=size,
            algorithm=algorithm,
            streams=streams,
        )
        actions.append(Action(
            name="recreate",
            success=True,
            message=f"size={size} algo={algorithm or 'default'} streams={streams or 'default'}",
        ))
    except SystemCommandError as e:
        actions.append(Action(name="recreate", success=False, message=str(e)))
        return False, actions

    return True, actions

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
