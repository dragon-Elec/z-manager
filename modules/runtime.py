# z-manager/modules/runtime.py
"""
Manages live, volatile system settings.

This module acts as a high-level manager for volatile system settings.
It provides simple interfaces for getting current states and orchestrating
changes via the core system tuning module.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from core.utils.common import read_file
from core import system_tuning

_LOGGER = logging.getLogger(__name__)


# --- CPU Governor ---

def get_available_cpu_governors() -> List[str]:
    """Gets the list of available CPU governors from the first CPU core."""
    path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors")
    content = read_file(path)
    return content.split() if content else []

def get_current_cpu_governor() -> str:
    """Gets the current CPU governor of the first CPU core."""
    path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    return read_file(path) or "unknown"

def set_cpu_governor(governor: str) -> bool:
    """Orchestrates setting the CPU governor for all online CPU cores."""
    available = get_available_cpu_governors()
    return system_tuning.set_cpu_governor(governor, available)


# --- I/O Scheduler ---

def get_available_io_schedulers(device_name: str) -> List[str]:
    """Gets the list of available I/O schedulers for a block device."""
    path = Path(f"/sys/block/{device_name}/queue/scheduler")
    content = read_file(path)
    return content.replace("[", "").replace("]", "").split() if content else []

def get_current_io_scheduler(device_name: str) -> str:
    """Gets the currently active I/O scheduler for a block device."""
    path = Path(f"/sys/block/{device_name}/queue/scheduler")
    content = read_file(path)
    if not content:
        return "unknown"

    for part in content.split():
        if part.startswith("[") and part.endswith("]"):
            return part[1:-1]
    return "unknown"

def set_io_scheduler(device_name: str, scheduler: str) -> bool:
    """Orchestrates setting the I/O scheduler for a given block device."""
    available = get_available_io_schedulers(device_name)
    return system_tuning.set_io_scheduler(device_name, scheduler, available)


# --- Live Kernel Parameters ---

def get_vfs_cache_pressure() -> int:
    """Gets the current vm.vfs_cache_pressure value."""
    path = Path("/proc/sys/vm/vfs_cache_pressure")
    val = read_file(path)
    return int(val) if val and val.isdigit() else 100

def set_vfs_cache_pressure(value: int) -> bool:
    """Orchestrates setting the live vm.vfs_cache_pressure value."""
    return system_tuning.set_vfs_cache_pressure(value)
