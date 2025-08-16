# zman/commands/check.py
import typer
from ..utils import run_command, is_command_available, get_swappiness
from ..core.health import check_system_health

def run_check():
    """
    Runs a health check on the ZRAM configuration.
    """
    typer.echo("--- Z-Manager Health Check ---")

    # Use core.health to gather the system health state
    report = check_system_health()

    # 1) Tooling availability
    typer.echo("\n[1] Checking for ZRAM Tools...")
    if not report.zramctl_available:
        typer.secho(
            "Error: 'zramctl' command not found. Is 'zram-tools' installed?",
            fg=typer.colors.RED,
            bold=True
        )
        raise typer.Exit(code=1)
    typer.secho("✅ 'zramctl' is available.", fg=typer.colors.GREEN)

    # 2) Device summary (from zramctl)
    typer.echo("\n[2] Checking ZRAM Device Status...")
    stdout, stderr, returncode = run_command("zramctl")
    if returncode == 0:
        if stdout.strip():
            typer.secho("✅ ZRAM is active and configured.", fg=typer.colors.GREEN)
            typer.echo(stdout)
        else:
            typer.secho("🟡 ZRAM module is loaded, but no devices are configured.", fg=typer.colors.YELLOW)
    else:
        err_text = (stderr or "").strip() or (stdout or "").strip() or "Unknown error querying zramctl"
        typer.secho(f"❌ Failed to get ZRAM status. Error:\n{err_text}", fg=typer.colors.RED)

    # 3) ZSwap status from core.health
    typer.echo("\n[3] Checking for ZSwap Conflict...")
    if report.zswap.available and report.zswap.enabled:
        typer.secho(
            "⚠️  Warning: zswap is enabled. This can conflict with zram.",
            fg=typer.colors.YELLOW,
            bold=True
        )
        typer.echo("   It's recommended to disable zswap for optimal zram performance.")
    else:
        typer.secho("✅ zswap is not enabled or not loaded.", fg=typer.colors.GREEN)

    # 4) Swappiness value (keep existing util)
    typer.echo("\n[4] Checking System Swappiness...")
    swappiness = get_swappiness()
    if swappiness is not None:
        if swappiness >= 180:
            typer.secho(
                f"✅ Current swappiness is {swappiness}. This is an optimal value for ZRAM.",
                fg=typer.colors.GREEN
            )
        elif swappiness >= 100:
            typer.secho(
                f"✅ Current swappiness is {swappiness}. This is a good, aggressive value for ZRAM.",
                fg=typer.colors.GREEN
            )
        else:
            typer.secho(
                f"ℹ️  Current swappiness is {swappiness}. This is a low value.",
                fg=typer.colors.BLUE
            )
            typer.echo("   For best ZRAM performance, a higher value (e.g., 180) is recommended.")
            typer.echo("   You can apply this with 'z-manager tune --profile'.")
    else:
        typer.secho("❌ Could not read system swappiness.", fg=typer.colors.RED)

    # Extra notes from health report (non-fatal info)
    if report.notes:
        typer.echo("\n[Notes]")
        for note in report.notes:
            typer.echo(f"- {note}")

    typer.echo("\n--- Check Complete ---")
