# zman/core/config_writer.py

from __future__ import annotations

from typing import Dict, Any, Optional, Tuple
from configobj import ConfigObj
import io
import re

from core.config import CONFIG_PATH, get_active_config_path
from pathlib import Path

def _read_local_config() -> ConfigObj:
    """Reads the specific target configuration file for editing to preserve structure and comments."""
    path = get_active_config_path()
    if path and path.exists():
        return ConfigObj(str(path), list_values=False, encoding='utf-8')
    return ConfigObj(list_values=False, encoding='utf-8')
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
    Strictly validates configuration updates to prevent injection and corruption.
    Returns None if valid, or an error string if invalid.
    """
    forbidden_chars = ("\n", "\r")

    for key, value in updates.items():
        # 1. Validate Keys
        key_str = str(key)
        if any(c in key_str for c in forbidden_chars):
            return f"Invalid characters in key: {key_str!r}"
        
        if value is None:
            continue

        # 2. Validate Values
        val_str = str(value)
        if any(c in val_str for c in forbidden_chars):
            return f"Injection attempt detected in value: {val_str!r}"
        
        # Prevent value from starting with '[' to avoid section injection
        if val_str.startswith("["):
             return f"Invalid value starting with '[': {val_str!r}"

        # 3. Specialized Field Validation
        match key:
            case "zram-size":
                # Allow alphanumeric, operators, parenthesis, comma, dot, and space
                if not re.match(r'^[\w\s\+\-\*\/\%\(\)\.\,]+$', val_str):
                    return f"Invalid zram-size format: {val_str!r}"
            
            case "compression-algorithm":
                # Allow alphanumeric and parens/equals (e.g. zstd(level=1))
                if not re.match(r'^[a-zA-Z0-9\-\(\)\=\s]+$', val_str):
                    return f"Invalid compression-algorithm format: {val_str!r}"
            
            case "swap-priority":
                if not val_str.lstrip("-").isdigit():
                    return f"Invalid swap-priority (must be integer): {val_str!r}"

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

    cfg = _read_local_config()
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
    cfg = _read_local_config()
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
    
    cfg = _read_local_config()
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
