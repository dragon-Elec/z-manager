# zman/commands/configure.py
import typer
import click
# --- MODIFIED IMPORTS ---
from ..core.config import generate_config_string, CONFIG_PATH
from ..utils import is_root, run_command, atomic_write_to_file
from ..core.system import SystemCommandError

def validate_priority(value: int):
    MIN_PRIO, MAX_PRIO = -1, 32767
    if not (MIN_PRIO <= value <= MAX_PRIO):
        raise typer.BadParameter(f"Priority must be between {MIN_PRIO} and {MAX_PRIO}.")
    return value

def run_configure():
    """
    Interactively creates and applies a new ZRAM configuration.
    """
    typer.echo("--- Z-Manager Interactive Configuration ---")
    typer.echo("This will guide you through creating a new zram-generator.conf.")

    # --- This section is unchanged ---
    typer.secho("\n[1] ZRAM Size", bold=True)
    # --- REPLACE THE PROMPT AND SIZE_MAP ---
    size_map = {
        "1": "min(ram / 2, 8192)",    # Recommended: 50% of RAM, capped at 8GB
        "2": "min(ram, 16384)",      # Aggressive: 100% of RAM, capped at 16GB
        "3": "ram"                  # Power User: 100% of RAM, no cap
    }
    size_choice = typer.prompt(
        text=(
            "  [1] Recommended: 50% of RAM (max 8GB)\n"
            "  [2] Aggressive: 100% of RAM (max 16GB)\n"
            "  [3] Power User: 100% of RAM (uncapped)\n"
            "Choose a size profile"
        ),
        type=click.Choice(["1", "2", "3"]), default="1", show_choices=False
    )
    zram_size_formula = size_map[size_choice]

    typer.secho("\n[2] Compression Algorithm", bold=True)
    algo_choice = typer.prompt(
        text=("  [1] zstd (Modern, fast, efficient)\n  [2] lzo-rle (Classic, very fast)\nChoose an option"),
        type=click.Choice(["1", "2"]), default="1", show_choices=False
    )
    algorithm = "zstd" if algo_choice == "1" else "lzo-rle"

    typer.secho("\n[3] Swap Priority", bold=True)
    priority = typer.prompt("Enter swap priority", default=100, type=int)
    validate_priority(priority)
    
    device_name = "zram0"

    # --- Preview Section ---
    typer.secho("\n--- Generated Configuration Preview ---", bold=True)
    config_string = generate_config_string(
        size_formula=zram_size_formula,  # Pass the formula string
        algorithm=algorithm,
        priority=priority,
        device=device_name
    )
    typer.secho("=" * 40, fg=typer.colors.BLUE)
    typer.secho(config_string, fg=typer.colors.GREEN, bold=True)
    typer.secho("=" * 40, fg=typer.colors.BLUE)

    # --- Apply Section ---
    typer.secho("\n[4] Apply Configuration", bold=True)
    if not typer.confirm("Do you want to write this configuration to the system?"):
        typer.echo("Aborted. No changes were made.")
        raise typer.Abort()

    if not is_root():
        typer.secho("Error: Writing system files requires root privileges. Please run with 'sudo'.", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)

    typer.echo("Writing configuration file...")
    # --- MODIFIED: Calling the centralized utility function ---
    success, error = atomic_write_to_file(CONFIG_PATH, config_string + "\n")
    if not success:
        typer.secho(f"Failed to write config file! Error: {error}", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)
    typer.secho("✅ Configuration file written successfully.", fg=typer.colors.GREEN)

    # --- Apply systemd settings via core.config policy ---
    typer.echo("\nApplying settings via systemd (core.config)...")
    try:
        from ..core.config import apply_config_with_restart
        res = apply_config_with_restart(device=device_name, restart_mode="try")
        if res.success:
            if res.applied:
                typer.secho("✅ daemon-reload and restart succeeded.", fg=typer.colors.GREEN)
            else:
                typer.secho("✅ daemon-reload completed (no restart requested).", fg=typer.colors.GREEN)
        else:
            typer.secho(f"❌ Failed to apply configuration: {res.message}", fg=typer.colors.RED, bold=True)
            typer.echo("\nSystem may be in an inconsistent state. Please check system logs.")
            raise typer.Exit(code=1)
    except SystemCommandError as e:
        # Should not typically raise with restart_mode='try', but guard anyway
        typer.secho(f"❌ Error applying configuration: {e}", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)

    typer.secho("\n--- Configuration Applied! ---", bold=True)
    typer.echo("Run 'z-manager check' to see the new status.")
