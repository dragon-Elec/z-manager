# zman/core/config_writer.py

from __future__ import annotations

from typing import Dict, Any, Optional, Tuple
from configobj import ConfigObj
import io
import re

from core.config import read_zram_config

def generate_config_string(size_formula: str, algorithm: str, priority: int, device: str = "zram0", writeback_device: Optional[str] = None) -> str:
    """
    Create a zram-generator.conf configuration as a string using ConfigObj.
    """
    cfg = ConfigObj(list_values=False, encoding='utf-8')
    cfg[device] = {}
    cfg[device]["zram-size"] = size_formula
    cfg[device]["compression-algorithm"] = algorithm
    cfg[device]["swap-priority"] = str(priority)
    
    if writeback_device:
        cfg[device]["writeback-device"] = writeback_device

    return "\n".join(cfg.write()).strip()


def validate_updates(updates: Dict[str, Any]) -> Optional[str]:
    """
    Validates configuration updates before applying them.
    Returns None if valid, or an error string if invalid.
    """
    # 1. Validate zram-size
    size = updates.get("zram-size")
    if size:
        size = str(size)
        # Check standard sizes (e.g., 512M) or formulas (min(...), ram / 2)
        # Simple regex for safety: allow alphanumeric, operators, parenthesis, comma
        if not re.match(r'^[\w\s\+\-\*\/\%\(\)\.\,]+$', size):
            return f"Invalid zram-size format: '{size}'"
        
    # 2. Validate compression-algorithm
    algo = updates.get("compression-algorithm")
    if algo:
        algo = str(algo)
        # Allow alphanumeric and parens (e.g. zstd(level=1))
        # Simple check: must start with a letter
        if not re.match(r'^[a-zA-Z0-9\-\(\)\=\s]+$', algo):
            return f"Invalid compression-algorithm format: '{algo}'"
            
    return None

def update_zram_config(device: str, updates: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
    """
    Merge updates into an existing zram-generator.conf for the given device.
    Uses ConfigObj to preserve comments and structure.
    Returns (success, error, rendered_config_string).
    """
    # Protection: Do not allow using the global section [zram-generator] as a device
    if device == "zram-generator":
        return False, "The section 'zram-generator' is reserved for global settings and cannot be used as a device name.", ""

    # Validation
    err = validate_updates(updates)
    if err:
        return False, err, ""

    cfg = read_zram_config()
    if device not in cfg:
        cfg[device] = {}
    
    # ConfigObj (like dict) modification
    for key, value in updates.items():
        if value is None:
            if key in cfg[device]:
                del cfg[device][key]
        else:
            cfg[device][key] = str(value)

    try:
        # ConfigObj.write() writes to file if filename is set. 
        # We want the string representation.
        # We can capture it by passing an output-like object or simply getting it back.
        # Simplest way: set filename to None temporary or use output
        s = io.BytesIO()
        cfg.write(s)
        # Decode bytes to string
        rendered = s.getvalue().decode('utf-8').strip()
        return True, None, rendered
    except Exception as e:
        return False, str(e), ""


def update_writeback_config(device: str, writeback_device: Optional[str]) -> Tuple[bool, Optional[str], str]:
    """
    Update the writeback-device for the given device in zram-generator.conf.
    Returns (ok, error, rendered_config_string).
    """
    updates: Dict[str, Any] = (
        {"writeback-device": writeback_device} if writeback_device is not None else {"writeback-device": None}
    )
    ok, err, rendered = update_zram_config(device, updates)
    return ok, err, rendered


def update_host_limit_config(device: str, min_ram_mb: Optional[int]) -> Tuple[bool, Optional[str], str]:
    """
    Update the host-memory-limit for the given device in zram-generator.conf.
    The value is specified in megabytes.
    Returns (ok, error, rendered_config_string).
    """
    updates: Dict[str, Any] = {}
    if min_ram_mb is not None and min_ram_mb > 0:
        # zram-generator expects the value with an M suffix for megabytes.
        updates["host-memory-limit"] = f"{min_ram_mb}M"
    else:
        # If the value is None or 0, we remove the setting from the config.
        updates["host-memory-limit"] = None

    ok, err, rendered = update_zram_config(device, updates)
    return ok, err, rendered


def update_filesystem_config(device: str, fs_type: Optional[str], mount_point: Optional[str]) -> Tuple[bool, Optional[str], str]:
    """
    Update the filesystem settings (fs-type, mount-point) for the given device.
    If fs_type or mount_point is None, both settings will be removed to disable
    filesystem mode.
    Returns (ok, error, rendered_config_string).
    """
    updates: Dict[str, Any] = {}
    if fs_type and mount_point:
        # Both values are present, so we set them.
        updates["fs-type"] = fs_type
        updates["mount-point"] = mount_point
    else:
        # One or both are missing, so we ensure both are removed for consistency.
        updates["fs-type"] = None
        updates["mount-point"] = None

    ok, err, rendered = update_zram_config(device, updates)
    return ok, err, rendered


def remove_device_from_config(device: str) -> Tuple[bool, Optional[str], str]:
    """
    Remove an entire device section from the configuration.
    Returns (ok, error, rendered_config_string).
    """
    cfg = read_zram_config()
    if device in cfg:
        del cfg[device]
    
    # We must write to string to render it
    s = io.BytesIO()
    try:
        cfg.write(s)
        rendered = s.getvalue().decode('utf-8').strip()
        return True, None, rendered
    except Exception as e:
        return False, str(e), ""


def update_global_config(updates: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
    """
    Updates the global [zram-generator] section.
    Returns (success, error, rendered_config_string).
    """
    # Validation
    # We can reuse validate_updates if keys match, or do custom validation
    # For now, simplistic validation
    
    cfg = read_zram_config()
    section = "zram-generator"
    
    if section not in cfg:
        cfg[section] = {}
        
    for key, value in updates.items():
        if value is None:
            if key in cfg[section]:
                del cfg[section][key]
        else:
            cfg[section][key] = str(value)
            
    try:
        s = io.BytesIO()
        cfg.write(s)
        rendered = s.getvalue().decode('utf-8').strip()
        return True, None, rendered
    except Exception as e:
        return False, str(e), ""
