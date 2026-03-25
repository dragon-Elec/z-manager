# z-manager/core/hibernation/provisioner.py
"""
The Hazard Zone.
Handles device creation, swap lifecycle, and destructive operations.
Logic in this file can directly impact system swap and kernel stability.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from core.utils.common import run, SystemCommandError
from core.utils.io import pkexec_write
from core.utils.block import check_device_safety, is_block_device
from core.utils.privilege import pkexec_daemon_reload, pkexec_systemctl
from .types import SwapCreationResult, SwapPersistResult, SwapTeardownResult
from .prober import _get_fs_type, get_resume_offset, get_partition_uuid

_LOGGER = logging.getLogger(__name__)


def create_swapfile(path: str, size_mb: int) -> SwapCreationResult:
    """
    Creates a swapfile safely, handling Btrfs COW disabling.
    """
    if os.path.exists(path) and is_block_device(path):
        return SwapCreationResult(
            False,
            path,
            None,
            None,
            "Path is an existing block device. Use it directly.",
        )

    fs_type = _get_fs_type(os.path.dirname(path))

    try:
        if fs_type == "btrfs":
            run(["truncate", "-s", "0", path], check=True)
            run(["chattr", "+C", path], check=True)

        try:
            run(["fallocate", "-l", f"{size_mb}M", path], check=True)
        except SystemCommandError:
            run(
                [
                    "dd",
                    "if=/dev/zero",
                    f"of={path}",
                    "bs=1M",
                    f"count={size_mb}",
                    "status=progress",
                ],
                check=True,
            )

        os.chmod(path, 0o600)
        run(["mkswap", path], check=True)

    except (SystemCommandError, OSError) as e:
        if os.path.exists(path) and os.path.isfile(path) and os.path.getsize(path) == 0:
            os.remove(path)
        return SwapCreationResult(False, path, None, None, str(e))

    uuid = get_partition_uuid(path)
    offset = get_resume_offset(path)
    return SwapCreationResult(
        True, path, uuid, offset, "Swapfile created successfully."
    )


def enable_swapon(path: str, priority: int = 0) -> bool:
    try:
        run(["swapon", "-p", str(priority), path], check=True)
        return True
    except SystemCommandError:
        return False


def swapoff_swap(path: str) -> bool:
    try:
        run(["swapoff", path], check=True)
        return True
    except SystemCommandError:
        return False


def delete_swap(path: str) -> SwapTeardownResult:
    """
    Full teardown of a hibernation swap:
    1. swapoff if active
    2. disable and neutralize systemd unit if present
    3. remove swapfile or leave block device as-is
    """
    from core.utils.io import is_root

    logs: list[str] = []

    if swapoff_swap(path):
        logs.append("Disabled swap")
    else:
        logs.append("swapoff skipped (not active or failed)")

    unit_name = escape_unit_name(path)
    unit_path = f"/etc/systemd/system/{unit_name}"
    if Path(unit_path).exists():
        ok, err = pkexec_systemctl("disable", unit_name)
        if not ok:
            logs.append(f"Failed to disable unit: {err}")
        # Neutralize the unit file via pkexec instead of unprivileged os.remove
        ok, err = pkexec_write(
            unit_path, "# Unit removed by Z-Manager teardown\n"
        )
        if ok:
            logs.append("Neutralized systemd unit")
        else:
            logs.append(f"Could not neutralize systemd unit file: {err}")
        pkexec_daemon_reload()

    if not is_block_device(path):
        if os.path.exists(path):
            if is_root():
                try:
                    os.remove(path)
                    logs.append("Removed swapfile")
                except OSError as e:
                    return SwapTeardownResult(
                        False, f"Failed to remove swapfile: {e}"
                    )
            else:
                # Swapfile in user space or needs privilege
                try:
                    os.remove(path)
                    logs.append("Removed swapfile")
                except PermissionError:
                    logs.append(
                        "Swapfile requires root to remove — left in place"
                    )
                except OSError as e:
                    return SwapTeardownResult(
                        False, f"Failed to remove swapfile: {e}"
                    )
    else:
        logs.append("Block device left as-is")

    return SwapTeardownResult(True, "; ".join(logs))


def escape_unit_name(path: str) -> str:
    """Escapes a filesystem path for use as a systemd unit name."""
    try:
        res = run(["systemd-escape", "-p", "--suffix=swap", path], check=True)
        return res.out.strip()
    except SystemCommandError:
        escaped = path.lstrip("/").replace("/", "-")
        return f"{escaped}.swap"


def generate_swap_unit(path: str, priority: int = 0) -> str:
    """Generates the content for a systemd .swap unit file."""
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


def persist_swap_unit(path: str, priority: int = 0) -> SwapPersistResult:
    """
    Saves the .swap unit to /etc/systemd/system and enables it.
    """
    unit_name = escape_unit_name(path)
    unit_path = f"/etc/systemd/system/{unit_name}"
    content = generate_swap_unit(path, priority)

    ok, err = pkexec_write(unit_path, content)
    if not ok:
        return SwapPersistResult(False, unit_name, f"Failed to write unit file: {err}")

    ok, err = pkexec_daemon_reload()
    if not ok:
        return SwapPersistResult(
            False, unit_name, f"Systemd daemon-reload failed: {err}"
        )

    ok, err = pkexec_systemctl("enable", unit_name)
    if not ok:
        return SwapPersistResult(False, unit_name, f"Failed to enable swap unit: {err}")

    return SwapPersistResult(True, unit_name, "Swap unit persisted and activated.")
