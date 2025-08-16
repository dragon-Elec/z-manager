"""
Manages live, volatile system settings.

This module is responsible for making instantaneous changes to the running
system by writing to the /sys/ and /proc/sys/ filesystems. These changes
are generally not persistent and will be lost on reboot unless saved
by a mechanism in the 'persist' module.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from core.os_utils import sysfs_read, sysfs_write

_LOGGER = logging.getLogger(__name__)


# --- CPU Governor ---

def get_available_cpu_governors() -> List[str]:
    """Gets the list of available CPU governors from the first CPU core."""
    path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors")
    content = sysfs_read(path)
    return content.split() if content else []

def get_current_cpu_governor() -> str:
    """Gets the current CPU governor of the first CPU core."""
    path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    return sysfs_read(path) or "unknown"

def set_cpu_governor(governor: str) -> bool:
    """Sets the CPU governor for all online CPU cores."""
    if governor not in get_available_cpu_governors():
        _LOGGER.error(f"Governor '{governor}' is not available.")
        return False

    all_success = True
    found_any_governor_files = False

    cpu_glob_path = Path("/sys/devices/system/cpu/")
    for gov_path in cpu_glob_path.glob("cpu*/cpufreq/scaling_governor"):
        found_any_governor_files = True
        
        success, _ = sysfs_write(gov_path, governor)
        if not success:
            all_success = False
            _LOGGER.warning(f"Failed to set governor for {gov_path.parent.parent.name}")

    if not found_any_governor_files:
        _LOGGER.error("Could not find any CPU governor files in /sys. Is cpufreq enabled?")
        return False
        
    return all_success


# --- I/O Scheduler ---

def get_available_io_schedulers(device_name: str) -> List[str]:
    """Gets the list of available I/O schedulers for a block device."""
    path = Path(f"/sys/block/{device_name}/queue/scheduler")
    content = sysfs_read(path)
    return content.replace("[", "").replace("]", "").split() if content else []

def get_current_io_scheduler(device_name: str) -> str:
    """Gets the currently active I/O scheduler for a block device."""
    path = Path(f"/sys/block/{device_name}/queue/scheduler")
    content = sysfs_read(path)
    if not content:
        return "unknown"

    for part in content.split():
        if part.startswith("[") and part.endswith("]"):
            return part[1:-1]
    return "unknown"

def set_io_scheduler(device_name: str, scheduler: str) -> bool:
    """Sets the I/O scheduler for a given block device."""
    if not device_name or not device_name.strip():
        _LOGGER.error("set_io_scheduler called with an invalid or empty device_name.")
        return False

    if scheduler not in get_available_io_schedulers(device_name):
        _LOGGER.error(f"I/O Scheduler '{scheduler}' not available for device '{device_name}'.")
        return False

    path = Path(f"/sys/block/{device_name}/queue/scheduler")
    success, _ = sysfs_write(path, scheduler)
    return success


# --- Live Kernel Parameters ---

def get_vfs_cache_pressure() -> int:
    """Gets the current vm.vfs_cache_pressure value."""
    path = Path("/proc/sys/vm/vfs_cache_pressure")
    val = sysfs_read(path)
    return int(val) if val and val.isdigit() else 100

def set_vfs_cache_pressure(value: int) -> bool:
    """Sets the live vm.vfs_cache_pressure value."""
    if not 0 <= value <= 500: # Sanity check
        _LOGGER.error(f"Invalid vfs_cache_pressure value: {value}. Must be 0-500.")
        return False
    path = Path("/proc/sys/vm/vfs_cache_pressure")
    success, _ = sysfs_write(path, str(value))
    return success