# zman/core/utils/zram_stats.py
"""
ZRAM-specific sysfs parsing and status reporting.
"""
from __future__ import annotations
import logging
import os
import re
from pathlib import Path
from typing import Any
from .common import read_file
from .units import bytes_to_human, calculate_compression_ratio

_LOGGER = logging.getLogger(__name__)

def scan_zram_devices() -> list[str]:
    """Find all zram device names in sysfs."""
    sys_block = Path("/sys/block")
    if not sys_block.exists(): return []
    try:
        devs = [e.name for e in sys_block.iterdir() if e.is_dir() and e.name.startswith("zram")]
        devs.sort(key=lambda x: int(x[4:]) if x[4:].isdigit() else 0)
        return devs
    except Exception:
        return []

def zram_sysfs_dir(device_name: str) -> str:
    """Returns sysfs path for a zram device."""
    return f"/sys/block/{device_name}"
def sysfs_reset_device(device_path: str) -> None:
    """Resets a zram device via sysfs."""
    import os
    device_name = os.path.basename(device_path)
    reset_path = Path(f"/sys/block/{device_name}/reset")
    try:
        reset_path.write_text("1", encoding="utf-8")
    except (IOError, OSError) as e:
        # Dual-layer reporting: High-level context + raw system error
        raise RuntimeError(f"Z-Manager Error: Failed to reset zram device via {reset_path}. System Error: {e}") from e


def get_zram_mountpoint(device_name: str) -> str:
    """Check if zram is used as swap or mounted."""
    dev_path = f"/dev/{device_name}"
    for f in ("/proc/swaps", "/proc/mounts"):
        try:
            content = Path(f).read_text(encoding="utf-8")
            if dev_path in content:
                if f == "/proc/swaps": return "[SWAP]"
                for line in content.splitlines():
                    if line.startswith(dev_path):
                        return line.split()[1]
        except Exception:
            pass
    return ""

def get_zram_props(device_name: str) -> dict[str, Any]:
    """
    Read all properties for a zram device. 
    Restores full parity with the monolith (Legacy Fallbacks & Writeback).
    """
    base = Path(f"/sys/block/{device_name}")
    props = {"name": device_name}
    
    # Disksize
    ds = read_file(base / "disksize")
    props["disksize"] = bytes_to_human(int(ds)) if ds and ds != "0" else "-"
    
    # 1. MM Stat (Modern kernels: 7+ columns)
    ms = read_file(base / "mm_stat")
    if ms:
        p = ms.split()
        if len(p) >= 3:
            props["data-size"] = bytes_to_human(int(p[0]))
            props["compr-size"] = bytes_to_human(int(p[1]))
            props["total-size"] = bytes_to_human(int(p[2]))
            props["ratio"] = calculate_compression_ratio(props["data-size"], props["compr-size"])
        
        if len(p) >= 7:
            props["mem-limit"] = bytes_to_human(int(p[3]))
            props["mem-used-max"] = bytes_to_human(int(p[4]))
            props["same-pages"] = p[5] # Count, not size
    else:
        # 2. Legacy Fallback (Older kernels)
        orig = read_file(base / "orig_data_size")
        compr = read_file(base / "compr_data_size")
        total = read_file(base / "mem_used_total")
        
        props["data-size"] = bytes_to_human(int(orig)) if orig else "-"
        props["compr-size"] = bytes_to_human(int(compr)) if compr else "-"
        props["total-size"] = bytes_to_human(int(total)) if total else "-"
        props["ratio"] = calculate_compression_ratio(props["data-size"], props["compr-size"])
        
        # Extended fields usually unavailable in legacy, use defaults
        props.setdefault("mem-limit", "-")
        props.setdefault("mem-used-max", "-")
        props.setdefault("same-pages", "-")

    # 3. Writeback (Migrated) Stats
    bd = read_file(base / "bd_stat")
    if bd:
        p = bd.split()
        if len(p) >= 3:
            # Column 3 is bd_writes (pages). PAGE_SIZE is 4096.
            props["migrated"] = bytes_to_human(int(p[2]) * 4096)
    else:
        props["migrated"] = "0B"
    
    # 4. Compression Algorithm
    algo = read_file(base / "comp_algorithm")
    if algo:
        m = re.search(r'\[([^\]]+)\]', algo)
        props["algorithm"] = m.group(1) if m else algo.split()[0]
    else:
        props["algorithm"] = None
        
    props["mountpoint"] = get_zram_mountpoint(device_name)
    return props

def parse_zramctl_table() -> list[dict[str, Any]]:
    """Backward compatibility wrapper for zram device list."""
    return [get_zram_props(dev) for dev in scan_zram_devices() if get_zram_props(dev).get("disksize") != "-"]
