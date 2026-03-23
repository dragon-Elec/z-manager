# zman/core/config.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from configobj import ConfigObj
import io
import subprocess
from pathlib import Path

from core.utils.common import run, SystemCommandError
from core.utils.privilege import systemd_daemon_reload, systemd_try_restart

# Standard systemd lookup paths (Legacy/Fallback)
SEARCH_PATHS = [
    Path("/etc/systemd/zram-generator.conf"),
    Path("/run/systemd/zram-generator.conf"),
    Path("/usr/lib/systemd/zram-generator.conf"),
    Path("/usr/local/lib/systemd/zram-generator.conf")
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

@dataclass
class EffectiveConfig:
    """Holds the merged configuration and the lineage (provenance) of each setting."""
    config: ConfigObj
    provenance: Dict[str, Dict[str, str]] = field(default_factory=dict) # {section: {key: source_file}}

def get_active_config_path() -> Optional[Path]:
    """Returns the primary (highest priority) config file path."""
    return next((p for p in SEARCH_PATHS if p.exists()), Path(CONFIG_PATH))

def _parse_systemd_cat_config(raw_output: str) -> EffectiveConfig:
    """
    Parses the tagged output from 'systemd-analyze cat-config'.
    Example tag: '# /etc/systemd/zram-generator.conf'
    """
    merged_cfg = ConfigObj(list_values=False, encoding='utf-8')
    provenance: Dict[str, Dict[str, str]] = {}
    
    current_file = "Unknown"
    current_section = "default"

    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue

        match line[0]:
            case "#":
                # Detect source file tag: # /path/to/file
                if line.startswith("# /"):
                    current_file = line.removeprefix("# ").strip()
            case "[":
                # Detect section: [zram0]
                current_section = line.strip("[]")
                if current_section not in merged_cfg:
                    merged_cfg[current_section] = {}
                if current_section not in provenance:
                    provenance[current_section] = {}
            case _:
                # Detect key-value: zram-size = 4096M
                if "=" in line:
                    key, value = (s.strip() for s in line.split("=", 1))
                    # Merging: Last one wins (systemd standard)
                    merged_cfg[current_section][key] = value
                    # Tracking: Who provided this specific value?
                    if current_section not in provenance:
                         provenance[current_section] = {}
                    provenance[current_section][key] = current_file

    return EffectiveConfig(config=merged_cfg, provenance=provenance)

def load_effective_config_state(root: Optional[str] = None) -> EffectiveConfig:
    """
    The 'God View' of the configuration.
    Uses systemd-analyze to merge the entire hierarchy (including .d directories).
    Optional 'root' parameter allows operating on an alternate filesystem root.
    """
    cmd = ["systemd-analyze"]
    if root:
        cmd.extend([f"--root={root}"])
    cmd.extend(["cat-config", "systemd/zram-generator.conf"])

    try:
        # We use systemd-analyze cat-config to let systemd handle the complex merging rules.
        res = run(cmd, check=True)
        if res.out:
            return _parse_systemd_cat_config(res.out)
    except (SystemCommandError, FileNotFoundError):
        # Fallback to single-file read if systemd-analyze is unavailable or fails
        pass
    
    # Fallback to traditional first-found logic
    # Note: Traditional fallback doesn't easily support 'root' without more logic,
    # so we prioritize the systemd-analyze path.
    path = get_active_config_path()
    cfg = ConfigObj(str(path), list_values=False, encoding='utf-8') if path and path.exists() else ConfigObj()
    return EffectiveConfig(config=cfg)

def read_zram_config() -> ConfigObj:
    """Read the merged, effective zram-generator configuration."""
    return load_effective_config_state().config

def read_global_config() -> Dict[str, str]:
    """Reads the merged [zram-generator] global section."""
    cfg = read_zram_config()
    return dict(cfg["zram-generator"]) if "zram-generator" in cfg else {}

def load_effective_config(root: Optional[str] = None) -> str:
    """Returns the raw concatenated string from systemd-analyze or the best-found file."""
    cmd = ["systemd-analyze"]
    if root:
        cmd.extend([f"--root={root}"])
    cmd.extend(["cat-config", "systemd/zram-generator.conf"])

    try:
        res = run(cmd, check=True)
        if res.out:
            return res.out
    except Exception:
        pass
    
    path = get_active_config_path()
    return path.read_text(encoding='utf-8') if path and path.exists() else ""

def apply_config_with_restart(device: str, restart_mode: str = "try") -> ConfigResult:
    """Reload systemd and optionally restart the zram unit for the given device."""
    try:
        systemd_daemon_reload()
    except SystemCommandError as e:
        return ConfigResult(success=False, device=device, applied=False, message=f"daemon-reload failed: {e}", rendered="")

    if restart_mode == "none":
        return ConfigResult(success=True, device=device, applied=False, message="daemon-reload only", rendered="")

    svc = f"systemd-zram-setup@{device}.service"
    ok, err = systemd_try_restart(svc)
    return ConfigResult(
        success=ok, 
        device=device, 
        applied=ok, 
        message="restarted" if ok else f"restart failed: {err or ''}".strip(), 
        rendered=""
    )