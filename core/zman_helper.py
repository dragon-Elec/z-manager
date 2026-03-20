#!/usr/bin/env python3
"""
zman-helper.py - Privileged helper for Z-Manager

This script is designed to be called via pkexec to perform
operations that require root privileges.

Usage:
    pkexec /path/to/zman-helper.py write <path>
        Reads content from stdin and writes to <path>
    
    pkexec /path/to/zman-helper.py daemon-reload
        Runs systemctl daemon-reload
    
    pkexec /path/to/zman-helper.py restart <service>
        Runs systemctl restart <service>
    
    pkexec /path/to/zman-helper.py stop <service>
        Runs systemctl stop <service>

    pkexec /path/to/zman-helper.py live-apply <device> <config_path>
        Batched: Stop -> Write (stdin) -> Reload -> Restart

    pkexec /path/to/zman-helper.py live-remove <device> <config_path>
        Batched: Stop -> Write (stdin) -> Reload
"""

import sys
import os
import subprocess
import shutil
import tempfile

# Allowed paths for write operations (security whitelist)
ALLOWED_WRITE_PATHS = [
    "/etc/systemd/zram-generator.conf",
    "/etc/sysctl.d/99-z-manager.conf",
    "/etc/default/grub.d/99-z-manager-disable-zswap.cfg",
    "/etc/default/grub.d/98-z-manager-enable-psi.cfg",
]

# Allowed service patterns for systemctl operations
ALLOWED_SERVICE_PATTERNS = [
    "systemd-zram-setup@zram",  # Matches zram0, zram1, etc.
]


def is_path_allowed(path: str) -> bool:
    """Check if the path is in the whitelist."""
    return path in ALLOWED_WRITE_PATHS


def is_service_allowed(service: str) -> bool:
    """Check if the service matches allowed patterns."""
    for pattern in ALLOWED_SERVICE_PATTERNS:
        if service.startswith(pattern):
            return True
    return False


def cmd_write(path: str) -> int:
    """Write content from stdin to path atomically with backup."""
    if not is_path_allowed(path):
        print(f"Error: Path not allowed: {path}", file=sys.stderr)
        return 1
    
    try:
        # Read content from stdin
        content = sys.stdin.read()
        
        # 1. Backup: Create a .bak copy if file exists
        if os.path.exists(path):
            try:
                shutil.copy2(path, f"{path}.bak")
            except Exception as e:
                print(f"Warning: Backup failed: {e}", file=sys.stderr)
                # We proceed even if backup fails to ensure we can still fix configs,
                # but we notify the caller.

        # 2. Atomic write: write to temp file, then move
        dir_name = os.path.dirname(path)
        os.makedirs(dir_name, exist_ok=True)
        
        fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
            shutil.move(temp_path, path)
            os.chmod(path, 0o644)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
        
        return 0
    except Exception as e:
        print(f"Error writing to {path}: {e}", file=sys.stderr)
        return 1


def cmd_daemon_reload() -> int:
    """Run systemctl daemon-reload."""
    try:
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error: daemon-reload failed: {e}", file=sys.stderr)
        return e.returncode


def cmd_systemctl(action: str, service: str) -> int:
    """Run systemctl action on a service."""
    if action not in ("restart", "stop", "start"):
        print(f"Error: Invalid action: {action}", file=sys.stderr)
        return 1
    
    if not is_service_allowed(service):
        print(f"Error: Service not allowed: {service}", file=sys.stderr)
        return 1
    
    try:
        subprocess.run(["systemctl", action, service], check=True)
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error: systemctl {action} {service} failed: {e}", file=sys.stderr)
        return e.returncode



def cmd_live_apply(device_name: str, config_path: str) -> int:
    """
    Batched operation: Stop -> Write -> Daemon Reload -> Restart.
    Prints progress markers ">> Step Name" for the UI to parse.
    """
    service = f"systemd-zram-setup@{device_name}.service"
    
    if not is_path_allowed(config_path):
        print(f"Error: Path not allowed: {config_path}", file=sys.stderr)
        return 1
    
    # 1. STOP
    print(f">> Stopping {service}...", flush=True)
    # We ignore errors on stop (service might not be running)
    subprocess.run(["systemctl", "stop", service], stderr=subprocess.STDOUT)
    
    # 2. WRITE
    print(f">> Writing configuration...", flush=True)
    if cmd_write(config_path) != 0:
        return 1
        
    # 3. RELOAD
    print(f">> Reloading systemd...", flush=True)
    if cmd_daemon_reload() != 0:
        return 1
        
    # 4. RESTART
    print(f">> Restarting {service}...", flush=True)
    if cmd_systemctl("restart", service) != 0:
        return 1
        
    print(">> Done", flush=True)
    return 0


def cmd_live_remove(device_name: str, config_path: str) -> int:
    """
    Batched operation: Stop -> Write -> Daemon Reload.
    """
    service = f"systemd-zram-setup@{device_name}.service"
    
    if not is_path_allowed(config_path):
        print(f"Error: Path not allowed: {config_path}", file=sys.stderr)
        return 1

    # 1. STOP
    print(f">> Stopping {service}...", flush=True)
    subprocess.run(["systemctl", "stop", service], stderr=subprocess.STDOUT)

    # 2. WRITE
    print(f">> Writing configuration...", flush=True)
    if cmd_write(config_path) != 0:
        return 1

    # 3. RELOAD
    print(f">> Reloading systemd...", flush=True)
    if cmd_daemon_reload() != 0:
        return 1
    
    print(">> Done", flush=True)
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    match sys.argv[1:]:
        case ["write", path]:
            return cmd_write(path)

        case ["daemon-reload"]:
            return cmd_daemon_reload()

        case [("restart" | "stop" | "start") as action, service]:
            return cmd_systemctl(action, service)

        case ["live-apply", device, config_path]:
            return cmd_live_apply(device, config_path)

        case ["live-remove", device, config_path]:
            return cmd_live_remove(device, config_path)

        case _:
            print(f"Unknown command or arguments: {' '.join(sys.argv[1:])}", file=sys.stderr)
            return 1



if __name__ == "__main__":
    sys.exit(main())
