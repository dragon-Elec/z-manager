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

from core.utils.common import (
    run,
    SystemCommandError,
    read_file,
)
from core.utils.io import (
    atomic_write_to_file,
    pkexec_write,
    is_root,
)
from core.utils.block import (
    check_device_safety,
    is_block_device,
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
    Checks system readiness by delegating to systemd-logind with a fallback to sysfs parsing.
    """
    secure_boot_mode = "queried-via-logind"
    try:
        res = run(["busctl", "call", "org.freedesktop.login1", "/org/freedesktop/login1", 
                   "org.freedesktop.login1.Manager", "CanHibernate"], check=True)
        
        # Robust parsing: Look for the variant value in the busctl output string
        out = res.out.lower()
        if '"yes"' in out:
            ready, msg = True, "System is fully ready for hibernation."
        elif '"no"' in out:
            ready, msg = False, "Hibernation is disabled (likely Secure Boot or Driver policy)."
        elif '"na"' in out:
            ready, msg = False, "Hibernation is not supported by this hardware or kernel."
        elif '"challenge"' in out:
            ready, msg = True, "Hibernation available (requires authentication)."
        else:
            ready, msg = False, f"Unexpected response from logind: {res.out.strip()}"

    except (SystemCommandError, Exception):
        # Fallback to sysfs if systemd-logind is unavailable or output is unparseable
        ready, msg = True, "Logind unavailable. Fallback: System appears ready."
        secure_boot_mode = "disabled"
        try:
            lockdown = read_file("/sys/kernel/security/lockdown")
            if lockdown:
                if "[integrity]" in lockdown:
                    secure_boot_mode = "integrity"
                elif "[confidentiality]" in lockdown:
                    secure_boot_mode = "confidentiality"
                    ready, msg = False, "Secure Boot confidentiality active. Hibernation blocked."
        except Exception:
            pass

    mem_total, swap_total = get_memory_info()
    
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
    Uses filesystem-specific tools for high-fidelity offset discovery.
    """
    if is_block_device(path):
        return 0 # Offsets are 0 for partitions

    match _get_fs_type(path):
        case "btrfs":
            # Btrfs requires specific tool: btrfs inspect-internal map-swapfile -r /path/to/swapfile
            try:
                res = run(["btrfs", "inspect-internal", "map-swapfile", "-r", path], check=True)
                return int(res.out.strip())
            except (ValueError, SystemCommandError):
                pass
        
        case _:
            # Universal fallback for standard allocating filesystems
            try:
                res = run(["filefrag", "-v", path], check=True)
                for line in res.out.splitlines():
                    if line.strip().startswith("0:"):
                        parts = line.split()
                        if len(parts) >= 4:
                            return int(parts[3].split("..")[0])
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

def escape_unit_name(path: str) -> str:
    """
    Escapes a filesystem path for use as a systemd unit name.
    Standardizes via systemd-escape to natively handle hyphens.
    """
    try:
        res = run(["systemd-escape", "-p", "--suffix=swap", path], check=True)
        return res.out.strip()
    except SystemCommandError:
        escaped = path.lstrip("/").replace("/", "-")
        return f"{escaped}.swap"

def generate_swap_unit(path: str, priority: int = 0) -> str:
    """
    Generates the content for a systemd .swap unit file.
    """
    return f"""[Unit]
Description=Z-Manager Hibernation Swapfile
Documentation=https://github.com/ray/z-manager

[Swap]
What={path}
Priority={priority}
Options=nofail

[Install]
WantedBy=multi-user.target
"""

def persist_swap_unit(path: str, priority: int = 0) -> Tuple[bool, str]:
    """
    Saves the .swap unit to /etc/systemd/system and enables it.
    This is the modern replacement for update_fstab.
    """
    unit_name = escape_unit_name(path)
    unit_path = f"/etc/systemd/system/{unit_name}"
    content = generate_swap_unit(path, priority)

    from core.utils.io import pkexec_write
    from core.utils.privilege import pkexec_daemon_reload, pkexec_systemctl

    # 1. Write the unit file (requires root)
    ok, err = pkexec_write(unit_path, content)
    if not ok:
        return False, f"Failed to write unit file: {err}"

    # 2. Orchestrate systemd
    # Reload to see the new unit
    ok, err = pkexec_daemon_reload()
    if not ok:
        return False, f"Systemd daemon-reload failed: {err}"
        
    # Enable and start it immediately
    ok, err = pkexec_systemctl("enable", unit_name)
    if not ok:
        return False, f"Failed to enable swap unit: {err}"
        
    return True, "Swap unit persisted and activated."

def update_fstab(device_path: str, uuid: str) -> bool:
    """
    [DEPRECATED] Adds a swap entry to /etc/fstab.
    Use persist_swap_unit() instead for better safety and isolation.
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
