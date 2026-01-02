# zman/core/config.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
import configparser
import io
from pathlib import Path

from core.os_utils import systemd_daemon_reload, systemd_try_restart, SystemCommandError

# Standard systemd lookup paths in order of priority
SEARCH_PATHS = [
    Path("/etc/systemd/zram-generator.conf"),      # Admin overrides
    Path("/run/systemd/zram-generator.conf"),      # Runtime transient
    Path("/usr/lib/systemd/zram-generator.conf"),  # Vendor defaults
    Path("/usr/local/lib/systemd/zram-generator.conf") # Alternative vendor
]

# Canonical path for writing changes (always /etc)
CONFIG_PATH = "/etc/systemd/zram-generator.conf"

@dataclass(frozen=True)
class ConfigResult:
    success: bool
    device: str
    applied: bool
    message: str
    rendered: str

def get_active_config_path() -> Optional[Path]:
    """
    Returns the Path to the first existing zram-generator.conf found in the hierarchy.
    """
    for path in SEARCH_PATHS:
        if path.exists():
            return path
    return None

def read_zram_config() -> configparser.ConfigParser:
    """
    Read the active zram-generator.conf. Returns a configparser instance.
    """
    cfg = configparser.ConfigParser()
    path = get_active_config_path()
    if path:
        cfg.read(str(path))
    return cfg

def load_effective_config() -> str:
    """
    Load the content of the currently active configuration file.
    """
    path = get_active_config_path()
    if path:
        try:
            return path.read_text(encoding='utf-8')
        except Exception:
            pass
    
    # Fallback to configparser rendering if direct read fails
    cfg = read_zram_config()
    s = io.StringIO()
    cfg.write(s)
    return s.getvalue().strip()

def apply_config_with_restart(device: str, restart_mode: str = "try") -> ConfigResult:
    """
    Reload systemd and optionally restart the zram unit for the given device.
    """
    try:
        systemd_daemon_reload()
    except SystemCommandError as e:
        return ConfigResult(success=False, device=device, applied=False, message=f"daemon-reload failed: {e}", rendered="")

    if restart_mode == "none":
        return ConfigResult(success=True, device=device, applied=False, message="daemon-reload only", rendered="")

    svc = f"systemd-zram-setup@{device}.service"
    ok, err = systemd_try_restart(svc)
    if ok:
        return ConfigResult(success=True, device=device, applied=True, message="restarted", rendered="")
    return ConfigResult(success=False, device=device, applied=False, message=f"restart failed: {err or ''}".strip(), rendered="")