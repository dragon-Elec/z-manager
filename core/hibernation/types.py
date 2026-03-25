# z-manager/core/hibernation/types.py
"""
Shared data structures for hibernation management.
Acts as the 'contract' between the system layer and the UI/consumers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class HibernateCheckResult:
    ready: bool
    secure_boot: Literal[
        "disabled", "integrity", "confidentiality", "queried-via-logind"
    ]
    swap_total: int
    ram_total: int
    message: str


@dataclass(frozen=True)
class SwapCreationResult:
    success: bool
    path: str
    uuid: str | None
    offset: int | None
    message: str


@dataclass(frozen=True)
class ResumeConfig:
    uuid: str
    offset: int | None
    device_path: str


@dataclass(frozen=True)
class SwapPersistResult:
    success: bool
    unit_name: str
    message: str


@dataclass(frozen=True)
class SwapTeardownResult:
    success: bool
    message: str


@dataclass(frozen=True)
class HibernateSetupResult:
    success: bool
    path: str
    uuid: str | None
    offset: int | None
    swap_persisted: bool
    boot_configured: bool
    initramfs_regenerated: bool
    reboot_required: bool
    message: str
