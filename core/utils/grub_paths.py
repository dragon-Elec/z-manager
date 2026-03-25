# z-manager/core/utils/grub_paths.py
"""
GRUB configuration path constants used across the codebase.
Centralized to avoid duplication across boot_config.py, configurator.py, and zman_helper.py.
"""

from __future__ import annotations

from pathlib import Path

GRUB_ZSWAP_DISABLE_PATH = Path("/etc/default/grub.d/99-z-manager-disable-zswap.cfg")
GRUB_ZSWAP_DISABLE_CONTENT = (
    'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT zswap.enabled=0"'
)

GRUB_PSI_ENABLE_PATH = Path("/etc/default/grub.d/98-z-manager-enable-psi.cfg")
GRUB_PSI_ENABLE_CONTENT = (
    'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT psi=1"'
)

GRUB_RESUME_CONFIG_PATH = Path("/etc/default/grub.d/99-z-manager-resume.cfg")
GRUB_RESUME_CONTENT_TEMPLATE = (
    'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT {params}"'
)

SYSCTL_CONFIG_PATH = Path("/etc/sysctl.d/99-z-manager.conf")
SYSCTL_DEFAULT_SETTINGS = """\
# Default kernel tuning values.
vm.swappiness = 60
vm.watermark_boost_factor = 150
vm.watermark_scale_factor = 10
vm.page-cluster = 3
""".strip()

SYSCTL_GAMING_PROFILE = """\
# Kernel tuning for ZRAM, recommended by Pop!_OS and others.
vm.swappiness = 180
vm.watermark_boost_factor = 0
vm.watermark_scale_factor = 125
vm.page-cluster = 0
""".strip()

ZMAN_HELPER_ALLOWED_PATHS = [
    "/etc/systemd/zram-generator.conf",
    "/etc/sysctl.d/99-z-manager.conf",
    "/etc/default/grub.d/99-z-manager-disable-zswap.cfg",
    "/etc/default/grub.d/98-z-manager-enable-psi.cfg",
    "/etc/default/grub.d/99-z-manager-resume.cfg",
    "/etc/initramfs-tools/conf.d/resume",
]
