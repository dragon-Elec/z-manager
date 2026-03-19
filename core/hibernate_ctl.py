# zman/core/hibernate_ctl.py

from __future__ import annotations

import logging
import os
import re
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

from core.os_utils import (
    run,
    SystemCommandError,
    atomic_write_to_file,
    read_file,
    check_device_safety,
    is_block_device,
    pkexec_write,
    is_root,
)

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class HibernateCheckResult:
    ready: bool
    secure_boot: str # "disabled", "integrity", "confidentiality"
    swap_total: int
    ram_total: int
    message: str

@dataclass(frozen=True)
class SwapCreationResult:
    success: bool
    path: str
    uuid: Optional[str]
    offset: Optional[int]
    message: str

def get_memory_info() -> Tuple[int, int]:
    """Returns (ram_total, swap_total) in bytes from /proc/meminfo."""
    mem_total = 0
    swap_total = 0
    try:
        content = read_file("/proc/meminfo")
        if content:
            for line in content.splitlines():
                if line.startswith("MemTotal:"):
                    # value is in kB
                    parts = line.split()
                    if len(parts) >= 2:
                        mem_total = int(parts[1]) * 1024
                elif line.startswith("SwapTotal:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        swap_total = int(parts[1]) * 1024
    except Exception:
        pass
    return mem_total, swap_total

def check_hibernation_readiness() -> HibernateCheckResult:
    """
    Checks basic system readiness for hibernation.
    """
    # 1. Check Secure Boot
    secure_boot_mode = "disabled"
    try:
        # Check kernel lockdown mode
        lockdown = read_file("/sys/kernel/security/lockdown")
        if lockdown:
            # Format: [none] integrity confidentiality
            if "[integrity]" in lockdown:
                secure_boot_mode = "integrity"
            elif "[confidentiality]" in lockdown:
                secure_boot_mode = "confidentiality"
            elif "integrity" in lockdown: # active but not bracketed in some formats?
                 # Double check with efivars if possible, but sysfs is source of truth for kernel restrictions
                 pass
    except Exception:
        pass

    # 2. Check Memory Fitness
    mem_total, swap_total = get_memory_info()
    
    # Heuristic: We need at least 1/2 RAM in swap (compressed) or full RAM ideally.
    # For safe hibernation, Swap should ideally be >= RAM * 0.6 (assuming compression)
    # But strictly speaking, if Swap < RAM usage, it fails.
    # We'll just report the values for the UI to warn.
    
    ready = True
    msg = "System appears ready."
    
    if secure_boot_mode == "confidentiality":
        ready = False
        msg = "Secure Boot 'confidentiality' mode is active. Hibernation is blocked by kernel."

    return HibernateCheckResult(
        ready=ready,
        secure_boot=secure_boot_mode,
        swap_total=swap_total,
        ram_total=mem_total,
        message=msg
    )

def _get_fs_type(path: str) -> Optional[str]:
    """Detect filesystem type of the directory containing the path."""
    # We use `df -T` on the directory
    directory = os.path.dirname(path)
    try:
        res = run(["df", "-T", directory], check=False)
        if res.code == 0:
            # Output:
            # Filesystem     Type     1K-blocks  Used Available Use% Mounted on
            # /dev/sda2      ext4     ...
            lines = res.out.strip().splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 2:
                    return parts[1]
    except Exception:
        pass
    return None

def get_resume_offset(path: str) -> Optional[int]:
    """
    Calculate the physical offset of the swapfile for the kernel resume parameter.
    """
    if is_block_device(path):
        return 0 # Offsets are 0 for partitions

    fs_type = _get_fs_type(path)
    
    if fs_type == "btrfs":
        # Btrfs requires specific tool
        try:
            # btrfs inspect-internal map-swapfile -r /path/to/swapfile
            res = run(["btrfs", "inspect-internal", "map-swapfile", "-r", path], check=False)
            if res.code == 0:
                return int(res.out.strip())
        except (ValueError, SystemCommandError):
            pass
        return None
        
    else:
        # Standard Ext4/XFS use filefrag
        try:
            # filefrag -v /swapfile
            # output format:
            # Filesystem type is: ef53
            # File size of /swapfile is ...
            # ext:     logical_offset:        physical_offset: length:   expected: flags:
            #   0:        0..       0:      34816..     34816:      1:
            res = run(["filefrag", "-v", path], check=False)
            if res.code == 0:
                # We need the first physical offset value from line with "0:"
                for line in res.out.splitlines():
                    if line.strip().startswith("0:"):
                        # Parts might look like: "0:", "0..", "0:", "34816..", "34816:", "1:"
                        # We want the 4th column roughly (physical_offset range start)
                        parts = line.split()
                        if len(parts) >= 4:
                            phys_range = parts[3] # e.g. "34816..34816" or "34816"
                            val = phys_range.split("..")[0]
                            return int(val)
        except (ValueError, SystemCommandError, IndexError):
            pass
            
    return None

def get_partition_uuid(path: str) -> Optional[str]:
    """Get UUID of a partition or the device holding a file."""
    target_dev = path
    if not is_block_device(path):
        # Find the device holding the file
        try:
            res = run(["df", "--output=source", path], check=False)
            if res.code == 0:
                lines = res.out.strip().splitlines()
                if len(lines) >= 2:
                    target_dev = lines[1]
        except Exception:
            return None

    # Now get UUID of target_dev
    try:
        res = run(["blkid", "-s", "UUID", "-o", "value", target_dev], check=False)
        if res.code == 0:
            return res.out.strip()
    except Exception:
        pass
    return None

def create_swapfile(path: str, size_mb: int) -> SwapCreationResult:
    """
    Creates a swapfile safely.
    Handles Btrfs COW disabling.
    """
    # 1. Verification
    if os.path.exists(path):
        if is_block_device(path):
             return SwapCreationResult(False, path, None, None, "Path is an existing block device. Use it directly.")
        # If it's a file, we could overwrite, but let's be safe
        # Ideally user should delete it first or we rename it?
        # For now, let's proceed to overwrite if it's just a file
    
    fs_type = _get_fs_type(os.path.dirname(path))
    
    try:
        # 2. Preparation (Btrfs specific)
        if fs_type == "btrfs":
            # Btrfs requires: zero length file -> NoCOW -> allocation
            run(["truncate", "-s", "0", path], check=True)
            run(["chattr", "+C", path], check=True)
        
        # 3. Allocation
        # Use fallocate for speed if supported, else dd
        # ext4 supports fallocate. btrfs supports fallocate (kernel 5.0+)
        try:
             run(["fallocate", "-l", f"{size_mb}M", path], check=True)
        except SystemCommandError:
             # Fallback to dd
             run(["dd", "if=/dev/zero", f"of={path}", "bs=1M", f"count={size_mb}", "status=progress"], check=True)

        # 4. Permissions
        os.chmod(path, 0o600)

        # 5. Format
        run(["mkswap", path], check=True)

    except (SystemCommandError, OSError) as e:
        # Cleanup
        if os.path.exists(path) and os.path.isfile(path) and os.path.getsize(path) == 0:
            os.remove(path)
        return SwapCreationResult(False, path, None, None, str(e))

    # 6. Gather Info
    uuid = get_partition_uuid(path)
    offset = get_resume_offset(path)
    
    return SwapCreationResult(True, path, uuid, offset, "Swapfile created successfully.")


def enable_swapon(path: str, priority: int = 0) -> bool:
    try:
        run(["swapon", "-p", str(priority), path], check=True)
        return True
    except SystemCommandError:
        return False

def update_fstab(device_path: str, uuid: str) -> bool:
    """
    Adds a swap entry to /etc/fstab with 'nofail' and priority 0.
    """
    fstab_path = "/etc/fstab"
    
    # Construct entry
    # Ident: UUID=... preferred
    ident = f"UUID={uuid}"
    
    # Check if already exists
    current = read_file(fstab_path) or ""
    if ident in current and "swap" in current:
        return True # Already there

    # Entry format: UUID=... none swap sw,pri=0,nofail 0 0
    # Use tabs for alignment
    new_line = f"{ident}\t\tnone\t\tswap\t\tsw,pri=0,nofail\t0 0\n"
    
    # Append
    # This requires root.
    if is_root():
        try:
            with open(fstab_path, "a") as f:
                f.write(new_line)
            return True
        except Exception:
            return False
            
    # Try pkexec helper
    # Our helper currently only supports 'write' which overwrites.
    # We need to read, append, and write back.
    # This is slightly racy but acceptable for fstab updates usually.
    new_content = current + new_line
    success, err = pkexec_write(fstab_path, new_content)
    if not success:
        _LOGGER.error(f"Failed to update fstab: {err}")
    return success
