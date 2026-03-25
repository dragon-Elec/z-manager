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
import subprocess
from dataclasses import dataclass
from pathlib import Path

from core.utils.common import run, SystemCommandError, read_file
from core.utils.io import atomic_write_to_file, is_root

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
    from core.utils.io import pkexec_write
    from core.utils.privilege import pkexec_sysctl_system
    if enable:
        current_content = read_file(SYSCTL_CONFIG_PATH)
        if current_content and current_content.strip() == GAMING_PROFILE_CONTENT:
            _LOGGER.info("Sysctl profile file is already correctly configured.")
            return TuneResult(success=True, changed=False, message="Sysctl performance profile is already configured.")

        _LOGGER.info("Writing sysctl performance profile configuration.")
        success, error = pkexec_write(str(SYSCTL_CONFIG_PATH), GAMING_PROFILE_CONTENT + "\n")
        if not success:
            return TuneResult(success=False, changed=False, message=f"Failed to write sysctl config: {error}")

        ok, err = pkexec_sysctl_system()
        if not ok:
            _LOGGER.error(f"Failed to apply live sysctl settings: {err}")
            return TuneResult(success=False, changed=True, message=f"Config file written, but failed to apply live settings: {err}")
        
        _LOGGER.info("Successfully applied live sysctl settings.")
        return TuneResult(success=True, changed=True, message="System performance profile was successfully applied.")
    else: # Disabling
        if not SYSCTL_CONFIG_PATH.exists():
            return TuneResult(success=True, changed=False, message="Sysctl performance profile is already disabled.")

        # Removing a file also requires privilege if in /etc/
        # For now, zman-helper write command doesn't support 'delete', 
        # but we can write an empty file or a default one. 
        # Better: let's write DEFAULT_SYSCTL_SETTINGS to the path instead of unlinking
        # to stay within the 'write' whitelist.
        success, error = pkexec_write(str(SYSCTL_CONFIG_PATH), DEFAULT_SYSCTL_SETTINGS + "\n")
        if not success:
            return TuneResult(success=False, changed=False, message=f"Failed to reset sysctl config: {error}")

        ok, err = pkexec_sysctl_system()
        if not ok:
            return TuneResult(success=False, changed=True, message="Profile config reset, but failed to apply live settings.")
        
        return TuneResult(success=True, changed=True, message="Sysctl performance profile was disabled and settings reverted.")


def apply_sysctl_values(settings: dict[str, str]) -> TuneResult:
    """
    Applies custom sysctl values by merging them into the configuration file.
    'settings' is a dict like {'vm.swappiness': '100', 'vm.page-cluster': '0'}.
    """
    if not settings:
        return TuneResult(success=True, changed=False, message="No settings provided.")

    from core.utils.io import pkexec_write
    from core.utils.privilege import pkexec_sysctl_system
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
    success, error = pkexec_write(str(SYSCTL_CONFIG_PATH), new_content)
    if not success:
        return TuneResult(success=False, changed=False, message=f"Failed to write config: {error}")

    ok, err = pkexec_sysctl_system()
    if not ok:
        return TuneResult(success=False, changed=True, message=f"Config saved, but sysctl failed: {err}")
    
    return TuneResult(success=True, changed=True, message="Successfully applied custom sysctl settings.")

def set_zswap_in_grub(enabled: bool) -> TuneResult:
    """
    Manages the kernel parameter to disable zswap permanently via GRUB.
    This function only writes the file; it does not run update-grub.
    """
    if detect_bootloader() != "grub":
        return TuneResult(
            success=False, 
            changed=False, 
            message="Feature unavailable: Automatic configuration requires GRUB bootloader.",
            action_needed="Manual entry: Add 'zswap.enabled=0' to your bootloader's kernel parameters."
        )

    from core.utils.io import pkexec_write
    # We are setting `zswap.enabled=0`, so `enabled=False` means we want the config present.
    if not enabled:
        if is_kernel_param_active("zswap.enabled=0"):
            return TuneResult(success=True, changed=False, message="ZSwap is already disabled in the current boot session.")
        
        current = read_file(GRUB_ZSWAP_DISABLE_PATH)
        if current and GRUB_ZSWAP_DISABLE_CONTENT in current:
            return TuneResult(success=True, changed=False, message="GRUB configuration to disable zswap already exists.", action_needed="update-grub")

        success, error = pkexec_write(str(GRUB_ZSWAP_DISABLE_PATH), GRUB_ZSWAP_DISABLE_CONTENT + "\n")
        if not success:
            return TuneResult(success=False, changed=False, message=f"Failed to write GRUB config file: {error}")
        return TuneResult(success=True, changed=True, message="GRUB configuration to disable zswap was written.", action_needed="update-grub")
    else: # Re-enabling zswap
        current = read_file(GRUB_ZSWAP_DISABLE_PATH)
        if not current or GRUB_ZSWAP_DISABLE_CONTENT not in current:
            return TuneResult(success=True, changed=False, message="ZSwap is already enabled (config file absent or cleared).")
        
        # Instead of unlink, write an empty file or a comment to "disable" the drop-in
        success, error = pkexec_write(str(GRUB_ZSWAP_DISABLE_PATH), "# ZSwap disabling removed by Z-Manager\n")
        if not success:
             return TuneResult(success=False, changed=False, message=f"Failed to remove GRUB config: {error}")
        return TuneResult(success=True, changed=True, message="GRUB configuration to disable zswap was cleared.", action_needed="update-grub")


def set_psi_in_grub(enabled: bool) -> TuneResult:
    """
    Manages the kernel parameter to enable/disable PSI permanently via GRUB.
    This function only writes the file; it does not run update-grub.
    """
    if detect_bootloader() != "grub":
        return TuneResult(
            success=False, 
            changed=False, 
            message="Feature unavailable: Automatic configuration requires GRUB bootloader.",
            action_needed="Manual entry: Add 'psi=1' to your bootloader's kernel parameters."
        )

    from core.utils.io import pkexec_write
    if enabled:
        if is_kernel_param_active("psi=1"):
            return TuneResult(success=True, changed=False, message="PSI is already enabled in the current boot session.")
            
        current = read_file(GRUB_PSI_ENABLE_PATH)
        if current and GRUB_PSI_ENABLE_CONTENT in current:
            return TuneResult(success=True, changed=False, message="GRUB configuration to enable PSI already exists.", action_needed="update-grub")

        success, error = pkexec_write(str(GRUB_PSI_ENABLE_PATH), GRUB_PSI_ENABLE_CONTENT + "\n")
        if not success:
            return TuneResult(success=False, changed=False, message=f"Failed to write GRUB config file for PSI: {error}")
        return TuneResult(success=True, changed=True, message="GRUB configuration to enable PSI was written.", action_needed="update-grub")
    else: # Disabling PSI
        current = read_file(GRUB_PSI_ENABLE_PATH)
        if not current or GRUB_PSI_ENABLE_CONTENT not in current:
            return TuneResult(success=True, changed=False, message="PSI is already disabled (config file absent or cleared).")
        
        success, error = pkexec_write(str(GRUB_PSI_ENABLE_PATH), "# PSI enabling removed by Z-Manager\n")
        if not success:
            return TuneResult(success=False, changed=False, message=f"Failed to remove GRUB PSI config: {error}")
        return TuneResult(success=True, changed=True, message="GRUB configuration to enable PSI was cleared.", action_needed="update-grub")

# --- Hibernation Boot Config ---

def detect_bootloader() -> str:
    """Returns 'grub', 'systemd-boot', or 'unknown'."""
    if shutil.which("update-grub") or shutil.which("grub-mkconfig") or os.path.exists("/etc/default/grub") or os.path.isdir("/boot/grub"):
        return "grub"
    if os.path.isdir("/boot/efi/loader") or os.path.exists("/usr/bin/bootctl") or os.path.isdir("/boot/efi/EFI/systemd"):
        return "systemd-boot"
    return "unknown"


def pkexec_update_grub() -> TuneResult:
    """Runs update-grub via pkexec."""
    if is_root():
        try:
            # Try update-grub first
            if shutil.which("update-grub"):
                run(["update-grub"], check=True)
            elif shutil.which("grub-mkconfig"):
                # Fallback to grub-mkconfig with common paths
                for p in ["/boot/grub/grub.cfg", "/boot/efi/EFI/fedora/grub.cfg", "/boot/grub2/grub.cfg"]:
                    if os.path.exists(p):
                        run(["grub-mkconfig", "-o", p], check=True)
                        break
                else:
                    return TuneResult(False, False, "Could not find grub.cfg to update.")
            else:
                return TuneResult(False, False, "Neither update-grub nor grub-mkconfig found.")
            return TuneResult(True, True, "GRUB configuration updated successfully.")
        except SystemCommandError as e:
            return TuneResult(False, False, f"Failed to update GRUB: {e.stderr}")
    
    helper_path = os.path.join(os.path.dirname(__file__), "zman_helper.py")
    try:
        proc = subprocess.run(["pkexec", helper_path, "update-grub"], capture_output=True, text=True)
        if proc.returncode == 0:
            return TuneResult(True, True, "GRUB configuration updated successfully via pkexec.")
        else:
            return TuneResult(False, False, f"pkexec update-grub failed: {proc.stderr.strip()}")
    except Exception as e:
        return TuneResult(False, False, str(e))


def update_grub_resume(uuid: str, offset: int | None = None) -> TuneResult:
    """
    Add resume=UUID=... [resume_offset=...] to GRUB config.
    Uses pkexec for writing to /etc/default/grub.d/
    """
    if detect_bootloader() != "grub":
        return TuneResult(
            success=False, 
            changed=False, 
            message="Feature unavailable: Automatic resume configuration requires GRUB.",
            action_needed=f"Manual entry: Add 'resume=UUID={uuid}' to your bootloader config."
        )

    params = f'resume=UUID={uuid}'
    if offset is not None and offset > 0:
        params += f' resume_offset={offset}'
    
    content = f'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT {params}"'
    
    from core.utils.io import pkexec_write
    success, error = pkexec_write(str(GRUB_RESUME_CONFIG_PATH), content + "\n")
    if not success:
        return TuneResult(False, False, f"Failed to write GRUB resume config: {error}")
    
    return TuneResult(True, True, "Resume configuration written to GRUB drop-in.", action_needed="update-grub")


def detect_initramfs_system() -> str:
    """Detects if system uses initramfs-tools, dracut, or mkinitcpio."""
    if os.path.isdir("/etc/initramfs-tools") or shutil.which("update-initramfs"):
        return "initramfs-tools"
    if shutil.which("dracut"):
        return "dracut"
    if os.path.exists("/etc/mkinitcpio.conf") or shutil.which("mkinitcpio"):
        return "mkinitcpio"
    return "unknown"


def pkexec_update_initramfs() -> TuneResult:
    """Regenerates initramfs via pkexec."""
    if is_root():
        return regenerate_initramfs()
        
    helper_path = os.path.join(os.path.dirname(__file__), "zman_helper.py")
    try:
        proc = subprocess.run(["pkexec", helper_path, "update-initramfs"], capture_output=True, text=True)
        if proc.returncode == 0:
            return TuneResult(True, True, "Initramfs regenerated successfully via pkexec.")
        else:
            return TuneResult(False, False, f"pkexec update-initramfs failed: {proc.stderr.strip()}")
    except Exception as e:
        return TuneResult(False, False, str(e))


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
        
    from core.utils.io import pkexec_write
    success, error = pkexec_write(str(conf_path), content)
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


def apply_hibernation_boot_config(uuid: str, offset: int | None = None) -> TuneResult:
    """
    High-level orchestrator for the 'Bootloader Handshake'.
    1. Writes GRUB resume parameters.
    2. Writes Initramfs resume parameters.
    3. Runs update-grub.
    4. Runs update-initramfs.
    """
    _LOGGER.info(f"Starting hibernation boot configuration (UUID={uuid}, Offset={offset})")
    
    # 1. Update GRUB config
    grub_res = update_grub_resume(uuid, offset)
    if not grub_res.success:
        return grub_res
    
    # 2. Update Initramfs config
    init_res = configure_initramfs_resume(uuid, offset)
    if not init_res.success:
        return init_res
    
    # 3. Run update-grub
    _LOGGER.info("Running update-grub...")
    update_grub_res = pkexec_update_grub()
    if not update_grub_res.success:
        return update_grub_res
        
    # 4. Run update-initramfs
    _LOGGER.info("Regenerating initramfs...")
    update_init_res = pkexec_update_initramfs()
    if not update_init_res.success:
        return update_init_res
        
    return TuneResult(True, True, "Hibernation boot configuration applied successfully. A reboot is required.")
