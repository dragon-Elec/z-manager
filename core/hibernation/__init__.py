# z-manager/core/hibernation/__init__.py
"""
Hibernation management module.

Architecture follows the prober/provisioner/configurator triad:

  prober.py       — Safe Zone: read-only system probing
  provisioner.py  — Hazard Zone: destructive swap lifecycle
  configurator.py — Orchestrator: full setup coordination
"""

from .types import (
    HibernateCheckResult,
    SwapCreationResult,
    ResumeConfig,
    SwapPersistResult,
    SwapTeardownResult,
    HibernateSetupResult,
)
from .prober import (
    get_memory_info,
    check_hibernation_readiness,
    get_resume_offset,
    get_partition_uuid,
    detect_resume_swap,
)
from .provisioner import (
    create_swapfile,
    enable_swapon,
    swapoff_swap,
    delete_swap,
    persist_swap_unit,
    escape_unit_name,
    generate_swap_unit,
)
from core.utils.bootloader import detect_bootloader, detect_initramfs_system
from core.utils.kernel_cmdline import is_kernel_param_active
from .configurator import (
    update_grub_resume,
    configure_initramfs_resume,
    apply_full_setup,
)

__all__ = [
    # types
    "HibernateCheckResult",
    "SwapCreationResult",
    "ResumeConfig",
    "SwapPersistResult",
    "SwapTeardownResult",
    "HibernateSetupResult",
    # prober
    "get_memory_info",
    "check_hibernation_readiness",
    "get_resume_offset",
    "get_partition_uuid",
    "detect_resume_swap",
    # provisioner
    "create_swapfile",
    "enable_swapon",
    "swapoff_swap",
    "delete_swap",
    "persist_swap_unit",
    "escape_unit_name",
    "generate_swap_unit",
    # configurator
    "update_grub_resume",
    "configure_initramfs_resume",
    "apply_full_setup",
]
