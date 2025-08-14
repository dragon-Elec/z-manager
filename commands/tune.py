# zman/commands/tune.py
import typer
from ..utils import is_root, run_command, atomic_write_to_file, read_file_content, get_swappiness

# --- Constants ---
SYSCTL_CONFIG_PATH = "/etc/sysctl.d/99-z-manager.conf"
GAMING_PROFILE_CONTENT = """# Kernel tuning for ZRAM, recommended by Pop!_OS and others.
vm.swappiness = 180
vm.watermark_boost_factor = 0
vm.watermark_scale_factor = 125
vm.page-cluster = 0""".strip()
GRUB_CONFIG_PATH = "/etc/default/grub.d/99-z-manager-disable-zswap.cfg"
GRUB_ZSWAP_DISABLE_CONTENT = 'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT zswap.enabled=0"'

# --- Your excellent helper function ---
def _write_file_if_confirmed(path: str, content: str, reason: str) -> bool:
    """Asks for confirmation, then atomically writes content to a file."""
    typer.echo(reason)
    if not typer.confirm("Proceed?"):
        raise typer.Abort()

    # The content passed here should already have its final newline
    success, error = atomic_write_to_file(path, content)
    if not success:
        typer.secho(f"❌ Failed to write file '{path}'! Error: {error}", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)
    
    typer.secho(f"✅ Successfully wrote to {path}", fg=typer.colors.GREEN)
    return True

# --- Your idempotent logic, now with the bug fix ---
def _check_and_apply_sysctl_profile():
    typer.secho("\n--- Applying Performance Profile ---", bold=True)
    current_swappiness = get_swappiness()
    config_content = read_file_content(SYSCTL_CONFIG_PATH) or ""
    
    # FIX: Use .strip() on both strings to ensure a reliable comparison
    is_file_correct = config_content.strip() == GAMING_PROFILE_CONTENT.strip()
    is_live_correct = current_swappiness == 180

    if is_file_correct and is_live_correct:
        typer.secho("✅ System is already tuned. No action needed.", fg=typer.colors.GREEN)
        return

    if not is_file_correct:
        _write_file_if_confirmed(SYSCTL_CONFIG_PATH, GAMING_PROFILE_CONTENT + "\n",
                                 f"This will create/overwrite '{SYSCTL_CONFIG_PATH}' with optimal settings.")

    # Re-check live status only if we need to apply it.
    current_swappiness = get_swappiness()
    if current_swappiness != 180:
        typer.echo("Applying settings to the live system...")
        _, stderr, returncode = run_command("sysctl --system")
        if returncode != 0:
            typer.secho(f"❌ Failed to apply live settings! Error: {stderr}", fg=typer.colors.RED, bold=True)
            raise typer.Exit(code=1)
        typer.secho("✅ System parameters applied successfully.", fg=typer.colors.GREEN)

def _check_and_disable_zswap():
    typer.secho("\n--- Disabling ZSwap Permanently ---", bold=True)
    cmdline, _, _ = run_command("cat /proc/cmdline")
    if "zswap.enabled=0" in cmdline:
        typer.secho("✅ zswap is already disabled in current boot parameters.", fg=typer.colors.GREEN)
        return

    config_content = read_file_content(GRUB_CONFIG_PATH) or ""
    
    if config_content.strip() == GRUB_ZSWAP_DISABLE_CONTENT.strip():
        typer.secho(f"✅ Config file '{GRUB_CONFIG_PATH}' is already correct.", fg=typer.colors.GREEN)
        typer.secho("\n--- ⚠️ IMPORTANT ⚠️ ---", fg=typer.colors.YELLOW, bold=True)
        typer.echo("You still need to run 'sudo update-grub' and reboot for it to take effect.")
        return

    if _write_file_if_confirmed(GRUB_CONFIG_PATH, GRUB_ZSWAP_DISABLE_CONTENT + "\n",
                                f"This will create/overwrite '{GRUB_CONFIG_PATH}' to disable zswap on the next boot."):
       
       typer.secho("\n--- Final Step: Update GRUB ---", bold=True)
       
       if typer.confirm("Do you want to run 'update-grub' now to apply this change?"):
           typer.echo("Running 'update-grub'...")
           
           stdout, stderr, returncode = run_command("update-grub")
           
           if returncode == 0:
               typer.secho("✅ 'update-grub' completed successfully.", fg=typer.colors.GREEN)
               typer.secho("A reboot is now required for the change to take full effect.", bold=True)
           else:
               typer.secho("❌ 'update-grub' failed!", fg=typer.colors.RED, bold=True)
               typer.secho(f"   Error: {stderr}", fg=typer.colors.RED)
               typer.echo("\nPlease run 'sudo update-grub' manually and then reboot.")
       else:
           typer.secho("\n--- ⚠️ ACTION REQUIRED ⚠️ ---", fg=typer.colors.YELLOW, bold=True)
           typer.echo("You MUST run 'sudo update-grub' and then reboot for the change to take effect.", bold=True)

def run_tune(
    profile: bool = typer.Option(False, "--profile", help="Apply the recommended 'gaming/desktop' performance profile."),
    disable_zswap: bool = typer.Option(False, "--disable-zswap", help="Permanently disable zswap (requires grub update + reboot).")
):
    """Tunes system parameters for optimal ZRAM performance."""
    # This logic from your version is already perfect.
    if not profile and not disable_zswap:
        typer.secho("No tuning option selected. Use --profile or --disable-zswap.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)
    if not is_root():
        typer.secho("Error: Tuning system parameters requires root privileges. Please run with 'sudo'.", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)
    if profile:
        _check_and_apply_sysctl_profile()
    if disable_zswap:
        _check_and_disable_zswap()
