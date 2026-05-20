#!/usr/bin/env python3
"""
zman-helper.py - Privileged helper for Z-Manager

This script is designed to be called via pkexec to perform
operations that require root privileges.
"""

import sys
import os
import subprocess
import shutil
import tempfile
import json

# Allowed paths for write operations (security whitelist)
ALLOWED_WRITE_PATHS = [
    "/etc/systemd/zram-generator.conf",
    "/etc/sysctl.d/99-z-manager.conf",
    "/etc/default/grub.d/99-z-manager-disable-zswap.cfg",
    "/etc/default/grub.d/98-z-manager-enable-psi.cfg",
    "/etc/default/grub.d/99-z-manager-resume.cfg",
    "/etc/initramfs-tools/conf.d/resume",
    "/etc/tmpfiles.d/99-z-manager-hibernation.conf",
    "/swapfile",
]

# Allowed service patterns for systemctl operations
ALLOWED_SERVICE_PATTERNS = [
    "systemd-zram-setup@zram",  # Matches zram0, zram1, etc.
]


def is_path_allowed(path: str) -> bool:
    """Check if the path is in the whitelist or a common swap location."""
    if path in ALLOWED_WRITE_PATHS:
        return True
    if path.endswith(".swap") and path.startswith("/etc/systemd/system/"):
        return True
    return False


def is_service_allowed(service: str) -> bool:
    """Check if the service matches allowed patterns or is a swap unit."""
    for pattern in ALLOWED_SERVICE_PATTERNS:
        if service.startswith(pattern):
            return True
    if service.endswith(".swap"):
        return True
    return False


def _atomic_write(path: str, content: str) -> bool:
    """Internal helper for atomic writes with backup."""
    if not is_path_allowed(path):
        print(f"Error: Path not allowed: {path}", file=sys.stderr)
        return False
    try:
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        if os.path.exists(path):
            shutil.copy2(path, f"{path}.bak")
        fd, temp_path = tempfile.mkstemp(dir=dir_name or ".", text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
            shutil.move(temp_path, path)
            os.chmod(path, 0o644)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
        return True
    except Exception as e:
        print(f"Error writing to {path}: {e}", file=sys.stderr)
        return False


def cmd_write(path: str) -> int:
    """Write content from stdin to path atomically."""
    content = sys.stdin.read()
    return 0 if _atomic_write(path, content) else 1


def _get_resume_offset(path: str) -> str:
    """Internal helper to calculate physical offset for resume."""
    if path.startswith("/dev/"): return "0"
    
    # 1. Detect Filesystem Type
    fs_type = "unknown"
    try:
        parent_dir = os.path.dirname(path) or "/"
        res = subprocess.run(["df", "-T", parent_dir], capture_output=True, text=True, check=True)
        lines = res.stdout.strip().splitlines()
        if len(lines) >= 2:
            fs_type = lines[1].split()[1]
    except Exception:
        pass

    # 2. Filesystem-specific Offset Calculations
    if fs_type == "btrfs":
        try:
            res = subprocess.run(["btrfs", "inspect-internal", "map-swapfile", "-r", path], capture_output=True, text=True, check=True)
            return res.stdout.strip()
        except Exception:
            pass

    try:
        # Try filefrag (standard)
        res = subprocess.run(["filefrag", "-v", path], capture_output=True, text=True, check=True)
        for line in res.stdout.splitlines():
            if line.strip().startswith("0:"):
                return line.split()[3].split("..")[0]
    except Exception:
        pass
    return "0"


def _check_device_safety(device_path: str) -> tuple[bool, str]:
    """Verify if device is safe for write operations (no filesystem)."""
    if not device_path.startswith("/dev/"):
        return True, ""
    try:
        # blkid -p (low-level probe) returns 2 if no filesystem found
        res = subprocess.run(["blkid", "-p", device_path], capture_output=True, text=True)
        if res.returncode == 0:
            # Check for TYPE= in output
            if "TYPE=" in res.stdout:
                import re
                m = re.search(r'TYPE="([^"]+)"', res.stdout)
                fs = m.group(1) if m else "unknown"
                if fs == "swap": return True, "" # Swap is safe to reuse
                return False, f"Device contains a '{fs}' filesystem."
        elif res.returncode == 2:
            return True, "" # No filesystem found
        return False, f"Safety check failed (code {res.returncode})"
    except Exception as e:
        return False, str(e)


def cmd_hibernate_setup() -> int:
    """
    Master Transaction for Hibernation Setup.
    Reads a JSON plan from stdin and executes all steps with transparency.
    """
    try:
        plan = json.load(sys.stdin)
        
        # 1. Swap Provisioning
        path = plan['swap_path']
        print(f">> STEP: Provisioning Storage ({path})", flush=True)
        is_block = path.startswith("/dev/")
        
        # --- CRITICAL SAFETY CHECK ---
        safe, reason = _check_device_safety(path)
        if not safe:
            print(f"!! SAFETY VIOLATION: {reason}", file=sys.stderr, flush=True)
            return 1
        # -----------------------------
        if not is_block:
            if plan.get('fs_type') == "btrfs":
                print("   Executing: btrfs NoCOW setup...", flush=True)
                subprocess.run(["truncate", "-s", "0", path], check=True)
                subprocess.run(["chattr", "+C", path], check=True)
            
            print(f"   Executing: Allocating {plan['size_mb']}MB...", flush=True)
            try:
                subprocess.run(["fallocate", "-l", f"{plan['size_mb']}M", path], check=True)
            except subprocess.CalledProcessError:
                subprocess.run(["dd", "if=/dev/zero", f"of={path}", "bs=1M", f"count={plan['size_mb']}", "status=none"], check=True)
        
        os.chmod(path, 0o600)
        print("   Executing: mkswap...", flush=True)
        subprocess.run(["mkswap", path], check=True)
        
        print(f"   Executing: swapon (Priority {plan['priority']})...", flush=True)
        subprocess.run(["swapon", "-p", str(plan['priority']), path], check=True)

        # 2. Persistence
        unit_path = plan['unit_path']
        print(f">> STEP: Persisting Systemd Unit ({os.path.basename(unit_path)})", flush=True)
        if not _atomic_write(unit_path, plan['unit_content']): return 1
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", "--now", os.path.basename(unit_path)], check=True)

        # 3. Boot Config (With Offset Auto-Correction)
        print(">> STEP: Updating Kernel Parameters", flush=True)
        offset = _get_resume_offset(path)
        grub_content = plan.get('grub_content', '')
        initramfs_content = plan.get('initramfs_content', '')
        
        if not is_block and offset != "0":
            print(f"   Auto-correcting resume_offset to: {offset}", flush=True)
            # Inject into GRUB
            if "resume_offset=" not in grub_content:
                grub_content = grub_content.replace('"', f' resume_offset={offset}"', 1)
            # Inject into initramfs
            if "RESUME_OFFSET=" not in initramfs_content:
                initramfs_content += f"RESUME_OFFSET={offset}\n"

        if plan.get('grub_path'):
            if not _atomic_write(plan['grub_path'], grub_content): return 1
        if plan.get('initramfs_path'):
            if not _atomic_write(plan['initramfs_path'], initramfs_content): return 1

        # 4. Policy
        print(">> STEP: Applying Hibernation Policy (ZRAM Paradox Fix)", flush=True)
        policy_path = "/etc/tmpfiles.d/99-z-manager-hibernation.conf"
        if not _atomic_write(policy_path, plan['policy_content']): return 1
        subprocess.run(["systemd-tmpfiles", "--create", policy_path], check=True)

        # 5. Regeneration
        print(">> STEP: Regenerating Bootloader & initramfs (This takes a minute...)", flush=True)
        if shutil.which("update-grub"):
            subprocess.run(["update-grub"], check=True)
        elif shutil.which("grub-mkconfig"):
            # Handle Fedora/Arch style
            for p in ["/boot/grub/grub.cfg", "/boot/grub2/grub.cfg", "/boot/efi/EFI/fedora/grub.cfg"]:
                if os.path.exists(p):
                    subprocess.run(["grub-mkconfig", "-o", p], check=True)
                    break
        
        if shutil.which("update-initramfs"):
            subprocess.run(["update-initramfs", "-u"], check=True)
        elif shutil.which("dracut"):
            subprocess.run(["dracut", "-f", "--regenerate-all"], check=True)

        print(">> ALL STEPS COMPLETED SUCCESSFULLY", flush=True)
        return 0
    except Exception as e:
        print(f"!! FATAL ERROR: {e}", file=sys.stderr, flush=True)
        return 1


def cmd_systemctl(action: str, service: str) -> int:
    """Run systemctl action on a service."""
    if action == "daemon-reload":
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        return 0
    if not is_service_allowed(service):
        print(f"Error: Service not allowed: {service}", file=sys.stderr)
        return 1
    cmd = ["systemctl", action]
    if action in ("enable", "disable"): cmd.append("--now")
    cmd.append(service)
    subprocess.run(cmd, check=True)
    return 0


def cmd_live_apply(device_name: str, config_path: str) -> int:
    """Atomic config update + daemon-reload + service restart."""
    content = sys.stdin.read()
    print(f">> STEP: Updating Configuration ({config_path})", flush=True)
    if not _atomic_write(config_path, content): return 1
    
    print(">> STEP: Reloading systemd daemon", flush=True)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    
    svc = f"systemd-zram-setup@{device_name}.service"
    print(f">> STEP: Restarting {svc}", flush=True)
    subprocess.run(["systemctl", "restart", svc], check=True)
    
    print(">> LIVE APPLY COMPLETED", flush=True)
    return 0


def cmd_live_remove(device_name: str, config_path: str) -> int:
    """Service stop + atomic config update + daemon-reload."""
    content = sys.stdin.read()
    svc = f"systemd-zram-setup@{device_name}.service"
    
    print(f">> STEP: Stopping {svc}", flush=True)
    subprocess.run(["systemctl", "stop", svc], check=True)
    
    print(f">> STEP: Updating Configuration ({config_path})", flush=True)
    if not _atomic_write(config_path, content): return 1
    
    print(">> STEP: Reloading systemd daemon", flush=True)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    
    print(">> LIVE REMOVE COMPLETED", flush=True)
    return 0


def cmd_update_boot() -> int:
    """Regenerate GRUB and initramfs."""
    print(">> STEP: Regenerating Bootloader", flush=True)
    if shutil.which("update-grub"):
        subprocess.run(["update-grub"], check=True)
    elif shutil.which("grub-mkconfig"):
        for p in ["/boot/grub/grub.cfg", "/boot/grub2/grub.cfg", "/boot/efi/EFI/fedora/grub.cfg"]:
            if os.path.exists(p):
                subprocess.run(["grub-mkconfig", "-o", p], check=True)
                break
                
    print(">> STEP: Regenerating initramfs", flush=True)
    if shutil.which("update-initramfs"):
        subprocess.run(["update-initramfs", "-u"], check=True)
    elif shutil.which("dracut"):
        subprocess.run(["dracut", "-f", "--regenerate-all"], check=True)
    return 0


def cmd_remove(path: str) -> int:
    """Remove a file if it is in the whitelist."""
    if not is_path_allowed(path):
        print(f"Error: Path not allowed for removal: {path}", file=sys.stderr)
        return 1
    try:
        if os.path.exists(path):
            os.remove(path)
        return 0
    except Exception as e:
        print(f"Error removing {path}: {e}", file=sys.stderr)
        return 1


def main():
    if len(sys.argv) < 2:
        return 1

    match sys.argv[1:]:
        case ["write", path]:
            return cmd_write(path)
        case ["remove", path]:
            return cmd_remove(path)
        case ["hibernate-setup"]:
            return cmd_hibernate_setup()
        case ["live-apply", device, path]:
            return cmd_live_apply(device, path)
        case ["live-remove", device, path]:
            return cmd_live_remove(device, path)
        case ["sysctl-system"]:
            subprocess.run(["sysctl", "--system"], check=True)
            return 0
        case ["hibernate-policy"]:
            # Trigger tmpfiles to apply the policy
            subprocess.run(["systemd-tmpfiles", "--create", "/etc/tmpfiles.d/99-z-manager-hibernation.conf"], check=True)
            return 0
        case ["update-boot"]:
            return cmd_update_boot()
        case ["daemon-reload"]:
            return cmd_systemctl("daemon-reload", "")
        case [action, service]:
            return cmd_systemctl(action, service)
        case _:
            return 1

if __name__ == "__main__":
    sys.exit(main())
