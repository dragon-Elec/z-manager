# zman/core/os_utils.py

from __future__ import annotations

import logging
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

# Pre-compiled regex patterns for zramctl output validation (performance optimization)
# Size fields: digits + optional decimal + unit (B, K, M, G, T, P), or "-" for empty
# Examples: "4G", "512M", "12K", "74B", "10.5M", "1.5G", "-"
_SIZE_PATTERN = re.compile(r"^(\d+(\.\d+)?[BKMGTP]?|-)$", re.IGNORECASE)

# Known compression algorithms supported by the Linux kernel zram module
# This list should be updated if new algorithms are added to the kernel
_KNOWN_ALGORITHMS = frozenset({
    "lzo", "lzo-rle", "lz4", "lz4hc", "zstd", "deflate", "842"
})

_PARSER_LOGGER = logging.getLogger(__name__)


def _calculate_compression_ratio(data_size_str: Optional[str], compr_size_str: Optional[str]) -> Optional[float]:
    """
    Calculate compression ratio from data-size and compr-size strings.
    
    Args:
        data_size_str: Original data size (e.g., "4K", "1M", "-")
        compr_size_str: Compressed data size (e.g., "74B", "500K", "-")
    
    Returns:
        Compression ratio as float (e.g., 2.5 means 2.5:1 compression),
        or None if calculation is not possible (missing/invalid data).
    """
    if not data_size_str or not compr_size_str:
        return None
    if data_size_str == "-" or compr_size_str == "-":
        return None
    
    # Import locally to avoid circular dependency issues
    data_bytes = parse_size_to_bytes(data_size_str)
    compr_bytes = parse_size_to_bytes(compr_size_str)
    
    if compr_bytes == 0:
        # Avoid division by zero; if compressed size is 0, ratio is undefined
        return None if data_bytes == 0 else float('inf')
    
    return round(data_bytes / compr_bytes, 2)


def parse_zramctl_table() -> List[Dict[str, Any]]:
    """
    Parse `zramctl` default table output into a list of device dictionaries.
    
    Uses a "smarter split" strategy that assumes only the last column (MOUNTPOINT)
    can contain spaces. This is more robust than fixed-width parsing if column
    spacing changes in future zramctl versions.
    
    Validation:
        - NAME must start with /dev/zram
        - DISKSIZE, DATA, COMPR, TOTAL must be valid size strings or "-"
        - STREAMS must be an integer or "-"
        - ALGORITHM should be a known compression algorithm (warns if unknown)
    
    Returns:
        List of device dicts with keys: name, disksize, data-size, compr-size,
        total-size, algorithm, streams, mountpoint
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
            _PARSER_LOGGER.debug(f"Skipping malformed line (too few columns): {ln!r}")
            continue

        # Pad parts if mountpoint is missing, so zip works correctly
        while len(parts) < num_cols:
            parts.append("")

        row_data = dict(zip(header, parts))

        # --- VALIDATION START ---
        # Ensure critical fields match expected patterns
        name_val = row_data.get("NAME", "")
        if not name_val.startswith("/dev/zram"):
            _PARSER_LOGGER.debug(f"Skipping line (invalid NAME): {ln!r}")
            continue

        # Validate size fields
        valid_row = True
        for field in ["DISKSIZE", "DATA", "COMPR", "TOTAL"]:
            val = row_data.get(field, "")
            if val and not _SIZE_PATTERN.match(val):
                _PARSER_LOGGER.debug(f"Skipping line (invalid {field}={val!r}): {ln!r}")
                valid_row = False
                break
        
        if not valid_row:
            continue
            
        # Streams: integer or "-"
        streams_val = row_data.get("STREAMS", "")
        if streams_val and streams_val != "-" and not streams_val.isdigit():
            _PARSER_LOGGER.debug(f"Skipping line (invalid STREAMS={streams_val!r}): {ln!r}")
            continue
        
        # Algorithm: warn if unknown (but don't reject - could be a new kernel algorithm)
        algorithm_val = row_data.get("ALGORITHM", "")
        if algorithm_val and algorithm_val.lower() not in _KNOWN_ALGORITHMS:
            _PARSER_LOGGER.warning(f"Unknown compression algorithm: {algorithm_val!r}")
        # --- VALIDATION END ---

        # Map to our final structure
        name_path = row_data.get("NAME", "")
        device_data: Dict[str, Any] = {"name": os.path.basename(name_path) if name_path else "unknown"}
        device_data["disksize"] = row_data.get("DISKSIZE")
        device_data["data-size"] = row_data.get("DATA")
        device_data["compr-size"] = row_data.get("COMPR")
        device_data["total-size"] = row_data.get("TOTAL")  # Added TOTAL column
        device_data["algorithm"] = row_data.get("ALGORITHM")
        device_data["mountpoint"] = row_data.get("MOUNTPOINT")

        streams_str = row_data.get("STREAMS")
        try:
            device_data["streams"] = int(streams_str) if streams_str else None
        except (ValueError, TypeError):
            device_data["streams"] = None
        
        # Calculate compression ratio from data-size and compr-size
        # Ratio = original_size / compressed_size (higher is better compression)
        device_data["ratio"] = _calculate_compression_ratio(
            device_data.get("data-size"),
            device_data.get("compr-size")
        )
        
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
