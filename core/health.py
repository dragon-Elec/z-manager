# zman/core/health.py

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from typing import Optional, List

from core.os_utils import run


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


def _check_cmd_available(cmd: str) -> bool:
    r = run(["/bin/sh", "-lc", f"command -v {cmd} >/dev/null 2>&1"], check=False)
    return r.code == 0


def _read_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def get_zswap_status() -> ZswapStatus:
    enabled_path = "/sys/module/zswap/parameters/enabled"
    if not os.path.exists(enabled_path):
        return ZswapStatus(available=False, enabled=None, detail="zswap sysfs not present")
    val = _read_file(enabled_path)
    if val is None:
        return ZswapStatus(available=True, enabled=None, detail="unable to read zswap enabled")
    enabled = True if val.upper() == "Y" else False
    return ZswapStatus(available=True, enabled=enabled, detail=f"value={val}")


def _check_sysfs_root() -> bool:
    return os.path.isdir("/sys/block")


def _devices_summary() -> str:
    # Use zramctl table output, but tolerate absence
    r = run(["/bin/sh", "-lc", "zramctl 2>/dev/null || true"], check=False)
    out = r.out.strip()
    if not out:
        return "no devices or zramctl produced no output"
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if len(lines) <= 1:
        return "no devices"
    count = 0
    for ln in lines[1:]:
        if "/dev/zram" in ln:
            count += 1
    return f"{count} device(s) reported by zramctl"


def _journal_available() -> bool:
    # Detect python3-systemd and journalctl command availability
    py = run(["/bin/sh", "-lc", "python3 -c 'import systemd.journal'"], check=False)
    if py.code == 0:
        return True
    jc = _check_cmd_available("journalctl")
    return jc


def check_system_health() -> HealthReport:
    zramctl_ok = _check_cmd_available("zramctl")
    systemd_ok = _check_cmd_available("systemctl")
    sysfs_ok = _check_sysfs_root()
    zswap = get_zswap_status()
    journal_ok = _journal_available()
    kernel_ver = platform.release()

    notes: List[str] = []
    if not zramctl_ok:
        notes.append("zramctl not found; install zram-tools")
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
        kernel_version=kernel_ver,
        devices_summary=_devices_summary(),
        notes=notes,
    )

def get_all_swaps() -> List[SwapDevice]:
    """
    Parses /proc/swaps to get a list of all active swap devices on the system.
    """
    swap_devices: List[SwapDevice] = []
    try:
        with open("/proc/swaps", "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return [] # No /proc/swaps means no swaps active

    # Skip the header line (lines[0])
    for line in lines[1:]:
        parts = line.strip().split()
        if len(parts) < 5:
            continue # Skip malformed lines

        try:
            # Typical format: /dev/dm-1 partition 8388604 0 -2
            name = parts[0]
            swap_type = parts[1]
            size_kb = int(parts[2])
            used_kb = int(parts[3])
            priority = int(parts[4])

            swap_devices.append(SwapDevice(
                name=name,
                type=swap_type,
                size_kb=size_kb,
                used_kb=used_kb,
                priority=priority
            ))
        except (ValueError, IndexError):
            # Gracefully skip any line that can't be parsed
            continue

    return swap_devices
