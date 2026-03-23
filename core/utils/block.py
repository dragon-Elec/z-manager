# zman/core/utils/block.py
"""
Hardware and block device discovery.
"""
from __future__ import annotations
import os
import json
import logging
from pathlib import Path
from typing import Any
from .common import run

_LOGGER = logging.getLogger(__name__)

def is_block_device(path: str | Path) -> bool:
    """Determine if a path is a block device."""
    p = Path(path)
    try:
        return p.exists() and p.stat().st_mode & 0o170000 == 0o060000
    except Exception:
        return False

def get_device_filesystem_type(device_path: str) -> str | None:
    """Detect filesystem via blkid."""
    if not is_block_device(device_path):
        return None
    res = run(["blkid", "-o", "value", "-s", "TYPE", device_path])
    return res.out.strip() if res.code == 0 else None

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

def check_device_safety(device_path: str) -> tuple[bool, str]:
    """Verify if device is safe for write operations (no filesystem, not active)."""
    if fs_type := get_device_filesystem_type(device_path):
        return False, f"Device {device_path} contains a '{fs_type}' filesystem. usage would cause data loss."
    if is_device_active(device_path):
        return False, f"Device {device_path} is currently active (mounted or swap)."
    return True, ""

def get_device_scheduler(device_name: str) -> tuple[str, list[str]]:
    """Reads the I/O scheduler for a block device."""
    name = device_name.replace("/dev/", "")
    path = Path(f"/sys/block/{name}/queue/scheduler")
    if not (content := Path(path).read_text(encoding="utf-8") if path.exists() else None):
        return "unknown", []

    schedulers = []
    current = "none"
    for item in content.split():
        if item.startswith("[") and item.endswith("]"):
            current = item[1:-1]
            schedulers.append(current)
        else:
            schedulers.append(item)
    return current, schedulers

def set_device_scheduler(device_name: str, scheduler: str) -> bool:
    """Sets the I/O scheduler for a block device."""
    name = device_name.replace("/dev/", "")
    path = Path(f"/sys/block/{name}/queue/scheduler")
    try:
        path.write_text(scheduler, encoding="utf-8")
        return True
    except (IOError, OSError) as e:
        _LOGGER.error(f"Failed to set scheduler {scheduler} for {name}: {e}")
        return False

def list_block_devices() -> list[dict[str, Any]]:
    """
    List all block devices suitable for selection.
    Restores lowercase schema for backward compatibility.
    """
    try:
        res = run(["lsblk", "-J", "-o", "NAME,PATH,SIZE,TYPE,LABEL,FSTYPE,MOUNTPOINT,MODEL"])
        if res.code != 0: return []
        
        data = json.loads(res.out)
        flat_list = []
        
        def recurse(dev_list):
            for d in dev_list:
                if (d.get("name") or "").startswith("zram"): continue
                
                # Map back to lowercase schema expected by the application
                info = {
                    "name": d.get("name"),
                    "path": d.get("path"),
                    "size": d.get("size"),
                    "type": d.get("type"),
                    "label": d.get("label"),
                    "fstype": d.get("fstype"),
                    "mountpoint": d.get("mountpoint"),
                    "model": d.get("model")
                }
                flat_list.append(info)
                if children := d.get("children"):
                    recurse(children)
        
        recurse(data.get("blockdevices", []))
        return flat_list
    except Exception as e:
        _LOGGER.error(f"lsblk parsing failed: {e}")
        return []
