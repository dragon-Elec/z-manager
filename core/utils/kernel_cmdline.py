# z-manager/core/utils/kernel_cmdline.py
"""
Kernel command-line parsing utilities.
"""

from __future__ import annotations

import logging
from .common import read_file

_LOGGER = logging.getLogger(__name__)


def is_kernel_param_active(param: str) -> bool:
    """Check the live kernel command line for a given parameter.

    Uses substring matching within each whitespace-delimited token, so both
    exact tokens (``zswap.enabled=0``) and prefix patterns (``resume=``)
    work correctly.
    """
    try:
        cmdline = read_file("/proc/cmdline")
        if not cmdline:
            return False
        return any(token.startswith(param) for token in cmdline.split())
    except Exception as e:
        _LOGGER.warning(f"Could not read /proc/cmdline: {e}")
        return False
