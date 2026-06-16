# zman/modules/journal.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from core.utils.common import run


@dataclass(frozen=True)
class JournalRecord:
    timestamp: datetime
    priority: int
    message: str
    fields: Dict[str, Any]


def python_journal_available() -> bool:
    """
    Returns True if python3-systemd journal module is importable.
    """
    try:
        import systemd.journal  # type: ignore
        return True
    except ImportError:
        return False


def _format_ts_safe(value: Any) -> datetime:
    try:
        match value:
            case datetime() as dt:
                pass
            case int() | float() as ts:
                dt = datetime.fromtimestamp(ts)
            case str() as s:
                try:
                    dt = datetime.fromisoformat(s)
                except ValueError:
                    dt = datetime.now().astimezone()
            case _:
                dt = datetime.now().astimezone()

        # Ensure timezone awareness
        return dt.astimezone() if dt.tzinfo is None else dt

    except Exception:
        return datetime.now().astimezone()


def list_zram_logs(
    unit: str = "systemd-zram-setup@zram0.service", count: int = 25
) -> List[JournalRecord]:
    """
    Return latest ZRAM-related logs as normalized records.
    Prefers python3-systemd if available; otherwise falls back to `journalctl`.
    """
    try:
        import systemd.journal  # type: ignore

        reader = systemd.journal.Reader()
        reader.add_match(_SYSTEMD_UNIT=unit)
        reader.seek_tail()
        buf: List[JournalRecord] = []
        i = 0
        while i < count and (entry := reader.get_previous()):
            i += 1
            ts = entry.get("__REALTIME_TIMESTAMP", datetime.now().astimezone())
            msg = entry.get("MESSAGE", "No message found.")
            prio = entry.get("PRIORITY", 6)
            rec = JournalRecord(
                timestamp=_format_ts_safe(ts),
                priority=int(prio)
                if isinstance(prio, (int, str)) and str(prio).isdigit()
                else 6,
                message=str(msg),
                fields={k: v for k, v in entry.items() if isinstance(k, str)},
            )
            buf.append(rec)
        buf.reverse()
        return buf
    except (ImportError, Exception):
        from core.utils.privilege import pkexec_read_journal
        
        cmd = [
            "journalctl",
            "--system",
            "-u",
            unit,
            "-n",
            str(count),
            "--no-pager",
            "--output=short-iso",
        ]
        jr = run(cmd, check=False)
        
        # If journalctl fails, try with pkexec
        out_text = jr.out
        if jr.code != 0:
            success, pkexec_out = pkexec_read_journal(unit, count)
            if success and pkexec_out:
                out_text = pkexec_out
            else:
                # If both fail, return empty or error message
                out_text = pkexec_out or jr.err or ""

        lines = [ln for ln in out_text.splitlines() if ln.strip()]
        records: List[JournalRecord] = []
        for ln in lines:
            ts: datetime = datetime.now().astimezone()
            msg = ln
            prio = 6
            try:
                first_space = ln.find(" ")
                if first_space > 0:
                    ts_str = ln[:first_space]
                    ts = _parse_iso_best_effort(ts_str) or datetime.now().astimezone()
                    msg = ln[first_space + 1 :].strip()
            except Exception:
                pass
            records.append(
                JournalRecord(
                    timestamp=ts,
                    priority=prio,
                    message=msg,
                    fields={"source": "journalctl"},
                )
            )
        return records


def _parse_iso_best_effort(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        try:
            if "+" in s:
                base = s.split("+", 1)[0]
                return datetime.fromisoformat(base)
        except Exception:
            pass
    return None


def systemd_journal_available_flag() -> Tuple[bool, Optional[str]]:
    """
    Returns (available, reason) for python3-systemd availability.
    """
    ok = python_journal_available()
    return ok, None if ok else "python3-systemd not importable"
