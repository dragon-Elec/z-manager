# zman/core/tuning.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .system import run, SystemCommandError
# utils.py is a core dependency, which is correct.
from ..utils import atomic_write_to_file, read_file_content, get_swappiness

# --- Core Constants ---
SYSCTL_CONFIG_PATH = "/etc/sysctl.d/99-z-manager.conf"
GAMING_PROFILE_CONTENT = """# Kernel tuning for ZRAM, recommended by Pop!_OS and others.
vm.swappiness = 180
vm.watermark_boost_factor = 0
vm.watermark_scale_factor = 125
vm.page-cluster = 0""".strip()

GRUB_CONFIG_PATH = "/etc/default/grub.d/99-z-manager-disable-zswap.cfg"
GRUB_ZSWAP_DISABLE_CONTENT = 'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT zswap.enabled=0"'


# --- Data Structure for Results ---
@dataclass(frozen=True)
class TuneResult:
    """Represents the outcome of a tuning operation."""
    success: bool
    changed: bool
    message: str
    action_needed: Optional[str] = None  # e.g., "reboot", "update-grub", "manual_update_grub"


# --- Core Helper Functions ---

def is_zswap_disabled_in_boot() -> bool:
    """
    Checks the live kernel command line to see if zswap is already disabled.
    This re-introduces the smart check from the original implementation.
    """
    # /proc/cmdline is a stable kernel interface.
    cmdline = read_file_content("/proc/cmdline")
    return "zswap.enabled=0" in (cmdline or "")


# --- Core Tuning Functions ---

def apply_sysctl_profile() -> TuneResult:
    """
    Checks and applies the optimal sysctl performance profile idempotently.
    Returns a TuneResult object detailing the outcome.
    """
    config_content = read_file_content(SYSCTL_CONFIG_PATH) or ""
    current_swappiness = get_swappiness()

    # Whitespace-insensitive comparison for robustness.
    is_file_correct = config_content.strip() == GAMING_PROFILE_CONTENT
    is_live_correct = current_swappiness == 180

    if is_file_correct and is_live_correct:
        return TuneResult(success=True, changed=False, message="System performance profile is already correctly configured and applied.")

    if not is_file_correct:
        success, error = atomic_write_to_file(SYSCTL_CONFIG_PATH, GAMING_PROFILE_CONTENT + "\n")
        if not success:
            return TuneResult(success=False, changed=False, message=f"Failed to write sysctl config: {error}")
    
    # FIX: Only apply live settings if they are not already correct.
    # This restores the more efficient logic from the original code.
    if not is_live_correct:
        try:
            run(["sysctl", "--system"], check=True)
        except SystemCommandError as e:
            # If we wrote the file but this failed, it's a partial success.
            return TuneResult(success=False, changed=True, message=f"Config file written, but failed to apply live settings: {e.stderr}")

    return TuneResult(success=True, changed=True, message="System performance profile was successfully applied.")


def disable_zswap_in_grub(run_update_grub: bool) -> TuneResult:
    """
    Checks and applies the kernel parameter to disable zswap permanently via GRUB.
    Returns a TuneResult object detailing the outcome and any required user action.
    """
    # REGRESSION FIX: Check the live system state first.
    if is_zswap_disabled_in_boot():
        return TuneResult(
            success=True,
            changed=False,
            message="ZSwap is already disabled in the current boot session."
        )

    config_content = read_file_content(GRUB_CONFIG_PATH) or ""
    is_file_correct = config_content.strip() == GRUB_ZSWAP_DISABLE_CONTENT

    if is_file_correct:
        # The file is correct, but the live check failed, so the user needs to act.
        return TuneResult(
            success=True,
            changed=False,
            message="GRUB configuration file to disable zswap is already in place.",
            action_needed="update-grub" # Action is to run update-grub and reboot.
        )

    # Write the file since it's incorrect or missing.
    success, error = atomic_write_to_file(GRUB_CONFIG_PATH, GRUB_ZSWAP_DISABLE_CONTENT + "\n")
    if not success:
        return TuneResult(success=False, changed=False, message=f"Failed to write GRUB config file: {error}")

    if run_update_grub:
        try:
            run(["update-grub"], check=True)
            return TuneResult(
                success=True,
                changed=True,
                message="GRUB configuration written and 'update-grub' executed successfully.",
                action_needed="reboot"
            )
        except SystemCommandError as e:
            return TuneResult(
                success=False,
                changed=True,
                message=f"GRUB config written, but 'update-grub' failed: {e.stderr}",
                action_needed="manual_update_grub"
            )
    else:
        # We wrote the file but were not asked to update grub.
        return TuneResult(
            success=True,
            changed=True,
            message="GRUB configuration file to disable zswap was written.",
            action_needed="update-grub"
        )
