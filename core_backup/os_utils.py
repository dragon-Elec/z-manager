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


# ============ Safety helpers ============

def get_device_filesystem_type(device_path: str) -> Optional[str]:
    """
    Detects if a block device has an existing filesystem using 'blkid'.
    Returns the TYPE string (e.g., 'ext4', 'swap', 'ntfs') or None if safe/unknown.
    """
    if not is_block_device(device_path):
        return None

    # blkid -o value -s TYPE /dev/sdX
    # Returns raw type string on stdout, or nothing if no signature found.
    # Exit code can be 2 if not found, so we don't 'check=True'.
    res = run(["blkid", "-o", "value", "-s", "TYPE", device_path])
    
    if res.code == 0 and res.out.strip():
        return res.out.strip()
    return None


def check_device_safety(device_path: str) -> Tuple[bool, str]:
    """
    Checks if a device is safe to use for writeback (i.e., has no filesystem).
    Returns (True, "") if safe, or (False, reason) if unsafe.
    """
    fs_type = get_device_filesystem_type(device_path)
    if fs_type:
        return False, f"Device {device_path} contains a '{fs_type}' filesystem. usage would cause data loss."
    return True, ""


# ============ Block Device Discovery ============

def list_block_devices() -> List[Dict[str, Any]]:
    """
    List all block devices suitable for selection.
    Uses 'lsblk' JSON output for robust parsing.
    Returns a list of dicts with keys: name, path, size, type, label, fstype, mountpoint.
    """
    cmd = ["lsblk", "-J", "-o", "NAME,PATH,SIZE,TYPE,LABEL,FSTYPE,MOUNTPOINT,MODEL"]
    
    try:
        # Check=False because lsblk might return non-zero if some devices fail (rare but safe)
        res = run(cmd, check=False)
        if res.code != 0:
            logging.error(f"lsblk failed: {res.err}")
            return []
            
        import json
        data = json.loads(res.out)
        
        # lsblk returns a dict with key "blockdevices" which is a list
        devices = data.get("blockdevices", [])
        
        # Flatten the list if there are children partitions (lsblk tree structure)
        # We want a flat list of all selectable nodes
        flat_list = []
        
        def recurse(dev_list):
            for d in dev_list:
                # We are interested in identifying info
                info = {
                    "name": d.get("name"),             # e.g. "sda1"
                    "path": d.get("path"),             # e.g. "/dev/sda1"
                    "size": d.get("size"),             # e.g. "500G"
                    "type": d.get("type"),             # e.g. "part", "disk", "loop"
                    "label": d.get("label"),           # e.g. "Data"
                    "fstype": d.get("fstype"),         # e.g. "ext4", "swap"
                    "mountpoint": d.get("mountpoint"), # e.g. "/" or None
                    "model": d.get("model")            # e.g. "Samsung SSD..."
                }
                
                # Filter out zram devices themselves to avoid recursion loops
                if info["name"] and info["name"].startswith("zram"):
                    continue
                    
                flat_list.append(info)
                
                # Process children (partitions)
                if "children" in d:
                    recurse(d["children"])

        recurse(devices)
        return flat_list

    except json.JSONDecodeError:
        logging.error("Failed to parse lsblk output")
        return []
    except Exception as e:
        logging.error(f"Error listing block devices: {e}")
        return []


# ============ I/O Scheduler helpers ============

def get_device_scheduler(device_name: str) -> Tuple[str, List[str]]:
    """
    Reads the I/O scheduler for a block device (e.g., 'sda', 'nvme0n1').
    Returns (current_scheduler, available_schedulers).
    Example return: ('mq-deadline', ['none', 'mq-deadline', 'kyber'])
    """
    # Scheduler is at /sys/block/{name}/queue/scheduler
    # Format: [mq-deadline] kyber bfq none
    
    # Handle /dev prefix if passed
    name = device_name.replace("/dev/", "")
    
    path = f"/sys/block/{name}/queue/scheduler"
    content = read_file(path)
    if not content:
        return "unknown", []

    # Parse content
    schedulers = []
    current = "none" # Default fallback
    
    for item in content.split():
        if item.startswith("[") and item.endswith("]"):
            clean = item[1:-1]
            current = clean
            schedulers.append(clean)
        else:
            schedulers.append(item)
            
    return current, schedulers


def set_device_scheduler(device_name: str, scheduler: str) -> bool:
    """
    Sets the I/O scheduler for a block device.
    """
    name = device_name.replace("/dev/", "")
    path = f"/sys/block/{name}/queue/scheduler"
    
    try:
        sysfs_write(path, scheduler)
        return True
    except (IOError, OSError) as e:
        logging.error(f"Failed to set scheduler {scheduler} for {name}: {e}")
        return False


# ============ sysfs-based zram device discovery ============


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


def _scan_zram_devices() -> List[str]:
    """
    Scan /sys/block/ for zram devices and return their names.
    
    Returns:
        List of device names like ['zram0', 'zram1']
    """
    devices: List[str] = []
    sys_block = Path("/sys/block")
    
    if not sys_block.exists():
        return devices
    
    try:
        for entry in sys_block.iterdir():
            if entry.is_dir() and entry.name.startswith("zram"):
                devices.append(entry.name)
    except (OSError, PermissionError):
        pass
    
    # Sort numerically by device number
    devices.sort(key=lambda x: int(x[4:]) if x[4:].isdigit() else 0)
    return devices


def _read_zram_sysfs_props(device_name: str) -> Dict[str, Any]:
    """
    Read all zram properties from sysfs for a single device.
    
    Returns dict with keys matching the old zramctl output format:
    - name, disksize, data-size, compr-size, total-size, algorithm, streams, mountpoint
    """
    sysfs_base = Path(f"/sys/block/{device_name}")
    props: Dict[str, Any] = {"name": device_name}
    
    # Read disksize (in bytes)
    disksize_bytes = read_file(sysfs_base / "disksize")
    if disksize_bytes and disksize_bytes != "0":
        props["disksize"] = _bytes_to_human(int(disksize_bytes))
    else:
        props["disksize"] = "-"
    
    # Try reading mm_stat first (consolidated stats on modern kernels)
    # Format: orig_data_size compr_data_size mem_used_total mem_limit mem_used_max same_pages pages_compacted huge_pages ...
    mm_stat = read_file(sysfs_base / "mm_stat")
    if mm_stat:
        parts = mm_stat.split()
        if len(parts) >= 3:
            props["data-size"] = _bytes_to_human(int(parts[0]))
            props["compr-size"] = _bytes_to_human(int(parts[1]))
            props["total-size"] = _bytes_to_human(int(parts[2]))
        else:
            props["data-size"] = "-"
            props["compr-size"] = "-"
            props["total-size"] = "-"
        
        if len(parts) >= 7:
            props["mem-limit"] = _bytes_to_human(int(parts[3]))
            props["mem-used-max"] = _bytes_to_human(int(parts[4]))
            props["same-pages"] = parts[5] # Count
        else:
            props["mem-limit"] = "-"
            props["mem-used-max"] = "-"
            props["same-pages"] = "-"

    else:
        # Fallback to individual files (legacy kernels)
        
        # Read orig_data_size (uncompressed data in bytes)
        orig_data = read_file(sysfs_base / "orig_data_size")
        if orig_data:
            props["data-size"] = _bytes_to_human(int(orig_data))
        else:
            props["data-size"] = "-"
        
        # Read compr_data_size (compressed data in bytes)
        compr_data = read_file(sysfs_base / "compr_data_size")
        if compr_data:
            props["compr-size"] = _bytes_to_human(int(compr_data))
        else:
            props["compr-size"] = "-"
        
        # Read mem_used_total (total memory used in bytes)
        mem_used = read_file(sysfs_base / "mem_used_total")
        if mem_used:
            props["total-size"] = _bytes_to_human(int(mem_used))
        else:
            props["total-size"] = "-"
        
        # Legacy defaults for extended fields
        props["mem-limit"] = "-"
        props["mem-used-max"] = "-"
        props["same-pages"] = "-"

    # Read bd_stat for actual writeback data (Migrated)
    # Format: bd_count bd_reads bd_writes
    bd_stat = read_file(sysfs_base / "bd_stat")
    if bd_stat:
        parts = bd_stat.split()
        if len(parts) >= 3:
            # Column 3 (index 2) is bd_writes (pages written to backing device)
            # Convert pages to bytes (PAGE_SIZE=4096)
            props["migrated"] = _bytes_to_human(int(parts[2]) * 4096)
        else:
            props["migrated"] = "0B"
    else:
        props["migrated"] = "0B"
    
    # Read compression algorithm (format: [lz4])
    algo_raw = read_file(sysfs_base / "comp_algorithm")
    if algo_raw:
        # Extract the active algorithm from bracketed format like "[lz4] lzo lzo-rle"
        import re
        match = re.search(r'\[([^\]]+)\]', algo_raw)
        if match:
            props["algorithm"] = match.group(1)
        else:
            props["algorithm"] = algo_raw.split()[0] if algo_raw else None
    else:
        props["algorithm"] = None
    
    # Read max_comp_streams
    streams_str = read_file(sysfs_base / "max_comp_streams")
    try:
        props["streams"] = int(streams_str) if streams_str else None
    except (ValueError, TypeError):
        props["streams"] = None
    
    # Check mountpoint from /proc/swaps
    props["mountpoint"] = _get_zram_mountpoint(device_name)
    
    # Calculate compression ratio
    props["ratio"] = _calculate_compression_ratio(
        props.get("data-size"),
        props.get("compr-size")
    )
    
    return props


def _bytes_to_human(size_bytes: int) -> str:
    """Convert bytes to human-readable format matching zramctl output (B, K, M, G, T, P)."""
    if size_bytes == 0:
        return "0B"
    
    units = ['B', 'K', 'M', 'G', 'T', 'P']
    unit_idx = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_idx < len(units) - 1:
        size /= 1024
        unit_idx += 1
    
    # Format: if it's a whole number, no decimal; otherwise 1 decimal place
    if size == int(size):
        return f"{int(size)}{units[unit_idx]}"
    else:
        return f"{size:.1f}{units[unit_idx]}"


def _get_zram_mountpoint(device_name: str) -> str:
    """Check if zram device is used as swap or mounted."""
    dev_path = f"/dev/{device_name}"
    
    # Check /proc/swaps first
    try:
        with open("/proc/swaps", "r") as f:
            for line in f:
                if dev_path in line:
                    return "[SWAP]"
    except (IOError, OSError):
        pass
    
    # Check /proc/mounts
    try:
        with open("/proc/mounts", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[0] == dev_path:
                    return parts[1]  # mount point
    except (IOError, OSError):
        pass
    
    return ""


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
    Parse zram devices using sysfs instead of zramctl command.
    
    Returns list of device dicts with keys: name, disksize, data-size, compr-size,
    total-size, algorithm, streams, mountpoint, ratio
    
    This function maintains API compatibility with the old zramctl-based parser.
    """
    devices: List[Dict[str, Any]] = []
    
    for device_name in _scan_zram_devices():
        try:
            props = _read_zram_sysfs_props(device_name)
            # Only include devices that have been configured (disksize > 0)
            if props.get("disksize") and props["disksize"] != "-":
                devices.append(props)
        except (OSError, ValueError) as e:
            _PARSER_LOGGER.debug(f"Error reading {device_name}: {e}")
            continue
    
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
