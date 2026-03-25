# z-manager/core/utils/swap.py
"""
Swap device detection and parsing utilities.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .common import run, SystemCommandError, read_file


@dataclass(frozen=True)
class SwapDevice:
    """Represents a single entry from /proc/swaps."""

    name: str
    type: str
    size_kb: int
    used_kb: int
    priority: int


def get_all_swaps() -> list[SwapDevice]:
    """
    Parses /proc/swaps to get a list of all active swap devices on the system.
    """
    content = read_file("/proc/swaps")
    if not content:
        return []

    lines = content.strip().splitlines()
    if len(lines) <= 1:
        return []

    swaps = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 5 and parts[2].isdigit():
            try:
                swaps.append(
                    SwapDevice(
                        name=parts[0],
                        type=parts[1],
                        size_kb=int(parts[2]),
                        used_kb=int(parts[3]),
                        priority=int(parts[4]),
                    )
                )
            except (ValueError, IndexError):
                continue
    return swaps


def is_device_active(device_path: str) -> bool:
    """Check if device is used as swap or mounted."""
    real_p = os.path.realpath(device_path)
    for f in ("/proc/swaps", "/proc/mounts"):
        try:
            for line in Path(f).read_text(errors="ignore").splitlines():
                parts = line.split()
                if parts and (parts[0] == real_p or parts[0] == device_path):
                    return True
        except Exception:
            pass
    return False


def is_device_in_swaps(device_name: str) -> bool:
    """Checks if a device name is currently used as swap."""
    try:
        swaps = run(["cat", "/proc/swaps"]).out
        if f"/dev/{device_name}" in swaps:
            return True
    except (SystemCommandError, OSError):
        pass
    return False


def detect_resume_swap() -> Optional[str]:
    """
    Returns the path of the first non-zram swap in /proc/swaps, or None.
    """
    content = read_file("/proc/swaps")
    if not content:
        return None
    for line in content.splitlines()[1:]:
        parts = line.split()
        if parts and "zram" not in parts[0]:
            return parts[0]
    return None
