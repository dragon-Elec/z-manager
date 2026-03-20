# z-manager/core/device_management/provisioner.py
"""
The Hazard Zone.
Handles device creation, kernel node management, and destructive resets.
Logic in this file can directly impact kernel stability and system swap.
"""
from __future__ import annotations
import os
import logging
from typing import Optional

from core.os_utils import (
    run,
    SystemCommandError,
    ValidationError,
    read_file,
    sysfs_write,
    zram_sysfs_dir,
    sysfs_reset_device,
)
from .types import UnitResult

_LOGGER = logging.getLogger(__name__)

def ensure_device_exists(device_name: str) -> None:
    """
    Ensures the /dev/zramN node exists.
    Uses kernel's hot_add mechanism.
    """
    dev_path = f"/dev/{device_name}"
    if os.path.exists(dev_path):
        return

    try:
        run(["modprobe", "zram"], check=True)
        if not device_name.startswith("zram"):
            raise RuntimeError(f"Invalid device name '{device_name}'")
        
        device_num_str = device_name[4:]
        if not device_num_str.isdigit():
            raise RuntimeError(f"Invalid device number in '{device_name}'")

        hot_add_path = "/sys/class/zram-control/hot_add"
        if not os.path.exists(hot_add_path):
            raise RuntimeError("Kernel does not support hot_add.")

        current_devices = {d for d in os.listdir("/sys/block") if d.startswith("zram")}
        target_num = int(device_num_str)

        while not os.path.exists(dev_path):
            with open(hot_add_path, "w") as f:
                f.write("1")
            
            new_devices = {d for d in os.listdir("/sys/block") if d.startswith("zram")}
            if not (new_devices - current_devices):
                 raise RuntimeError("Failed to create any zram device via hot_add")
            
            current_devices = new_devices
            highest_num = max(int(d[4:]) for d in new_devices if d[4:].isdigit())
            if highest_num > target_num:
                raise RuntimeError(f"Created up to {highest_num}, but target {device_name} missing.")

    except (SystemCommandError, IOError, OSError) as e:
        raise RuntimeError(f"Failed to ensure device '{device_name}': {e}")


def reconfigure_device_sysfs(
    device_name: str, 
    size: str, 
    algorithm: Optional[str] = None, 
    streams: Optional[int] = None, 
    backing_dev: Optional[str] = None
) -> None:
    """
    Low-level kernel reconfiguration.
    Destructive: Resets the device before applying new settings.
    """
    ensure_device_exists(device_name)
    sysfs_path = zram_sysfs_dir(device_name)
    dev_path = f"/dev/{device_name}"

    current_size = read_file(f"{sysfs_path}/disksize")
    if current_size is None:
        raise ValidationError(f"Cannot read disksize for '{device_name}'. The device may be in a bad state.")

    if current_size != "0":
        sysfs_reset_device(dev_path)

    if backing_dev:
        backing_path = f"{sysfs_path}/backing_dev"
        if not os.path.exists(backing_path):
            raise NotImplementedError(f"Cannot set writeback device: your kernel does not support it (sysfs node '{backing_path}' is missing).")
        try:
            sysfs_write(backing_path, backing_dev)
        except (IOError, OSError) as e:
            raise ValidationError(f"Failed to set backing_dev '{backing_dev}'") from e

    if algorithm:
        try:
            sysfs_write(f"{sysfs_path}/comp_algorithm", algorithm)
        except (IOError, OSError) as e:
            raise ValidationError(f"Failed to set comp_algorithm '{algorithm}'") from e

    if streams:
        try:
            sysfs_write(f"{sysfs_path}/max_comp_streams", str(streams))
        except (IOError, OSError) as e:
            raise ValidationError(f"Failed to set max_comp_streams '{streams}'") from e

    try:
        sysfs_write(f"{sysfs_path}/disksize", size)
    except (IOError, OSError) as e:
        raise ValidationError(f"Failed to set disksize '{size}'") from e


def reset_device(device_name: str, confirm: bool = False) -> UnitResult:
    """
    Public API to reset a device safely (preserves the node).
    confirm parameter exists for CLI UX compatibility.
    """
    dev_path = f"/dev/{device_name}"
    from core.os_utils import is_block_device
    if not is_block_device(dev_path):
        return UnitResult(success=False, message=f"Device {device_name} does not exist")

    try:
        sysfs_reset_device(dev_path)
        return UnitResult(success=True, message="reset")
    except (SystemCommandError, RuntimeError) as e:
        return UnitResult(success=False, message=str(e))
