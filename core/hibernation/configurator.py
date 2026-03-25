# z-manager/core/hibernation/configurator.py
"""
The Orchestrator.
Manages the full hibernation setup lifecycle: GRUB config, initramfs, and
systemd coordination. Bridges the gap between the persistent plan and the
live kernel state.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from core.utils.common import run, SystemCommandError, read_file
from core.utils.io import pkexec_write, is_root, _get_helper_path
from core.utils.block import is_block_device, check_device_safety
from core.utils.bootloader import detect_bootloader, detect_initramfs_system
from core.utils.kernel_cmdline import is_kernel_param_active
from core.utils.grub_paths import GRUB_RESUME_CONFIG_PATH
from .types import (
    SwapCreationResult,
    SwapPersistResult,
    SwapTeardownResult,
    HibernateSetupResult,
    ResumeConfig,
)
from .prober import (
    get_partition_uuid,
    get_resume_offset,
    check_hibernation_readiness,
)
from .provisioner import (
    create_swapfile,
    enable_swapon,
    swapoff_swap,
    persist_swap_unit,
    delete_swap,
)

_LOGGER = logging.getLogger(__name__)


def update_grub_resume(uuid: str, offset: int | None = None) -> tuple[bool, str]:
    """
    Adds resume=UUID=... [resume_offset=...] to GRUB config drop-in.
    """
    if detect_bootloader() != "grub":
        return False, "Automatic resume configuration requires GRUB bootloader."

    params = f"resume=UUID={uuid}"
    if offset is not None and offset > 0:
        params += f" resume_offset={offset}"
    content = f'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT {params}"'
    success, err = pkexec_write(str(GRUB_RESUME_CONFIG_PATH), content + "\n")
    if not success:
        return False, f"Failed to write GRUB resume config: {err}"
    return (
        True,
        "Resume configuration written to GRUB drop-in. Run update-grub to apply.",
    )


def configure_initramfs_resume(
    uuid: str, offset: int | None = None
) -> tuple[bool, str]:
    """
    Configures initramfs resume parameters (initramfs-tools only).
    """
    system = detect_initramfs_system()
    if system != "initramfs-tools":
        return (
            True,
            f"Initramfs system '{system}' auto-configuration not implemented. GRUB is set.",
        )

    conf_path = Path("/etc/initramfs-tools/conf.d/resume")
    content = f"RESUME=UUID={uuid}\n"
    if offset is not None and offset > 0:
        content += f"RESUME_OFFSET={offset}\n"

    success, err = pkexec_write(str(conf_path), content)
    if not success:
        return False, f"Failed to write initramfs resume config: {err}"
    return True, "Initramfs resume config updated."


def pkexec_update_grub() -> tuple[bool, str]:
    """Runs update-grub via pkexec."""
    if is_root():
        try:
            if shutil.which("update-grub"):
                run(["update-grub"], check=True)
            elif shutil.which("grub-mkconfig"):
                for p in [
                    "/boot/grub/grub.cfg",
                    "/boot/efi/EFI/fedora/grub.cfg",
                    "/boot/grub2/grub.cfg",
                ]:
                    if os.path.exists(p):
                        run(["grub-mkconfig", "-o", p], check=True)
                        break
                else:
                    return False, "Could not find grub.cfg to update."
            else:
                return False, "Neither update-grub nor grub-mkconfig found."
            return True, "GRUB configuration updated successfully."
        except SystemCommandError as e:
            return False, f"Failed to update GRUB: {e.stderr}"
    helper_path = _get_helper_path()
    proc = subprocess.run(
        ["pkexec", helper_path, "update-grub"],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, "GRUB configuration updated successfully via pkexec."
    return False, f"pkexec update-grub failed: {proc.stderr.strip()}"


def pkexec_update_initramfs() -> tuple[bool, str]:
    """Regenerates initramfs via pkexec."""
    if is_root():
        return _regenerate_initramfs()
    helper_path = _get_helper_path()
    proc = subprocess.run(
        ["pkexec", helper_path, "update-initramfs"],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, "Initramfs regenerated successfully via pkexec."
    return False, f"pkexec update-initramfs failed: {proc.stderr.strip()}"


def _regenerate_initramfs() -> tuple[bool, str]:
    """Regenerates initramfs as root."""
    match detect_initramfs_system():
        case "initramfs-tools":
            cmd = ["update-initramfs", "-u"]
        case "dracut":
            cmd = ["dracut", "-f", "--regenerate-all"]
        case "mkinitcpio":
            cmd = ["mkinitcpio", "-P"]
        case s:
            return False, f"Unknown or unsupported initramfs system: {s}"
    try:
        run(cmd, check=True)
        return (
            True,
            f"Initramfs regenerated successfully ({detect_initramfs_system()}).",
        )
    except SystemCommandError as e:
        return False, f"Failed to regenerate initramfs: {e.stderr}"


def apply_full_setup(
    swap_path: str,
    size_mb: int,
    priority: int = 0,
) -> HibernateSetupResult:
    """
    High-level orchestrator for the complete hibernation setup:
    1. Create / enable swap
    2. Resolve UUID + offset (AFTER creation so the file exists)
    3. Persist systemd swap unit
    4. Write GRUB resume parameters
    5. Write initramfs resume parameters
    6. Run update-grub
    7. Run update-initramfs
    """
    _LOGGER.info(f"Starting full hibernation setup for {swap_path}")

    swap_persisted = False
    boot_configured = False
    initramfs_regenerated = False
    reboot_required = False
    logs: list[str] = []

    # --- Step 1: Create or format the swap target ---
    res_create: SwapCreationResult | None = None
    if not is_block_device(swap_path):
        res_create = create_swapfile(swap_path, size_mb)
        if not res_create.success:
            return HibernateSetupResult(
                success=False,
                path=swap_path,
                uuid=None,
                offset=None,
                swap_persisted=False,
                boot_configured=False,
                initramfs_regenerated=False,
                reboot_required=False,
                message=f"SWAPFILE creation failed: {res_create.message}",
            )
        logs.append("Swapfile created.")
        if not enable_swapon(swap_path, priority):
            logs.append("Warning: Could not enable swapon (maybe already active).")
    else:
        safe, msg = check_device_safety(swap_path)
        if not safe:
            return HibernateSetupResult(
                success=False,
                path=swap_path,
                uuid=None,
                offset=None,
                swap_persisted=False,
                boot_configured=False,
                initramfs_regenerated=False,
                reboot_required=False,
                message=f"Device safety check failed: {msg}",
            )
        try:
            run(["mkswap", swap_path], check=True)
            logs.append(f"Formatted partition {swap_path}")
        except SystemCommandError as e:
            return HibernateSetupResult(
                success=False,
                path=swap_path,
                uuid=None,
                offset=None,
                swap_persisted=False,
                boot_configured=False,
                initramfs_regenerated=False,
                reboot_required=False,
                message=f"mkswap failed: {e.stderr}",
            )
        if not enable_swapon(swap_path, priority):
            logs.append("Warning: Could not enable swapon.")
        res_create = SwapCreationResult(
            True, swap_path, None, None, "Partition prepared."
        )

    # --- Step 2: Resolve UUID + offset AFTER the swap target exists ---
    uuid = get_partition_uuid(swap_path)
    offset = get_resume_offset(swap_path)

    if not uuid:
        return HibernateSetupResult(
            success=False,
            path=swap_path,
            uuid=None,
            offset=offset,
            swap_persisted=False,
            boot_configured=False,
            initramfs_regenerated=False,
            reboot_required=False,
            message="Could not determine UUID for device after creation.",
        )

    # --- Step 3: Persist systemd swap unit ---
    res_persist = persist_swap_unit(swap_path, priority)
    swap_persisted = res_persist.success
    logs.append(f"Persist swap unit: {res_persist.message}")

    # --- Step 4: Write GRUB resume parameters ---
    ok, msg = update_grub_resume(uuid, offset)
    boot_configured = ok
    logs.append(f"GRUB: {msg}")
    if not ok:
        return HibernateSetupResult(
            success=False,
            path=swap_path,
            uuid=uuid,
            offset=offset,
            swap_persisted=swap_persisted,
            boot_configured=boot_configured,
            initramfs_regenerated=False,
            reboot_required=False,
            message="; ".join(logs),
        )

    # --- Step 5: Write initramfs resume parameters ---
    ok, msg = configure_initramfs_resume(uuid, offset)
    logs.append(f"initramfs config: {msg}")

    # --- Step 6-7: Regenerate ---
    logs.append("Regenerating initramfs (this may take a minute)...")
    ok_grub, _ = pkexec_update_grub()
    logs.append(f"update-grub: {'OK' if ok_grub else 'FAILED'}")

    ok_init, msg_init = pkexec_update_initramfs()
    initramfs_regenerated = ok_init
    logs.append(f"update-initramfs: {msg_init}")

    reboot_required = ok_grub and ok_init
    return HibernateSetupResult(
        success=reboot_required,
        path=swap_path,
        uuid=uuid,
        offset=offset,
        swap_persisted=swap_persisted,
        boot_configured=boot_configured,
        initramfs_regenerated=initramfs_regenerated,
        reboot_required=reboot_required,
        message="; ".join(logs),
    )
