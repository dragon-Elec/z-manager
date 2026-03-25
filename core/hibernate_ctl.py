# zman/core/hibernate_ctl.py
"""
Deprecated compatibility shim.

All hibernation logic has moved to core.hibernation.

This module re-exports the public API for backwards compatibility
with any external code that imports from here. It will be removed
in a future release.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "core.hibernate_ctl is deprecated; import from core.hibernation instead",
    DeprecationWarning,
    stacklevel=2,
)

from core.hibernation.prober import (
    get_memory_info as get_memory_info,
    check_hibernation_readiness as check_hibernation_readiness,
    get_resume_offset as get_resume_offset,
    get_partition_uuid as get_partition_uuid,
)
from core.hibernation.provisioner import (
    create_swapfile as create_swapfile,
    enable_swapon as enable_swapon,
    swapoff_swap as swapoff_swap,
    delete_swap as delete_swap,
    persist_swap_unit as persist_swap_unit,
    escape_unit_name as escape_unit_name,
    generate_swap_unit as generate_swap_unit,
)
from core.hibernation import types as types

HibernateCheckResult = types.HibernateCheckResult
SwapCreationResult = types.SwapCreationResult


def update_fstab(device_path: str, uuid: str) -> bool:
    """
    [DEPRECATED] Adds a swap entry to /etc/fstab.
    This function is no longer provided by the new module.
    systemd swap units are the modern replacement.
    """
    raise NotImplementedError(
        "update_fstab has been removed. "
        "Use persist_swap_unit() from core.hibernation instead."
    )
