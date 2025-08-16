# zman/commands/device.py
import typer
from ..utils import (
    is_root,
    run_command,
)
# New core service imports
from ..core.devices import (
    set_writeback as core_set_writeback,
    clear_writeback as core_clear_writeback,
    get_writeback_status as core_get_writeback_status,
    persist_writeback as core_persist_writeback,
)
from ..core.system import ValidationError, NotBlockDeviceError, SystemCommandError

def _ensure_root():
    """Helper function to check for root privileges and exit if not found."""
    if not is_root():
        typer.secho("Error: This action requires root privileges. Please run with 'sudo'.", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)

def run_device_restart(device_name: str):
    """
    Restarts the systemd service for a given ZRAM device to apply new settings.
    Delegates to core.devices.restart_unit_for_device.
    """
    _ensure_root()
    from ..core.devices import restart_unit_for_device
    try:
        res = restart_unit_for_device(device_name)
        if res.success:
            typer.secho(f"✅ Service '{res.service or f'systemd-zram-setup@{device_name}.service'}' restarted successfully.", fg=typer.colors.GREEN)
            typer.echo("New configuration should now be applied. Use 'z-manager check' to verify.")
        else:
            typer.secho(f"❌ Failed to restart service for '{device_name}'!", fg=typer.colors.RED, bold=True)
            if res.message:
                typer.secho(f"   Error: {res.message}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    except SystemCommandError as e:
        typer.secho(str(e), fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)

def run_device_reset(device_name: str):
    """
    Resets a ZRAM device, wiping its content and freeing its memory.
    Delegates to core.devices.reset_device. Confirmation remains in CLI layer.
    """
    _ensure_root()
    device_path = f"/dev/{device_name}"
    typer.secho(f"⚠️ This will wipe all data from {device_path} and release its memory.", fg=typer.colors.YELLOW, bold=True)
    if not typer.confirm("Are you sure you want to proceed?"):
        typer.echo("Aborted. No changes were made.")
        raise typer.Abort()

    from ..core.devices import reset_device
    try:
        res = reset_device(device_name)
        if res.success:
            typer.secho(f"✅ Device '{device_path}' has been reset successfully.", fg=typer.colors.GREEN)
        else:
            typer.secho(f"❌ Failed to reset device '{device_path}'!", fg=typer.colors.RED, bold=True)
            if res.message:
                typer.secho(f"   Error: {res.message}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    except SystemCommandError as e:
        typer.secho(str(e), fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)


def set_writeback_device(
    device_name: str,
    writeback_device: str,
    force: bool = False,
    dry_run: bool = False
):
    """
    Advanced: Set a writeback device for a zram device.
    Now delegates orchestration to core.devices.ensure_writeback_state.
    """
    _ensure_root()
    if dry_run:
        typer.echo(f"DRY-RUN: Would set writeback for {device_name} to {writeback_device} (force={force})")
        return
    try:
        from ..core.devices import ensure_writeback_state
        orch = ensure_writeback_state(device_name=device_name, desired_writeback=writeback_device, force=force, restart_mode="try")
        if orch.success:
            typer.secho(
                f"✅ Writeback device for '/dev/{device_name}' set to '{writeback_device}'.",
                fg=typer.colors.GREEN
            )
            for act in orch.actions:
                typer.echo(f"   - {act.name}: {'ok' if act.success else 'fail'}{(' - ' + act.message) if act.message else ''}")
        else:
            typer.secho(f"❌ Failed to set writeback on '/dev/{device_name}'.", fg=typer.colors.RED, bold=True)
            for act in orch.actions:
                if not act.success:
                    typer.secho(f"   - {act.name}: {act.message}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    except (ValidationError, NotBlockDeviceError) as e:
        typer.secho(f"❌ {e}", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=2)
    except SystemCommandError as e:
        typer.secho(str(e), fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)

def clear_writeback_device(
    device_name: str,
    force: bool = False,
    dry_run: bool = False
):
    """
    Advanced: Clear writeback for a zram device.
    Now delegates orchestration to core.devices.ensure_writeback_state.
    """
    _ensure_root()
    if dry_run:
        typer.echo(f"DRY-RUN: Would clear writeback for {device_name} (force={force})")
        return
    try:
        from ..core.devices import ensure_writeback_state
        orch = ensure_writeback_state(device_name=device_name, desired_writeback=None, force=force, restart_mode="try")
        if orch.success:
            typer.secho(f"✅ Writeback cleared on '/dev/{device_name}'.", fg=typer.colors.GREEN)
            for act in orch.actions:
                typer.echo(f"   - {act.name}: {'ok' if act.success else 'fail'}{(' - ' + act.message) if act.message else ''}")
        else:
            typer.secho(f"❌ Failed to clear writeback on '/dev/{device_name}'.", fg=typer.colors.RED, bold=True)
            for act in orch.actions:
                if not act.success:
                    typer.secho(f"   - {act.name}: {act.message}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    except ValidationError as e:
        typer.secho(f"❌ {e}", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=2)
    except SystemCommandError as e:
        typer.secho(str(e), fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)

def persist_writeback_device(
    device_name: str,
    writeback_device: str | None,
    apply_now: bool = True
):
    """
    Persist writeback configuration into /etc/systemd/zram-generator.conf.
    Delegates to core.devices.persist_writeback for business logic.
    """
    _ensure_root()
    try:
        result = core_persist_writeback(device_name=device_name, writeback_device=writeback_device, apply_now=apply_now)
        if result.success:
            msg = "✅ Persisted writeback-device"
            if result.applied:
                msg += " and applied via systemd."
            else:
                msg += " (systemd not restarted)."
            typer.secho(msg, fg=typer.colors.GREEN)
        else:
            typer.secho(f"❌ {result.message}", fg=typer.colors.RED, bold=True)
            raise typer.Exit(code=1)
    except (ValidationError, NotBlockDeviceError) as e:
        # Should be rare here since core validates, but keep consistent behaviour
        typer.secho(f"❌ {e}", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=2)
    except SystemCommandError as e:
        typer.secho(str(e), fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)

def show_writeback_status(device_name: str):
    """
    Display writeback and compression stats suitable for GUI consumption.
    Now sources data via core.devices.get_writeback_status.
    """
    wb = core_get_writeback_status(device_name)
    typer.echo(f"Device: {wb.device}")
    typer.echo(f"  backing_dev     : {wb.backing_dev}")
    typer.echo(f"  orig_data_size  : {wb.orig_data_size}")
    typer.echo(f"  compr_data_size : {wb.compr_data_size}")
    typer.echo(f"  mem_used_total  : {wb.mem_used_total}")
    typer.echo(f"  num_writeback   : {wb.num_writeback}")
    typer.echo(f"  writeback_failed: {wb.writeback_failed}")
