# z-manager/core/utils/bootloader.py
"""
Bootloader and initramfs detection utilities.
"""

from __future__ import annotations

import os
import shutil


def detect_bootloader() -> str:
    """Returns 'grub', 'systemd-boot', or 'unknown'."""
    if (
        shutil.which("update-grub")
        or shutil.which("grub-mkconfig")
        or os.path.exists("/etc/default/grub")
        or os.path.isdir("/boot/grub")
    ):
        return "grub"
    if (
        os.path.isdir("/boot/efi/loader")
        or shutil.which("bootctl")
        or os.path.isdir("/boot/efi/EFI/systemd")
    ):
        return "systemd-boot"
    return "unknown"


def detect_initramfs_system() -> str:
    """Returns 'initramfs-tools', 'dracut', 'mkinitcpio', or 'unknown'."""
    if os.path.isdir("/etc/initramfs-tools") or shutil.which("update-initramfs"):
        return "initramfs-tools"
    if shutil.which("dracut"):
        return "dracut"
    if os.path.exists("/etc/mkinitcpio.conf") or shutil.which("mkinitcpio"):
        return "mkinitcpio"
    return "unknown"
