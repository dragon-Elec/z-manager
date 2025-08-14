# zman/cli.py
import typer
from .commands.check import run_check
from .commands.configure import run_configure
from .commands.tune import run_tune
from .commands.logs import run_logs
from .commands.device import (
    run_device_restart,
    run_device_reset,
    set_writeback_device,
    clear_writeback_device,
    show_writeback_status,
    persist_writeback_device,
)
from .gui import run_gui
from . import __version__

app = typer.Typer()
device_app = typer.Typer()
app.add_typer(device_app, name="device", help="Manage ZRAM devices at runtime.")


def version_callback(value: bool):
    if value:
        typer.echo(f"Z-Manager Version: {__version__}")
        raise typer.Exit()

@app.callback()
def main(version: bool = typer.Option(None, "--version", callback=version_callback, is_eager=True)):
    pass

@app.command()
def check():
    """Runs a health check on your ZRAM configuration."""
    run_check()

@app.command()
def configure():
    """Interactively creates and applies a new ZRAM configuration."""
    run_configure()

@app.command()
def tune(
    profile: bool = typer.Option(False, "--profile", help="Apply the recommended 'gaming/desktop' performance profile."),
    disable_zswap: bool = typer.Option(False, "--disable-zswap", help="Permanently disable zswap (requires grub update + reboot).")
):
    """Tunes system parameters for optimal ZRAM performance."""
    run_tune(profile=profile, disable_zswap=disable_zswap)

@app.command()
def logs(
    count: int = typer.Option(
        25,
        "--count",
        "-n",
        help="Number of log entries to show."
    )
):
    """Shows the latest logs for the zram-setup service."""
    run_logs(count=count)

@device_app.command("restart")
def device_restart(
    device_name: str = typer.Argument("zram0", help="The ZRAM device to restart (e.g., 'zram0').")
):
    """Restart the ZRAM device service to apply new settings."""
    run_device_restart(device_name=device_name)

@device_app.command("set-writeback")
def device_set_writeback(
    device_name: str = typer.Argument("zram0", help="The ZRAM device (e.g., 'zram0')."),
    writeback_device: str = typer.Argument(..., help="Block device path for writeback (e.g., /dev/nvme0n1p3 or /dev/zvol/pool/vol)"),
    force: bool = typer.Option(False, "--force", help="Reset active device if needed to apply writeback."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show actions without executing them.")
):
    """Set a writeback block device for the given zram device."""
    set_writeback_device(device_name=device_name, writeback_device=writeback_device, force=force, dry_run=dry_run)

@device_app.command("clear-writeback")
def device_clear_writeback(
    device_name: str = typer.Argument("zram0", help="The ZRAM device (e.g., 'zram0')."),
    force: bool = typer.Option(False, "--force", help="Reset active device if needed to clear writeback."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show actions without executing them.")
):
    """Clear the writeback configuration for the given zram device."""
    clear_writeback_device(device_name=device_name, force=force, dry_run=dry_run)

@device_app.command("status")
def device_status(
    device_name: str = typer.Argument("zram0", help="The ZRAM device (e.g., 'zram0').")
):
    """Show writeback and compression status for the device."""
    show_writeback_status(device_name=device_name)

@device_app.command("persist-writeback")
def device_persist_writeback(
    device_name: str = typer.Argument("zram0", help="Target zram device (e.g., 'zram0')."),
    writeback_device: str = typer.Argument(..., help="Block device path to persist (e.g., /dev/nvme0n1p3 or /dev/zvol/pool/vol). Use 'none' to remove."),
    apply_now: bool = typer.Option(True, "--apply-now/--no-apply-now", help="Reload systemd and restart the unit to apply immediately.")
):
    """
    Persist writeback-device into /etc/systemd/zram-generator.conf.
    Pass 'none' to remove the writeback-device key.
    """
    persist_value = None if writeback_device.lower() == "none" else writeback_device
    persist_writeback_device(device_name=device_name, writeback_device=persist_value, apply_now=apply_now)

@device_app.command("reset")
def device_reset(
    device_name: str = typer.Argument("zram0", help="The ZRAM device to reset (e.g., 'zram0').")
):
    """Reset a ZRAM device, wiping its contents."""
    run_device_reset(device_name=device_name)


@app.command()
def monitor():
    """Launch the live monitoring GUI dashboard."""
    run_gui()
