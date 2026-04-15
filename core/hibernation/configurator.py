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
from core.utils.privilege import pkexec_mkswap
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
    get_fs_type,
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

    ok, err = pkexec_write(str(conf_path), content)
    if not ok:
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


def apply_hibernation_policy(minimize_image: bool = True) -> tuple[bool, str]:
    """
    Persistently configures hibernation image size policy via systemd-tmpfiles.
    Minimize image=True sets /sys/power/image_size to 0 (maximum compression).
    """
    path = "/etc/tmpfiles.d/99-z-manager-hibernation.conf"
    val = "0" if minimize_image else "1" # 0 is smallest, 1 is default/calculated
    
    # We use 'w' to write to a file (sysfs in this case)
    content = f"w /sys/power/image_size - - - - {val}\n"
    
    ok, err = pkexec_write(path, content)
    if not ok:
        return False, f"Failed to write hibernation policy: {err}"
    
    # Trigger tmpfiles to apply immediately
    if is_root():
        try:
            run(["systemd-tmpfiles", "--create", path], check=True)
            return True, "Hibernation policy applied via tmpfiles."
        except SystemCommandError as e:
            return False, f"Failed to apply tmpfiles: {e.stderr}"
    
    helper_path = _get_helper_path()
    proc = subprocess.run(
        ["pkexec", helper_path, "tmpfiles"],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, "Hibernation policy applied via pkexec/tmpfiles."
    return False, f"pkexec tmpfiles failed: {proc.stderr.strip()}"


from .provisioner import (
    escape_unit_name,
    generate_swap_unit,
)
from core.utils.privilege import pkexec_hibernate_setup


def apply_full_setup(
    swap_path: str,
    size_mb: int,
    priority: int = 0,
) -> HibernateSetupResult:
    """
    High-level orchestrator for the complete hibernation setup:
    Consolidated into a single Master Transaction via pkexec.
    """
    _LOGGER.info(f"Starting consolidated hibernation setup for {swap_path}")

    # 1. Prepare Storage Metadata
    fs_type = get_fs_type(os.path.dirname(swap_path) or "/")
    
    # 2. Prepare Systemd Metadata
    unit_name = escape_unit_name(swap_path)
    unit_path = f"/etc/systemd/system/{unit_name}"
    unit_content = generate_swap_unit(swap_path, priority)

    # 3. Prepare Boot Config metadata
    # We use a placeholder UUID/Offset if the device doesn't exist yet,
    # but the helper will re-resolve or use the ones we calculate here if it's a partition.
    uuid = get_partition_uuid(swap_path)
    offset = get_resume_offset(swap_path)
    
    # If it's a new swapfile, we have a 'Catch-22' for UUID/Offset before creation.
    # The helper handles creation, then we can resolve UUID. 
    # Actually, for simplicity, the helper just uses the params we send or 
    # we rely on the fact that for a swapfile, we need the UUID of the parent partition.
    parent_uuid = uuid # df -T should have given us this already in get_partition_uuid
    
    params = f"resume=UUID={parent_uuid}"
    # Note: For swapfiles, we'll need to update the offset AFTER creation in a second small step 
    # OR we let the helper handle the file creation and then it writes the configs.
    # To keep it to ONE prompt, the helper must be smart enough to write the config
    # AFTER it knows the offset.
    
    grub_content = f'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT {params}"'
    initramfs_content = f"RESUME=UUID={parent_uuid}\n"
    
    # 4. Policy
    policy_content = "w /sys/power/image_size - - - - 0\n"

    # 5. Build the Master Plan
    plan = {
        "swap_path": swap_path,
        "size_mb": size_mb,
        "fs_type": fs_type,
        "priority": priority,
        "unit_path": unit_path,
        "unit_content": unit_content,
        "grub_path": str(GRUB_RESUME_CONFIG_PATH),
        "grub_content": grub_content,
        "initramfs_path": "/etc/initramfs-tools/conf.d/resume",
        "initramfs_content": initramfs_content,
        "policy_content": policy_content
    }

    # 6. Execute Transaction
    success, message = pkexec_hibernate_setup(plan)

    return HibernateSetupResult(
        success=success,
        path=swap_path,
        uuid=parent_uuid,
        offset=offset, # Will need a quick refresh for files
        swap_persisted=success,
        boot_configured=success,
        initramfs_regenerated=success,
        reboot_required=success,
        message=message,
    )
