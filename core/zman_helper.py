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
    """Write content from stdin to path atomically."""
    if not is_path_allowed(path):
        print(f"Error: Path not allowed: {path}", file=sys.stderr)
        return 1
    
    try:
        # Read content from stdin
        content = sys.stdin.read()
        
        # Atomic write: write to temp file, then move
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


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    
    cmd = sys.argv[1]
    
    if cmd == "write":
        if len(sys.argv) < 3:
            print("Usage: zman-helper.py write <path>", file=sys.stderr)
            return 1
        return cmd_write(sys.argv[2])
    
    elif cmd == "daemon-reload":
        return cmd_daemon_reload()
    
    elif cmd in ("restart", "stop", "start"):
        if len(sys.argv) < 3:
            print(f"Usage: zman-helper.py {cmd} <service>", file=sys.stderr)
            return 1
        return cmd_systemctl(cmd, sys.argv[2])
    
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
