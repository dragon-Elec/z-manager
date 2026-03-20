# z-manager/core/device_management/types.py
"""
Shared data structures and models for device management.
Acts as the 'contract' between the system layer and the UI/consumers.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

@dataclass(frozen=True)
class DeviceInfo:
    """Represents a complete snapshot of a ZRAM device's current state."""
    name: str
    disksize: Optional[str] = None
    data_size: Optional[str] = None
    compr_size: Optional[str] = None
    total_size: Optional[str] = None  # mem_used_total
    mem_limit: Optional[str] = None
    mem_used_max: Optional[str] = None
    same_pages: Optional[str] = None
    migrated: Optional[str] = None
    mountpoint: Optional[str] = None
    ratio: Optional[str] = None
    streams: Optional[int] = None
    algorithm: Optional[str] = None

@dataclass(frozen=True)
class WritebackStatus:
    """Current live state of a ZRAM device's writeback backing device."""
    device: str
    backing_dev: Optional[str]
    mem_used_total: Optional[str]
    orig_data_size: Optional[str]
    compr_data_size: Optional[str]
    num_writeback: Optional[str]
    writeback_failed: Optional[str]

@dataclass(frozen=True)
class UnitResult:
    """Outcome of a systemd unit operation (restart, stop, etc.)."""
    success: bool
    message: str = ""
    service: Optional[str] = None

@dataclass(frozen=True)
class WritebackResult:
    """Outcome of configuring or clearing writeback for a device."""
    success: bool
    device: str
    action: str
    details: Dict[str, Any]

@dataclass(frozen=True)
class PersistResult:
    """Outcome of persisting a device configuration to disk."""
    success: bool
    device: str
    applied: bool
    message: str = ""

@dataclass(frozen=True)
class Action:
    """A single step within an orchestration pipeline."""
    name: str
    success: bool
    message: str = ""

@dataclass(frozen=True)
class OrchestrationResult:
    """Full summary of an idempotent state-assurance operation."""
    success: bool
    device: str
    desired_writeback: Optional[str]
    actions: List[Action]
    message: str = ""
