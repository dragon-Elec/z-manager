# zman/core/runtime.py
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

_LOGGER = logging.getLogger(__name__)


# --- Private Helpers for sysfs/procfs I/O ---

def _read_sys_file(path: Path) -> Optional[str]:
    """Safely reads a sysfs/procfs file."""
    try:
        return path.read_text().strip()
    except (IOError, FileNotFoundError):
        _LOGGER.warning(f"Could not read from {path}")
        return None

def _write_sys_file(path: Path, value: str) -> bool:
    """Safely writes to a sysfs/procfs file. Returns success."""
    try:
        path.write_text(value)
        _LOGGER.info(f"Successfully wrote '{value}' to {path}")
        return True
    except (IOError, PermissionError) as e:
        _LOGGER.error(f"Failed to write to {path}: {e}. Requires root privileges.")
        return False


# --- CPU Governor ---

def get_available_cpu_governors() -> List[str]:
    """Gets the list of available CPU governors from the first CPU core."""
    path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors")
    content = _read_sys_file(path)
    return content.split() if content else []

def get_current_cpu_governor() -> str:
    """Gets the current CPU governor of the first CPU core."""
    path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    return _read_sys_file(path) or "unknown"

def set_cpu_governor(governor: str) -> bool:
    """Sets the CPU governor for all online CPU cores."""
    if governor not in get_available_cpu_governors():
        _LOGGER.error(f"Governor '{governor}' is not available.")
        return False

    all_success = True
    cpu_glob_path = Path("/sys/devices/system/cpu/")
    for gov_path in cpu_glob_path.glob("cpu*/cpufreq/scaling_governor"):
        if not _write_sys_file(gov_path, governor):
            all_success = False
            _LOGGER.warning(f"Failed to set governor for {gov_path.parent.parent.name}")

    return all_success


# --- I/O Scheduler ---

def get_available_io_schedulers(device_name: str) -> List[str]:
    """Gets the list of available I/O schedulers for a block device."""
    path = Path(f"/sys/block/{device_name}/queue/scheduler")
    content = _read_sys_file(path)
    return content.replace("[", "").replace("]", "").split() if content else []

def get_current_io_scheduler(device_name: str) -> str:
    """Gets the currently active I/O scheduler for a block device."""
    path = Path(f"/sys/block/{device_name}/queue/scheduler")
    content = _read_sys_file(path)
    if not content:
        return "unknown"

    for part in content.split():
        if part.startswith("[") and part.endswith("]"):
            return part[1:-1]
    return "unknown"

def set_io_scheduler(device_name: str, scheduler: str) -> bool:
    """Sets the I/O scheduler for a given block device."""
    if scheduler not in get_available_io_schedulers(device_name):
        _LOGGER.error(f"I/O Scheduler '{scheduler}' not available for device '{device_name}'.")
        return False

    path = Path(f"/sys/block/{device_name}/queue/scheduler")
    return _write_sys_file(path, scheduler)


# --- Live Kernel Parameters ---

def get_vfs_cache_pressure() -> int:
    """Gets the current vm.vfs_cache_pressure value."""
    path = Path("/proc/sys/vm/vfs_cache_pressure")
    val = _read_sys_file(path)
    return int(val) if val and val.isdigit() else 100

def set_vfs_cache_pressure(value: int) -> bool:
    """Sets the live vm.vfs_cache_pressure value."""
    if not 0 <= value <= 500: # Sanity check
        _LOGGER.error(f"Invalid vfs_cache_pressure value: {value}. Must be 0-500.")
        return False
    path = Path("/proc/sys/vm/vfs_cache_pressure")
    return _write_sys_file(path, str(value))
