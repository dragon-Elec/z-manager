# zman/core/persist.py
"""
Manages persistent, boot-time system configuration.

This module is responsible for creating and managing configuration files
in system directories like /etc/sysctl.d/ and /etc/default/grub.d/
to ensure that tuning settings survive a reboot.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.os_utils import run, SystemCommandError
from ..utils import atomic_write_to_file, read_file_content

_LOGGER = logging.getLogger(__name__)

# --- Core Constants ---
SYSCTL_CONFIG_PATH = Path("/etc/sysctl.d/99-z-manager.conf")
GAMING_PROFILE_CONTENT = """# Kernel tuning for ZRAM, recommended by Pop!_OS and others.
vm.swappiness = 180
vm.watermark_boost_factor = 0
vm.watermark_scale_factor = 125
vm.page-cluster = 0
""".strip()

GRUB_ZSWAP_DISABLE_PATH = Path("/etc/default/grub.d/99-z-manager-disable-zswap.cfg")
GRUB_ZSWAP_DISABLE_CONTENT = 'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT zswap.enabled=0"'

GRUB_PSI_ENABLE_PATH = Path("/etc/default/grub.d/98-z-manager-enable-psi.cfg")
GRUB_PSI_ENABLE_CONTENT = 'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT psi=1"'


# --- Data Structure for Results ---
@dataclass(frozen=True)
class TuneResult:
    """Represents the outcome of a persistent tuning operation."""
    success: bool
    changed: bool
    message: str
    action_needed: Optional[str] = None  # e.g., "reboot", "update-grub"


# --- Helper Functions ---

def is_kernel_param_active(param: str) -> bool:
    """Checks the live kernel command line for a given parameter."""
    try:
        cmdline = Path("/proc/cmdline").read_text()
        return param in cmdline.split()
    except Exception as e:
        _LOGGER.warning(f"Could not read /proc/cmdline: {e}")
        return False


# --- Core Tuning Functions ---

def apply_sysctl_profile(enable: bool) -> TuneResult:
    """
    Idempotently enables or disables the optimal sysctl performance profile.
    """
    if enable:
        current_content = read_file_content(SYSCTL_CONFIG_PATH)
        if current_content and current_content.strip() == GAMING_PROFILE_CONTENT:
            _LOGGER.info("Sysctl profile file is already correctly configured.")
            # You might still want to apply it if live settings are different,
            # but for simplicity, we assume file presence means it's configured.
            return TuneResult(success=True, changed=False, message="Sysctl performance profile is already configured.")

        _LOGGER.info("Writing sysctl performance profile configuration.")
        success, error = atomic_write_to_file(SYSCTL_CONFIG_PATH, GAMING_PROFILE_CONTENT + "\n")
        if not success:
            return TuneResult(success=False, changed=False, message=f"Failed to write sysctl config: {error}")

        try:
            run(["sysctl", "--system"], check=True)
            _LOGGER.info("Successfully applied live sysctl settings.")
            return TuneResult(success=True, changed=True, message="System performance profile was successfully applied.")
        except SystemCommandError as e:
            _LOGGER.error(f"Failed to apply live sysctl settings: {e}")
            return TuneResult(success=False, changed=True, message=f"Config file written, but failed to apply live settings: {e.stderr}")
    else: # Disabling
        if not SYSCTL_CONFIG_PATH.exists():
            return TuneResult(success=True, changed=False, message="Sysctl performance profile is already disabled.")

        try:
            SYSCTL_CONFIG_PATH.unlink()
            # Optionally, you could reset the values to defaults here and run `sysctl --system`.
            return TuneResult(success=True, changed=True, message="Sysctl performance profile was disabled.")
        except Exception as e:
            _LOGGER.error(f"Failed to remove sysctl config file: {e}")
            return TuneResult(success=False, changed=False, message=f"Failed to disable performance profile: {e}")


def set_zswap_in_grub(enabled: bool) -> TuneResult:
    """
    Manages the kernel parameter to disable zswap permanently via GRUB.
    This function only writes the file; it does not run update-grub.
    """
    # We are setting `zswap.enabled=0`, so `enabled=False` means create the file.
    if not enabled:
        if is_kernel_param_active("zswap.enabled=0"):
            return TuneResult(success=True, changed=False, message="ZSwap is already disabled in the current boot session.")
        if GRUB_ZSWAP_DISABLE_PATH.exists():
            return TuneResult(success=True, changed=False, message="GRUB configuration to disable zswap already exists.", action_needed="update-grub")

        success, error = atomic_write_to_file(GRUB_ZSWAP_DISABLE_PATH, GRUB_ZSWAP_DISABLE_CONTENT + "\n")
        if not success:
            return TuneResult(success=False, changed=False, message=f"Failed to write GRUB config file: {error}")
        return TuneResult(success=True, changed=True, message="GRUB configuration to disable zswap was written.", action_needed="update-grub")
    else: # Re-enabling zswap
        if not GRUB_ZSWAP_DISABLE_PATH.exists():
            return TuneResult(success=True, changed=False, message="ZSwap is already enabled (config file absent).")
        try:
            GRUB_ZSWAP_DISABLE_PATH.unlink()
            return TuneResult(success=True, changed=True, message="GRUB configuration to disable zswap was removed.", action_needed="update-grub")
        except Exception as e:
            return TuneResult(success=False, changed=False, message=f"Failed to remove GRUB config: {e}")


def set_psi_in_grub(enabled: bool) -> TuneResult:
    """
    Manages the kernel parameter to enable/disable PSI permanently via GRUB.
    This function only writes the file; it does not run update-grub.

    Note: This enables or disables the entire PSI subsystem globally. Individual
    resources (CPU, memory, I/O) cannot be controlled separately at boot time.
    """
    if enabled:
        if is_kernel_param_active("psi=1"):
            return TuneResult(success=True, changed=False, message="PSI is already enabled in the current boot session.")
        if GRUB_PSI_ENABLE_PATH.exists():
            return TuneResult(success=True, changed=False, message="GRUB configuration to enable PSI already exists.", action_needed="update-grub")

        success, error = atomic_write_to_file(GRUB_PSI_ENABLE_PATH, GRUB_PSI_ENABLE_CONTENT + "\n")
        if not success:
            return TuneResult(success=False, changed=False, message=f"Failed to write GRUB config file for PSI: {error}")
        return TuneResult(success=True, changed=True, message="GRUB configuration to enable PSI was written.", action_needed="update-grub")
    else: # Disabling PSI
        if not GRUB_PSI_ENABLE_PATH.exists():
            return TuneResult(success=True, changed=False, message="PSI is already disabled (config file absent).")
        try:
            GRUB_PSI_ENABLE_PATH.unlink()
            return TuneResult(success=True, changed=True, message="GRUB configuration to enable PSI was removed.", action_needed="update-grub")
        except Exception as e:
            return TuneResult(success=False, changed=False, message=f"Failed to remove GRUB PSI config: {e}")

