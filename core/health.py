# zman/core/health.py

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from typing import Optional, List, Dict

from core.utils.common import run, read_file
from modules.journal import python_journal_available


@dataclass(frozen=True)
class SwapDevice:
    """Represents a single entry from /proc/swaps."""
    name: str
    type: str
    size_kb: int
    used_kb: int
    priority: int


@dataclass(frozen=True)
class ZswapStatus:
    available: bool
    enabled: Optional[bool]
    detail: str = ""


@dataclass(frozen=True)
class DeviceHealth:
    device: str
    sysfs_ok: bool
    swaps_entry: bool
    issues: List[str]


@dataclass(frozen=True)
class HealthReport:
    zramctl_available: bool
    systemd_available: bool
    sysfs_root_accessible: bool
    zswap: ZswapStatus
    journal_available: bool
    kernel_version: str
    devices_summary: str
    notes: List[str]


_CMD_CACHE: Dict[str, bool] = {}


def _check_cmd_available(cmd: str) -> bool:
    if cmd in _CMD_CACHE:
        return _CMD_CACHE[cmd]
        
    r = run(["/bin/sh", "-lc", f"command -v {cmd} >/dev/null 2>&1"], check=False)
    available = (r.code == 0)
    _CMD_CACHE[cmd] = available
    return available


def get_zswap_status() -> ZswapStatus:
    enabled_path = "/sys/module/zswap/parameters/enabled"
    if not os.path.exists(enabled_path):
        return ZswapStatus(available=False, enabled=None, detail="zswap sysfs not present")
    
    val = read_file(enabled_path)
    if val is None:
        return ZswapStatus(available=True, enabled=None, detail="unable to read zswap enabled")
    
    val = val.strip()
    enabled = True if val.upper() == "Y" else False
    return ZswapStatus(available=True, enabled=enabled, detail=f"value={val}")


def _check_sysfs_root() -> bool:
    return os.path.isdir("/sys/block")


def _devices_summary() -> str:
    """Count zram devices using sysfs instead of zramctl."""
    try:
        count = 0
        if not os.path.exists("/sys/block"):
            return "unable to read /sys/block"
            
        for entry in os.listdir("/sys/block"):
            if entry.startswith("zram"):
                # Check if device is configured (disksize > 0)
                disksize_path = f"/sys/block/{entry}/disksize"
                size_str = read_file(disksize_path)
                if size_str:
                    try:
                        if int(size_str.strip()) > 0:
                            count += 1
                    except ValueError:
                        pass
        
        if count == 0:
            return "no active devices"
        return f"{count} device(s) active"
    except (OSError, FileNotFoundError):
        return "unable to read /sys/block"


def check_system_health() -> HealthReport:
    zramctl_ok = _check_cmd_available("zramctl")
    systemd_ok = _check_cmd_available("systemctl")
    sysfs_ok = _check_sysfs_root()
    zswap = get_zswap_status()
    
    # Check journal availability (Python module or journalctl command)
    journal_ok = python_journal_available() or _check_cmd_available("journalctl")
    
    kernel_version = platform.release()

    notes: List[str] = []
    if not zramctl_ok:
        notes.append("zramctl not found (optional; not required for functionality)")
    if not systemd_ok:
        notes.append("systemctl not found; systemd integration limited")
    if not sysfs_ok:
        notes.append("/sys/block not accessible")
    if zswap.available and zswap.enabled:
        notes.append("zswap is enabled; may conflict with zram writeback policies")
    if not journal_ok:
        notes.append("journal access not available (python3-systemd or journalctl missing)")

    return HealthReport(
        zramctl_available=zramctl_ok,
        systemd_available=systemd_ok,
        sysfs_root_accessible=sysfs_ok,
        zswap=zswap,
        journal_available=journal_ok,
        kernel_version=kernel_version,
        devices_summary=_devices_summary(),
        notes=notes,
    )


def get_all_swaps() -> List[SwapDevice]:
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
                swaps.append(SwapDevice(
                    name=parts[0],
                    type=parts[1],
                    size_kb=int(parts[2]),
                    used_kb=int(parts[3]),
                    priority=int(parts[4])
                ))
            except (ValueError, IndexError):
                continue
    return swaps
