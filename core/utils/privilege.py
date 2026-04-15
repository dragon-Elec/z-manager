# zman/core/utils/privilege.py
"""
Privileged orchestration via pkexec.
"""
from __future__ import annotations
import subprocess
from pathlib import Path
from .common import run, SystemCommandError
from .io import is_root, _get_helper_path

def systemd_daemon_reload() -> None:
    """Run systemctl daemon-reload. Non-privileged wrapper."""
    run(["systemctl", "daemon-reload"], check=True)

def systemd_restart(service: str) -> None:
    """Run systemctl restart. Non-privileged wrapper."""
    run(["systemctl", "restart", service], check=True)

def pkexec_daemon_reload() -> tuple[bool, str | None]:
    """systemctl daemon-reload via pkexec."""
    if is_root():
        try:
            run(["systemctl", "daemon-reload"], check=True)
            return True, None
        except SystemCommandError as e:
            return False, str(e)
    
    helper_path = _get_helper_path()
    try:
        proc = subprocess.run(["pkexec", helper_path, "daemon-reload"], capture_output=True, text=True)
        if proc.returncode == 0:
            return True, None
        return False, proc.stderr.strip() or f"pkexec daemon-reload failed (code {proc.returncode})"
    except Exception as e:
        return False, f"Z-Manager Orchestration Error: {e}"

def pkexec_systemctl(action: str, service: str) -> tuple[bool, str | None]:
    """systemctl action via pkexec."""
    if is_root():
        try:
            cmd = ["systemctl", action]
            if action in ("enable", "disable"): cmd.append("--now")
            cmd.append(service)
            run(cmd, check=True)
            return True, None
        except SystemCommandError as e:
            return False, str(e)
    
    helper_path = _get_helper_path()
    try:
        proc = subprocess.run(["pkexec", helper_path, action, service], capture_output=True, text=True)
        if proc.returncode == 0:
            return True, None
        return False, proc.stderr.strip() or f"pkexec {action} {service} failed (code {proc.returncode})"
    except Exception as e:
        return False, f"Z-Manager Orchestration Error: {e}"

def systemd_try_restart(service: str) -> tuple[bool, str | None]:
    """Attempts to restart a service using standard run() first, then pkexec."""
    res = run(["systemctl", "restart", service])
    if res.code == 0:
        return True, None
    
    # If standard restart fails, try with pkexec escalation
    return pkexec_systemctl("restart", service)

def pkexec_sysctl_system() -> tuple[bool, str | None]:
    """sysctl --system via pkexec."""
    if is_root():
        try:
            run(["sysctl", "--system"], check=True)
            return True, None
        except SystemCommandError as e:
            return False, str(e)
        
    helper_path = _get_helper_path()
    try:
        proc = subprocess.run(["pkexec", helper_path, "sysctl-system"], capture_output=True, text=True)
        if proc.returncode == 0:
            return True, None
        return False, proc.stderr.strip() or f"pkexec sysctl-system failed (code {proc.returncode})"
    except Exception as e:
        return False, f"Z-Manager Orchestration Error: {e}"


import json

def pkexec_hibernate_setup(plan: dict) -> tuple[bool, str]:
    """
    Consolidated hibernation setup via pkexec.
    Sends a JSON plan to the helper for single-prompt execution.
    """
    if is_root():
        # Ideally, we'd just call the logic directly, but for consistency 
        # and logging, we'll pipe it to a temporary instance of the helper
        # logic or just simulate the pipe.
        pass

    helper_path = _get_helper_path()
    try:
        proc = subprocess.run(
            ["pkexec", helper_path, "hibernate-setup"],
            input=json.dumps(plan),
            capture_output=True,
            text=True
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        return False, proc.stderr.strip() or proc.stdout.strip() or f"Transaction failed (code {proc.returncode})"
    except Exception as e:
        return False, f"Z-Manager Orchestration Error: {e}"


def pkexec_create_swapfile(
    path: str, size_mb: int, fs_type: str | None = None
) -> tuple[bool, str | None]:
    """Privileged creation of a swapfile via pkexec helper."""
    helper_path = _get_helper_path()
    try:
        proc = subprocess.run(
            ["pkexec", helper_path, "create-swapfile", path, str(size_mb), fs_type or "none"],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return True, None
        return False, proc.stderr.strip() or f"pkexec create-swapfile failed (code {proc.returncode})"
    except Exception as e:
        return False, f"Z-Manager Orchestration Error: {e}"


def pkexec_mkswap(device: str) -> tuple[bool, str | None]:
    """Privileged mkswap via pkexec helper."""
    helper_path = _get_helper_path()
    try:
        proc = subprocess.run(
            ["pkexec", helper_path, "mkswap", device], capture_output=True, text=True
        )
        if proc.returncode == 0:
            return True, None
        return False, proc.stderr.strip() or f"pkexec mkswap failed (code {proc.returncode})"
    except Exception as e:
        return False, f"Z-Manager Orchestration Error: {e}"


def pkexec_swapon(device: str, priority: int = 0) -> tuple[bool, str | None]:
    """Privileged swapon via pkexec helper."""
    helper_path = _get_helper_path()
    try:
        proc = subprocess.run(
            ["pkexec", helper_path, "swapon", device, str(priority)],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return True, None
        return False, proc.stderr.strip() or f"pkexec swapon failed (code {proc.returncode})"
    except Exception as e:
        return False, f"Z-Manager Orchestration Error: {e}"
