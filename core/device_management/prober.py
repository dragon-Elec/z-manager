# z-manager/core/device_management/prober.py
"""
The Safe Zone.
Handles device detection, state reading, and sysfs probing.
No destructive operations or system changes are performed here.
"""

from __future__ import annotations
from typing import List, Optional

from core.utils.common import (
    run,
    SystemCommandError,
    read_file,
)
from core.utils.block import is_block_device
from core.utils.swap import is_device_in_swaps
from core.utils.zram_stats import zram_sysfs_dir, parse_zramctl_table
from .types import DeviceInfo, WritebackStatus


def list_devices() -> List[DeviceInfo]:
    """Probes the system and returns a list of all active ZRAM devices."""
    infos = parse_zramctl_table()
    return [
        DeviceInfo(
            name=d.get("name", "unknown"),
            disksize=d.get("disksize"),
            data_size=d.get("data-size"),
            compr_size=d.get("compr-size"),
            total_size=d.get("total-size"),
            mem_limit=d.get("mem-limit"),
            mem_used_max=d.get("mem-used-max"),
            same_pages=d.get("same-pages"),
            migrated=d.get("migrated"),
            mountpoint=d.get("mountpoint"),
            ratio=f"{d.get('ratio'):.2f}" if d.get("ratio") is not None else None,
            streams=d.get("streams"),
            algorithm=d.get("algorithm"),
        )
        for d in infos
    ]


def get_writeback_status(device_name: str) -> WritebackStatus:
    """Reads current writeback stats for a specific device."""
    dev_path = f"/dev/{device_name}"
    if not is_block_device(dev_path):
        from core.utils.common import NotBlockDeviceError

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


def is_device_active(device_name: str) -> bool:
    """Checks if a device is currently used as swap or mounted."""
    device_path = f"/dev/{device_name}"
    if is_device_in_swaps(device_name):
        return True
    try:
        mounts = run(["mount"]).out
        if device_path in mounts:
            return True
    except (SystemCommandError, OSError):
        pass
    return False


def _get_sysfs(device_name: str, node: str) -> Optional[str]:
    """Internal helper to read a specific sysfs node."""
    base = zram_sysfs_dir(device_name)
    return read_file(f"{base}/{node}")


def read_params_best_effort(device_name: str, default_size: str = "1G") -> dict:
    """
    Attempts to read current device parameters before a reset.
    Returns current values to preserve configuration.
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
