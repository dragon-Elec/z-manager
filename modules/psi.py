# zman/modules/psi.py
"""
Provides functions for monitoring Pressure Stall Information (PSI).

This is a read-only module for parsing live data from the /proc/pressure/
filesystem, providing both snapshots and real-time monitoring capabilities.
Inspired by Kimi's superior monitoring implementation.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

_LOGGER = logging.getLogger(__name__)
PROC_PSI_PATH = Path("/proc/pressure")


@dataclass(frozen=True)
class PsiStats:
    """Represents the pressure stall information for a single resource."""
    resource: str      # "cpu", "memory", "io"
    some_avg10: float
    some_avg60: float
    some_avg300: float
    some_total: int     # microseconds
    full_avg10: float
    full_avg60: float
    full_avg300: float
    full_total: int     # microseconds


def _parse_psi_line(line: str) -> tuple[float, float, float, int]:
    """Helper to parse a 'some' or 'full' line from a PSI file."""
    parts = line.split()
    avg10 = float(parts[0].split("=")[1])
    avg60 = float(parts[1].split("=")[1])
    avg300 = float(parts[2].split("=")[1])
    total = int(parts[3].split("=")[1])
    return avg10, avg60, avg300, total


def get_psi(resource: str) -> Optional[PsiStats]:
    """
    Return current PSI numbers for a resource ('cpu', 'memory', 'io').
    Returns None if PSI is not available for that resource.
    """
    path = PROC_PSI_PATH / resource
    if not path.exists():
        _LOGGER.debug(f"PSI resource not found at {path}")
        return None

    try:
        lines = path.read_text().strip().split('\n')
        some_line = lines[0]
        full_line = lines[1]

        s_avg10, s_avg60, s_avg300, s_total = _parse_psi_line(some_line)
        f_avg10, f_avg60, f_avg300, f_total = _parse_psi_line(full_line)

        return PsiStats(
            resource=resource,
            some_avg10=s_avg10, some_avg60=s_avg60, some_avg300=s_avg300, some_total=s_total,
            full_avg10=f_avg10, full_avg60=f_avg60, full_avg300=f_avg300, full_total=f_total,
        )
    except (IOError, IndexError, ValueError, AttributeError) as e:
        _LOGGER.error(f"Failed to parse PSI data from {path}: {e}")
        return None


def watch_psi(resource: str, interval: float = 1.0) -> Iterator[PsiStats]:
    """
    Generator that yields fresh PsiStats every <interval> seconds.
    Stops if the PSI file becomes inaccessible.
    """
    _LOGGER.info(f"Starting PSI watch for '{resource}' with {interval}s interval.")
    while True:
        stats = get_psi(resource)
        if stats:
            yield stats
            time.sleep(interval)
        else:
            _LOGGER.warning(f"Stopping PSI watch for '{resource}' as it is no longer available.")
            break
