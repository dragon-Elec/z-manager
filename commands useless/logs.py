# zman/commands/logs.py
import typer
from datetime import datetime
from ..core.journal import list_zram_logs

def _format_timestamp(ts: datetime) -> str:
    try:
        return ts.strftime('%b %d %H:%M:%S')
    except Exception:
        return datetime.now().strftime('%b %d %H:%M:%S')

def run_logs(count: int):
    """
    Fetches and displays the latest zram-generator logs from the systemd journal.
    """
    typer.secho(f"--- Fetching Last {count} ZRAM Log Entries ---", bold=True)

    # Fetch normalized records from core.journal (handles python3-systemd or journalctl fallback)
    records = list_zram_logs(count=count)

    if not records:
        typer.secho("No ZRAM-related logs found in the systemd journal.", fg=typer.colors.YELLOW)
        return

    for rec in records:
        # Systemd journal priority: 0-3 (errors), 4 (warnings), 5+ (info)
        priority = getattr(rec, "priority", 6) or 6
        if priority <= 3:
            color = typer.colors.RED
        elif priority == 4:
            color = typer.colors.YELLOW
        else:
            color = None

        timestamp = _format_timestamp(rec.timestamp)
        message = rec.message or 'No message content.'

        typer.secho(f"[{timestamp}] ", fg=typer.colors.CYAN, nl=False)
        typer.secho(message, fg=color)

    typer.echo("\n--- End of Logs ---")
