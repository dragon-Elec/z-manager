# zman/core/boot_config.py
"""
Manages persistent, boot-time system configuration.

This core module is responsible for creating and managing configuration files
in system directories like /etc/sysctl.d/ and /etc/default/grub.d/
to ensure that tuning settings survive a reboot.
"""
from __future__ import annotations

import logging
import tempfile
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .os_utils import run, SystemCommandError, atomic_write_to_file, read_file

_LOGGER = logging.getLogger(__name__)

# --- Core Constants ---
SYSCTL_CONFIG_PATH = Path("/etc/sysctl.d/99-z-manager.conf")
# TODO: This is a temporary solution. A more robust solution will be implemented later.
# The ideal solution would be to read the default values from the system, but that is not a straightforward task.
DEFAULT_SYSCTL_SETTINGS = """# Default kernel tuning values.
vm.swappiness = 60
vm.watermark_boost_factor = 150
vm.watermark_scale_factor = 10
vm.page-cluster = 3
""".strip()

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
        cmdline = read_file("/proc/cmdline")
        if not cmdline:
            return False
        return param in cmdline.split()
    except Exception as e:
        _LOGGER.warning(f"Could not read /proc/cmdline: {e}")
        return False


def get_swappiness() -> int | None:
    """Reads the current system swappiness value."""
    content = read_file("/proc/sys/vm/swappiness")
    if content:
        try:
            return int(content.strip())
        except (ValueError, TypeError):
            return None
    return None


def _revert_sysctl_to_defaults() -> bool:
    """Writes the default sysctl settings to a temporary file and applies them."""
    try:
        # Use a temporary file to apply the default settings
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_f:
            temp_f.write(DEFAULT_SYSCTL_SETTINGS)
            temp_f.flush()
            run(["sysctl", "--load", temp_f.name], check=True)
        os.unlink(temp_f.name)
        _LOGGER.info("Successfully reverted sysctl settings to defaults.")
        return True
    except (SystemCommandError, OSError) as e:
        _LOGGER.error(f"Failed to revert sysctl settings to defaults: {e}")
        return False


# --- Core Tuning Functions ---

def apply_sysctl_profile(enable: bool) -> TuneResult:
    """
    Idempotently enables or disables the optimal sysctl performance profile.
    """
    if enable:
        current_content = read_file(SYSCTL_CONFIG_PATH)
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
            if not _revert_sysctl_to_defaults():
                # If reverting fails, the config file is already deleted, which is not ideal.
                # However, the user can re-enable and then disable again to retry.
                return TuneResult(success=False, changed=True, message="Profile disabled, but failed to revert live settings.")
            return TuneResult(success=True, changed=True, message="Sysctl performance profile was disabled and settings reverted.")
        except Exception as e:
            _LOGGER.error(f"Failed to remove sysctl config file: {e}")
            return TuneResult(success=False, changed=False, message=f"Failed to disable performance profile: {e}")


def apply_sysctl_values(settings: dict[str, str]) -> TuneResult:
    """
    Applies custom sysctl values by merging them into the configuration file.
    'settings' is a dict like {'vm.swappiness': '100', 'vm.page-cluster': '0'}.
    """
    if not settings:
        return TuneResult(success=True, changed=False, message="No settings provided.")

    # 1. Read existing file content (or start fresh)
    existing_lines = []
    current_content = read_file(SYSCTL_CONFIG_PATH)
    if current_content:
        existing_lines = current_content.splitlines()

    # 2. Parse existing content into a dict to allow merging
    final_config = {}
    
    # helper to parse line "key = value"
    for line in existing_lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            parts = line.split("=", 1)
            k = parts[0].strip()
            v = parts[1].strip()
            final_config[k] = v

    # 3. Update with new values
    changed = False
    for k, v in settings.items():
        if final_config.get(k) != str(v):
            final_config[k] = str(v)
            changed = True
    
    if not changed and SYSCTL_CONFIG_PATH.exists():
         return TuneResult(success=True, changed=False, message="Settings are already applied in config.")

    # 4. Serialize back to string
    # We add a header
    new_lines = ["# Custom Z-Manager Tuning Configuration"]
    for k, v in sorted(final_config.items()):
        new_lines.append(f"{k} = {v}")
    
    new_content = "\n".join(new_lines) + "\n"

    # 5. Write and Apply
    success, error = atomic_write_to_file(SYSCTL_CONFIG_PATH, new_content)
    if not success:
        return TuneResult(success=False, changed=False, message=f"Failed to write config: {error}")

    try:
        run(["sysctl", "--system"], check=True)
        return TuneResult(success=True, changed=True, message="Successfully applied custom sysctl settings.")
    except SystemCommandError as e:
        return TuneResult(success=False, changed=True, message=f"Config saved, but sysctl failed: {e.stderr}")

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
