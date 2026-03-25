# z-manager/core/system_tuning.py
"""
Low-level system tuning orchestrator.
Handles privileged writes to /sys and /proc for kernel parameters.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from core.utils.common import read_file
from core.utils.io import pkexec_write

_LOGGER = logging.getLogger(__name__)

def set_cpu_governor(governor: str, available_governors: List[str]) -> bool:
    """Sets the CPU governor for all online CPU cores via pkexec."""
    if governor not in available_governors:
        _LOGGER.error(f"Governor '{governor}' is not available.")
        return False

    cpu_glob_path = Path("/sys/devices/system/cpu/")
    success_count = 0
    total_count = 0

    for gov_path in cpu_glob_path.glob("cpu*/cpufreq/scaling_governor"):
        total_count += 1
        success, err = pkexec_write(gov_path, governor)
        if success:
            success_count += 1
        else:
            _LOGGER.warning(f"Failed to set governor for {gov_path.parent.parent.name}: {err}")

    if total_count == 0:
        _LOGGER.error("Could not find any CPU governor files in /sys.")
        return False

    return success_count == total_count

def set_io_scheduler(device_name: str, scheduler: str, available_schedulers: List[str]) -> bool:
    """Sets the I/O scheduler for a given block device via pkexec."""
    if not device_name or not device_name.strip():
        return False

    if scheduler not in available_schedulers:
        _LOGGER.error(f"I/O Scheduler '{scheduler}' not available for device '{device_name}'.")
        return False

    path = Path(f"/sys/block/{device_name}/queue/scheduler")
    success, err = pkexec_write(path, scheduler)
    if not success:
        _LOGGER.error(f"Failed to set I/O scheduler for {device_name}: {err}")
    return success

def set_vfs_cache_pressure(value: int) -> bool:
    """Sets the live vm.vfs_cache_pressure value via pkexec."""
    if not 0 <= value <= 500:
        _LOGGER.error(f"Invalid vfs_cache_pressure value: {value}.")
        return False
    
    path = Path("/proc/sys/vm/vfs_cache_pressure")
    success, err = pkexec_write(path, str(value))
    if not success:
        _LOGGER.error(f"Failed to set vfs_cache_pressure: {err}")
    return success
