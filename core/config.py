# zman/core/config.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import configparser
import io

from core.os_utils import systemd_daemon_reload, systemd_try_restart, SystemCommandError

# Canonical config path for systemd zram-generator
CONFIG_PATH = "/etc/systemd/zram-generator.conf"


@dataclass(frozen=True)
class ConfigResult:
    success: bool
    device: str
    applied: bool
    message: str
    rendered: str


def generate_config_string(size_formula: str, algorithm: str, priority: int, device: str = "zram0", writeback_device: Optional[str] = None) -> str:
    """
    Create a zram-generator.conf configuration as a string.
    """
    cfg = configparser.ConfigParser()
    section: Dict[str, str] = {
        "zram-size": size_formula,
        "compression-algorithm": algorithm,
        "swap-priority": str(priority),
    }
    if writeback_device:
        section["writeback-device"] = writeback_device
    cfg[device] = section
    s = io.StringIO()
    cfg.write(s)
    return s.getvalue().strip()


def read_zram_config() -> configparser.ConfigParser:
    """
    Read existing zram-generator.conf from CONFIG_PATH. Returns a configparser instance.
    """
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH)
    return cfg


def update_zram_config(device: str, updates: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
    """
    Merge updates into an existing zram-generator.conf for the given device.
    Returns (success, error, rendered_config_string).
    """
    cfg = read_zram_config()
    if device not in cfg:
        cfg[device] = {}
    for key, value in updates.items():
        if value is None:
            if key in cfg[device]:
                cfg[device].pop(key)
        else:
            cfg[device][key] = str(value)

    s = io.StringIO()
    try:
        cfg.write(s)
        rendered = s.getvalue().strip()
        return True, None, rendered
    except Exception as e:
        return False, str(e), ""


def load_effective_config() -> str:
    """
    Load the current zram-generator.conf from CONFIG_PATH and return its raw content string.
    Returns empty string if file is not present or unreadable.
    """
    cfg = read_zram_config()
    s = io.StringIO()
    cfg.write(s)
    return s.getvalue().strip()


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


def apply_config_with_restart(device: str, restart_mode: str = "try") -> ConfigResult:
    """
    Reload systemd and optionally restart the zram unit for the given device.
      - restart_mode="try": attempt to restart the unit, return success flag without raising
      - restart_mode="force": same as try but message emphasizes failure if any
      - restart_mode="none": only daemon-reload, no unit restart
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
