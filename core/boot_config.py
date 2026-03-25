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
import contextlib
from dataclasses import dataclass
from pathlib import Path

from core.utils.common import run, SystemCommandError, read_file
from core.utils.io import atomic_write_to_file, is_root
from core.utils.bootloader import detect_bootloader
from core.utils.kernel_cmdline import is_kernel_param_active
from core.utils.grub_paths import (
    SYSCTL_CONFIG_PATH,
    GRUB_ZSWAP_DISABLE_PATH,
    GRUB_ZSWAP_DISABLE_CONTENT,
    GRUB_PSI_ENABLE_PATH,
    GRUB_PSI_ENABLE_CONTENT,
    SYSCTL_DEFAULT_SETTINGS,
    SYSCTL_GAMING_PROFILE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TuneResult:
    """Represents the outcome of a persistent tuning operation."""

    success: bool
    changed: bool
    message: str
    action_needed: str | None = None


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
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_f:
            temp_f_name = temp_f.name
            temp_f.write(SYSCTL_DEFAULT_SETTINGS)
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


def apply_sysctl_profile(enable: bool) -> TuneResult:
    """
    Idempotently enables or disables the optimal sysctl performance profile.
    """
    from core.utils.io import pkexec_write
    from core.utils.privilege import pkexec_sysctl_system

    if enable:
        current_content = read_file(SYSCTL_CONFIG_PATH)
        if current_content and current_content.strip() == SYSCTL_GAMING_PROFILE:
            _LOGGER.info("Sysctl profile file is already correctly configured.")
            return TuneResult(
                success=True,
                changed=False,
                message="Sysctl performance profile is already configured.",
            )

        _LOGGER.info("Writing sysctl performance profile configuration.")
        success, error = pkexec_write(
            str(SYSCTL_CONFIG_PATH), SYSCTL_GAMING_PROFILE + "\n"
        )
        if not success:
            return TuneResult(
                success=False,
                changed=False,
                message=f"Failed to write sysctl config: {error}",
            )

        ok, err = pkexec_sysctl_system()
        if not ok:
            _LOGGER.error(f"Failed to apply live sysctl settings: {err}")
            return TuneResult(
                success=False,
                changed=True,
                message=f"Config file written, but failed to apply live settings: {err}",
            )

        _LOGGER.info("Successfully applied live sysctl settings.")
        return TuneResult(
            success=True,
            changed=True,
            message="System performance profile was successfully applied.",
        )
    else:
        if not SYSCTL_CONFIG_PATH.exists():
            return TuneResult(
                success=True,
                changed=False,
                message="Sysctl performance profile is already disabled.",
            )

        success, error = pkexec_write(
            str(SYSCTL_CONFIG_PATH), SYSCTL_DEFAULT_SETTINGS + "\n"
        )
        if not success:
            return TuneResult(
                success=False,
                changed=False,
                message=f"Failed to reset sysctl config: {error}",
            )

        ok, err = pkexec_sysctl_system()
        if not ok:
            return TuneResult(
                success=False,
                changed=True,
                message="Profile config reset, but failed to apply live settings.",
            )

        return TuneResult(
            success=True,
            changed=True,
            message="Sysctl performance profile was disabled and settings reverted.",
        )


def apply_sysctl_values(settings: dict[str, str]) -> TuneResult:
    """
    Applies custom sysctl values by merging them into the configuration file.
    'settings' is a dict like {'vm.swappiness': '100', 'vm.page-cluster': '0'}.
    """
    if not settings:
        return TuneResult(success=True, changed=False, message="No settings provided.")

    from core.utils.io import pkexec_write
    from core.utils.privilege import pkexec_sysctl_system

    final_config = {}
    if current_content := read_file(SYSCTL_CONFIG_PATH):
        for line in current_content.splitlines():
            if (line := line.strip()) and not line.startswith("#") and "=" in line:
                k, v = (p.strip() for p in line.split("=", 1))
                final_config[k] = v

    changed = any(final_config.get(k) != str(v) for k, v in settings.items())

    if not changed and SYSCTL_CONFIG_PATH.exists():
        return TuneResult(
            success=True,
            changed=False,
            message="Settings are already applied in config.",
        )

    for k, v in settings.items():
        final_config[k] = str(v)

    new_lines = ["# Custom Z-Manager Tuning Configuration"]
    new_lines.extend(f"{k} = {v}" for k, v in sorted(final_config.items()))
    new_content = "\n".join(new_lines) + "\n"

    success, error = pkexec_write(str(SYSCTL_CONFIG_PATH), new_content)
    if not success:
        return TuneResult(
            success=False, changed=False, message=f"Failed to write config: {error}"
        )

    ok, err = pkexec_sysctl_system()
    if not ok:
        return TuneResult(
            success=False,
            changed=True,
            message=f"Config saved, but sysctl failed: {err}",
        )

    return TuneResult(
        success=True,
        changed=True,
        message="Successfully applied custom sysctl settings.",
    )


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
            action_needed="Manual entry: Add 'zswap.enabled=0' to your bootloader's kernel parameters.",
        )

    from core.utils.io import pkexec_write

    if not enabled:
        if is_kernel_param_active("zswap.enabled=0"):
            return TuneResult(
                success=True,
                changed=False,
                message="ZSwap is already disabled in the current boot session.",
            )

        current = read_file(GRUB_ZSWAP_DISABLE_PATH)
        if current and GRUB_ZSWAP_DISABLE_CONTENT in current:
            return TuneResult(
                success=True,
                changed=False,
                message="GRUB configuration to disable zswap already exists.",
                action_needed="update-grub",
            )

        success, error = pkexec_write(
            str(GRUB_ZSWAP_DISABLE_PATH), GRUB_ZSWAP_DISABLE_CONTENT + "\n"
        )
        if not success:
            return TuneResult(
                success=False,
                changed=False,
                message=f"Failed to write GRUB config file: {error}",
            )
        return TuneResult(
            success=True,
            changed=True,
            message="GRUB configuration to disable zswap was written.",
            action_needed="update-grub",
        )
    else:
        current = read_file(GRUB_ZSWAP_DISABLE_PATH)
        if not current or GRUB_ZSWAP_DISABLE_CONTENT not in current:
            return TuneResult(
                success=True,
                changed=False,
                message="ZSwap is already enabled (config file absent or cleared).",
            )

        success, error = pkexec_write(
            str(GRUB_ZSWAP_DISABLE_PATH), "# ZSwap disabling removed by Z-Manager\n"
        )
        if not success:
            return TuneResult(
                success=False,
                changed=False,
                message=f"Failed to remove GRUB config: {error}",
            )
        return TuneResult(
            success=True,
            changed=True,
            message="GRUB configuration to disable zswap was cleared.",
            action_needed="update-grub",
        )


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
            action_needed="Manual entry: Add 'psi=1' to your bootloader config.",
        )

    from core.utils.io import pkexec_write

    if enabled:
        if is_kernel_param_active("psi=1"):
            return TuneResult(
                success=True,
                changed=False,
                message="PSI is already enabled in the current boot session.",
            )

        current = read_file(GRUB_PSI_ENABLE_PATH)
        if current and GRUB_PSI_ENABLE_CONTENT in current:
            return TuneResult(
                success=True,
                changed=False,
                message="GRUB configuration to enable PSI already exists.",
                action_needed="update-grub",
            )

        success, error = pkexec_write(
            str(GRUB_PSI_ENABLE_PATH), GRUB_PSI_ENABLE_CONTENT + "\n"
        )
        if not success:
            return TuneResult(
                success=False,
                changed=False,
                message=f"Failed to write GRUB config file for PSI: {error}",
            )
        return TuneResult(
            success=True,
            changed=True,
            message="GRUB configuration to enable PSI was written.",
            action_needed="update-grub",
        )
    else:
        current = read_file(GRUB_PSI_ENABLE_PATH)
        if not current or GRUB_PSI_ENABLE_CONTENT not in current:
            return TuneResult(
                success=True,
                changed=False,
                message="PSI is already disabled (config file absent or cleared).",
            )

        success, error = pkexec_write(
            str(GRUB_PSI_ENABLE_PATH), "# PSI enabling removed by Z-Manager\n"
        )
        if not success:
            return TuneResult(
                success=False,
                changed=False,
                message=f"Failed to remove GRUB PSI config: {error}",
            )
        return TuneResult(
            success=True,
            changed=True,
            message="GRUB configuration to enable PSI was cleared.",
            action_needed="update-grub",
        )
