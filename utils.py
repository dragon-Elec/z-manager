# zman/utils.py
import shutil
import os
import tempfile
from typing import List, Dict, Any

# Prefer core system primitives; utils will no longer duplicate them.
from .core.system import (
    run as core_run,
    is_block_device as core_is_block_device,
    sysfs_read as core_sysfs_read,
    sysfs_write as core_sysfs_write,
)
# Device listings should come from core
from .core.devices import list_devices

def format_bytes(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0B"
    size_names = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

def run_command(command: str) -> tuple[str, str, int]:
    """Executes a shell command via core.system.run to keep a single subprocess implementation."""
    try:
        res = core_run(["/bin/sh", "-lc", command], check=False)
        return (res.out.strip(), res.err.strip(), res.code)
    except Exception as e:
        return ("", str(e), -1)

def is_command_available(command: str) -> bool:
    """Checks if a command is available in the system's PATH."""
    return shutil.which(command) is not None

def is_root() -> bool:
    """Checks if the script is running with root privileges."""
    return os.geteuid() == 0

def get_swappiness() -> int | None:
    """Reads the current system swappiness value."""
    stdout, _, returncode = run_command("cat /proc/sys/vm/swappiness")
    if returncode == 0 and stdout:
        try:
            return int(stdout.strip())
        except (ValueError, TypeError):
            return None
    return None

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

def read_file_content(file_path: str) -> str | None:
    """
    Safely reads the RAW content of a file, returning None if not found.
    The calling function is responsible for stripping whitespace if needed.
    """
    try:
        with open(file_path, 'r') as f:
            return f.read() # Return raw, unmodified content
    except FileNotFoundError:
        return None

def _parse_size_to_bytes(size_str: str) -> int:
    """Converts a size string like '4G' or '512M' to bytes."""
    if not isinstance(size_str, str):
        return 0
    size_str = size_str.upper().strip()
    unit_multipliers = {'B': 1, 'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
    unit = size_str[-1] if size_str else ''
    if unit in unit_multipliers:
        try:
            numeric_part = size_str[:-1].strip()
            value = float(numeric_part)
            return int(value * unit_multipliers[unit])
        except (ValueError, IndexError):
            return 0
    try:
        return int(size_str)
    except (ValueError, TypeError):
        return 0

def _calculate_ratio(data_size: int, compr_size: int) -> str:
    """Calculates and formats the compression ratio."""
    if compr_size == 0:
        return "N/A"
    ratio = data_size / compr_size
    return f"{ratio:.2f}x"

# Delegate block device check to core to avoid duplication
def is_block_device(path: str) -> bool:
    return core_is_block_device(path)

def get_zram_sysfs(device_name: str) -> str:
    """Return /sys/block/zramN path for the device name like 'zram0'."""
    return f"/sys/block/{device_name}"

def read_sysfs(path: str) -> str | None:
    """Read a sysfs path using core helper (returns stripped text or None)."""
    return core_sysfs_read(path)

def write_sysfs(path: str, value: str) -> tuple[bool, str | None]:
    """Write to a sysfs path via core helper."""
    return core_sysfs_write(path, value)

def compute_zram_writeback_status(device_name: str) -> Dict[str, Any]:
    """
    Read useful writeback-related sysfs for the device and return a dict suitable for GUI.
    """
    sysfs = get_zram_sysfs(device_name)
    fields = {
        "backing_dev": "backing_dev",
        "orig_data_size": "orig_data_size",
        "compr_data_size": "compr_data_size",
        "mem_used_total": "mem_used_total",
        "num_wb": "num_writeback",
        "num_wb_fail": "writeback_failed",
        "num_pages": "pages",
        "discard": "discard",
    }
    out: Dict[str, Any] = {"device": device_name}
    for key, fname in fields.items():
        content = read_sysfs(os.path.join(sysfs, fname))
        out[key] = content.strip() if content is not None else None
    return out
