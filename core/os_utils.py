# zman/core/os_utils.py

from __future__ import annotations

import os
import subprocess
import shutil
import tempfile
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List, Union


# ============ Domain Errors ============

class SystemCommandError(RuntimeError):
    def __init__(self, cmd: List[str], returncode: int, stdout: str, stderr: str):
        super().__init__(f"Command failed: {' '.join(cmd)} (code {returncode})\n{stderr.strip()}")
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class ValidationError(ValueError):
    pass


class NotBlockDeviceError(ValidationError):
    pass


# ============ Low-level helpers ============

@dataclass(frozen=True)
class CmdResult:
    code: int
    out: str
    err: str


def run(cmd: List[str], check: bool = False, env: Optional[Dict[str, str]] = None) -> CmdResult:
    """
    Run a command and capture stdout/stderr. Optionally raise on failure.
    """
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    res = CmdResult(code=proc.returncode, out=proc.stdout, err=proc.stderr)
    if check and proc.returncode != 0:
        raise SystemCommandError(cmd, proc.returncode, proc.stdout, proc.stderr)
    return res


def is_block_device(path: str) -> bool:
    """
    Determine if a given path refers to a block device (by stat).
    """
    try:
        st = os.stat(path)
        # S_IFBLK 0o060000
        return (st.st_mode & 0o170000) == 0o060000
    except FileNotFoundError:
        return False
    except Exception:
        return False


# ============ Sysfs helpers ============

def read_file(path: Union[str, Path]) -> Optional[str]:
    """Safely reads a sysfs file, accepting either a string or Path object."""
    try:
        # The Path object can read itself, no need to convert if it's already one.
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
    except Exception:
        return None


def sysfs_write(path: Union[str, Path], value: str) -> None:
    """
    Safely writes to a sysfs file, accepting either a string or Path object.
    Raises IOError or OSError on failure.
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(value)
    except (IOError, OSError):
        raise


def zram_sysfs_dir(device_name: str) -> str:
    # device_name e.g. "zram0"
    return f"/sys/block/{device_name}"


# ============ zramctl wrappers ============


def sysfs_reset_device(device_path: str) -> None:
    """Resets a zram device using the sysfs interface to avoid device deletion."""
    device_name = os.path.basename(device_path)
    reset_path = f"/sys/block/{device_name}/reset"
    try:
        sysfs_write(reset_path, "1")
    except (IOError, OSError) as e:
        # This is the correct way to handle the error.
        # It reports the actual operation that failed (a file write)
        # and the underlying system error.
        raise RuntimeError(f"Failed to write '1' to sysfs node {reset_path}: {e}")


def zramctl_info_all() -> str:
    """
    Returns text output of `zramctl`.
    """
    return run(["zramctl"], check=False).out


def zramctl_info_json() -> Optional[str]:
    """
    Returns JSON (if supported by zramctl - not always available).
    """
    res = run(["zramctl", "--output-all", "--json"], check=False)
    if res.code == 0:
        return res.out
    return None


# ============ systemd wrappers ============

def systemd_daemon_reload() -> None:
    run(["systemctl", "daemon-reload"], check=True)


def systemd_restart(service: str) -> None:
    run(["systemctl", "restart", service], check=True)


def systemd_try_restart(service: str) -> Tuple[bool, Optional[str]]:
    r = run(["systemctl", "restart", service], check=False)
    if r.code == 0:
        return True, None
    return False, r.err.strip() or r.out.strip() or f"restart {service} failed"


# ============ discovery helpers ============

def parse_zramctl_table() -> List[Dict[str, Any]]:
    """
    Parse `zramctl` default table output using a "smarter split" that assumes
    only the last column (MOUNTPOINT) can contain spaces. This is more robust
    than fixed-width parsing if column spacing changes in future versions.
    """
    out = zramctl_info_all()
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if len(lines) < 2:
        return []

    # Get header columns, which we assume are always single words
    header = [col.upper().strip() for col in lines[0].split()]
    num_cols = len(header)
    devices: List[Dict[str, Any]] = []

    for ln in lines[1:]:
        # Split the line max (N-1) times. The last element will contain the rest of the line.
        parts = ln.split(maxsplit=num_cols - 1)
        
        # In case the last column is empty, parts will be shorter
        if len(parts) < num_cols - 1:
            continue # Skip malformed lines

        # Pad parts if mountpoint is missing, so zip works correctly
        while len(parts) < num_cols:
            parts.append("")

        row_data = dict(zip(header, parts))

        # --- VALIDATION START ---
        # Ensure critical fields match expected patterns
        name_val = row_data.get("NAME", "")
        if not name_val.startswith("/dev/zram"):
            continue

        # Size fields: digits + optional unit (B, K, M, G, T, P), or "-"
        # Example: "4G", "512M", "12K", "74B", "10.5M"
        size_pattern = re.compile(r"^(\d+(\.\d+)?[BKMGTP]?|-)$", re.IGNORECASE)
        
        valid_row = True
        for field in ["DISKSIZE", "DATA", "COMPR"]:
            val = row_data.get(field, "")
            if val and not size_pattern.match(val):
                valid_row = False
                break
        
        if not valid_row:
            continue
            
        # Streams: integer or "-"
        streams_val = row_data.get("STREAMS", "")
        if streams_val and streams_val != "-" and not streams_val.isdigit():
            continue
        # --- VALIDATION END ---

        # Map to our final structure
        name_path = row_data.get("NAME", "")
        device_data: Dict[str, Any] = {"name": os.path.basename(name_path) if name_path else "unknown"}
        device_data["disksize"] = row_data.get("DISKSIZE")
        device_data["data-size"] = row_data.get("DATA")
        device_data["compr-size"] = row_data.get("COMPR")
        device_data["algorithm"] = row_data.get("ALGORITHM")
        device_data["mountpoint"] = row_data.get("MOUNTPOINT")

        streams_str = row_data.get("STREAMS")
        try:
            device_data["streams"] = int(streams_str) if streams_str else None
        except (ValueError, TypeError):
            device_data["streams"] = None
        
        if device_data["name"] != "unknown":
            devices.append(device_data)

    return devices


def is_root() -> bool:
    """Checks if the script is running with root privileges."""
    return os.geteuid() == 0

def atomic_write_to_file(file_path: str, content: str) -> tuple[bool, str | None]:
    """Safely writes content to a system file using an atomic move operation."""
    try:
        dir_name = os.path.dirname(file_path)
        os.makedirs(dir_name, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        shutil.move(temp_path, file_path)
        os.chmod(file_path, 0o644)
        return True, None
    except Exception as e:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        return False, str(e)

def parse_size_to_bytes(size_str: str) -> int:
    """
    Converts a size string like '4G', '512M', '1GiB' to bytes.
    Handles B, K, M, G, T, P suffixes (and their iB/B variants).
    """
    if not isinstance(size_str, str):
        return 0
    
    s = size_str.strip().upper()
    if not s:
        return 0

    # Match number and optional unit
    # Groups: 1=number, 2=unit
    match = re.match(r"^(\d+(?:\.\d+)?)\s*([A-Z]+)?$", s)
    if not match:
        return 0
    
    number_str, unit_str = match.groups()
    try:
        value = float(number_str)
    except ValueError:
        return 0
        
    if not unit_str:
        return int(value)

    # Normalize unit: K, KB, KIB -> K
    # We assume binary prefixes (1024) for everything as is standard in system tools like zramctl
    unit = unit_str[0]
    
    multipliers = {
        'B': 1,
        'K': 1024,
        'M': 1024**2,
        'G': 1024**3,
        'T': 1024**4,
        'P': 1024**5
    }
    
    if unit in multipliers:
        return int(value * multipliers[unit])
        
    return 0
