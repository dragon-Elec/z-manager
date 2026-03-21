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
import shutil
import contextlib
from dataclasses import dataclass
from pathlib import Path

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

GRUB_RESUME_CONFIG_PATH = Path("/etc/default/grub.d/99-z-manager-resume.cfg")


# --- Data Structure for Results ---
@dataclass(frozen=True)
class TuneResult:
    """Represents the outcome of a persistent tuning operation."""
    success: bool
    changed: bool
    message: str
    action_needed: str | None = None  # e.g., "reboot", "update-grub"


# --- Helper Functions ---

def is_kernel_param_active(param: str) -> bool:
    """Checks the live kernel command line for a given parameter."""
    try:
        if not (cmdline := read_file("/proc/cmdline")):
            return False
        return param in cmdline.split()
    except Exception as e:
        _LOGGER.warning(f"Could not read /proc/cmdline: {e}")
        return False


def get_swappiness() -> int | None:
    """Reads the current system swappiness value."""
    if not (content := read_file("/proc/sys/vm/swappiness")):
        return None
    try:
        return int(content.strip())
    except (ValueError, TypeError):
        return None


def _revert_sysctl_to_defaults() -> bool:
    """Writes the default sysctl settings to a temporary file and applies them."""
    temp_f_name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_f:
            temp_f_name = temp_f.name
            temp_f.write(DEFAULT_SYSCTL_SETTINGS)
            temp_f.flush()
            run(["sysctl", "--load", temp_f_name], check=True)
        _LOGGER.info("Successfully reverted sysctl settings to defaults.")
        return True
    except (SystemCommandError, OSError) as e:
        _LOGGER.error(f"Failed to revert sysctl settings to defaults: {e}")
        return False
    finally:
        if temp_f_name:
            with contextlib.suppress(OSError):
                os.unlink(temp_f_name)


# --- Core Tuning Functions ---

def apply_sysctl_profile(enable: bool) -> TuneResult:
    """
    Idempotently enables or disables the optimal sysctl performance profile.
    """
    if enable:
        current_content = read_file(SYSCTL_CONFIG_PATH)
        if current_content and current_content.strip() == GAMING_PROFILE_CONTENT:
            _LOGGER.info("Sysctl profile file is already correctly configured.")
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
        except OSError as e:
            _LOGGER.error(f"Failed to remove sysctl config file: {e}")
            return TuneResult(success=False, changed=False, message=f"Failed to disable performance profile: {e}")

        if not _revert_sysctl_to_defaults():
            return TuneResult(success=False, changed=True, message="Profile config removed, but failed to revert live settings.")
        
        return TuneResult(success=True, changed=True, message="Sysctl performance profile was disabled and settings reverted.")


def apply_sysctl_values(settings: dict[str, str]) -> TuneResult:
    """
    Applies custom sysctl values by merging them into the configuration file.
    'settings' is a dict like {'vm.swappiness': '100', 'vm.page-cluster': '0'}.
    """
    if not settings:
        return TuneResult(success=True, changed=False, message="No settings provided.")

    # 1. Read existing file content and parse into a dict
    final_config = {}
    if current_content := read_file(SYSCTL_CONFIG_PATH):
        for line in current_content.splitlines():
            if (line := line.strip()) and not line.startswith("#") and "=" in line:
                k, v = (p.strip() for p in line.split("=", 1))
                final_config[k] = v

    # 2. Update with new values
    changed = any(final_config.get(k) != str(v) for k, v in settings.items())
    
    if not changed and SYSCTL_CONFIG_PATH.exists():
         return TuneResult(success=True, changed=False, message="Settings are already applied in config.")

    for k, v in settings.items():
        final_config[k] = str(v)

    # 3. Serialize back to string
    new_lines = ["# Custom Z-Manager Tuning Configuration"]
    new_lines.extend(f"{k} = {v}" for k, v in sorted(final_config.items()))
    new_content = "\n".join(new_lines) + "\n"

    # 4. Write and Apply
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

# --- Hibernation Boot Config ---

def detect_bootloader() -> str:
    """Returns 'grub', 'systemd-boot', or 'unknown'."""
    if shutil.which("update-grub") or shutil.which("grub-mkconfig") or os.path.exists("/etc/default/grub") or os.path.isdir("/boot/grub"):
        return "grub"
    if os.path.isdir("/boot/efi/loader") or os.path.exists("/usr/bin/bootctl") or os.path.isdir("/boot/efi/EFI/systemd"):
        return "systemd-boot"
    return "unknown"


def update_grub_resume(uuid: str, offset: int | None = None) -> TuneResult:
    """
    Add resume=UUID=... [resume_offset=...] to GRUB config.
    """
    params = f'resume=UUID={uuid}'
    if offset is not None and offset > 0:
        params += f' resume_offset={offset}'
    
    content = f'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT {params}"'
    
    success, error = atomic_write_to_file(GRUB_RESUME_CONFIG_PATH, content + "\n")
    if not success:
        return TuneResult(False, False, f"Failed to write GRUB resume config: {error}")
    
    return TuneResult(True, True, "Resume configuration written to GRUB.", action_needed="update-grub")


def detect_initramfs_system() -> str:
    """Detects if system uses initramfs-tools, dracut, or mkinitcpio."""
    if os.path.isdir("/etc/initramfs-tools") or shutil.which("update-initramfs"):
        return "initramfs-tools"
    if shutil.which("dracut"):
        return "dracut"
    if os.path.exists("/etc/mkinitcpio.conf") or shutil.which("mkinitcpio"):
        return "mkinitcpio"
    return "unknown"


def configure_initramfs_resume(uuid: str, offset: int | None = None) -> TuneResult:
    """
    Configures initramfs (specifically for initramfs-tools on Debian/Ubuntu).
    """
    system = detect_initramfs_system()
    if system != "initramfs-tools":
        return TuneResult(True, False, f"Initramfs system '{system}' auto-configuration not fully implemented yet, but GRUB is set.", action_needed="manual-check")

    # Creating /etc/initramfs-tools/conf.d/resume
    conf_path = Path("/etc/initramfs-tools/conf.d/resume")
    content = f"RESUME=UUID={uuid}\n"
    if offset is not None and offset > 0:
        content += f"RESUME_OFFSET={offset}\n"
        
    success, error = atomic_write_to_file(conf_path, content)
    if not success:
        return TuneResult(False, False, f"Failed to write initramfs resume config: {error}")
        
    return TuneResult(True, True, "Initramfs resume config updated.", action_needed="update-initramfs")


def regenerate_initramfs() -> TuneResult:
    match system := detect_initramfs_system():
        case "initramfs-tools":
            cmd = ["update-initramfs", "-u"]
        case "dracut":
            cmd = ["dracut", "-f", "--regenerate-all"]
        case "mkinitcpio":
            cmd = ["mkinitcpio", "-P"]
        case _:
            return TuneResult(False, False, f"Unknown or unsupported initramfs system: {system}")

    try:
        run(cmd, check=True)
        return TuneResult(True, True, f"Initramfs regenerated successfully ({system}).")
    except SystemCommandError as e:
        return TuneResult(False, False, f"Failed to regenerate initramfs: {e.stderr}")
