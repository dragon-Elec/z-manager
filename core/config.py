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





def read_zram_config() -> configparser.ConfigParser:
    """
    Read existing zram-generator.conf from CONFIG_PATH. Returns a configparser instance.
    """
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH)
    return cfg





def load_effective_config() -> str:
    """
    Load the current zram-generator.conf from CONFIG_PATH and return its raw content string.
    Returns empty string if file is not present or unreadable.
    """
    cfg = read_zram_config()
    s = io.StringIO()
    cfg.write(s)
    return s.getvalue().strip()





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





