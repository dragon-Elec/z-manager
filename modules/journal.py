from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from .system import run


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
    r = run(["/bin/sh", "-lc", "python3 -c 'import systemd.journal'"], check=False)
    return r.code == 0


def _format_ts_safe(value: Any) -> datetime:
    try:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except Exception:
                return datetime.now()
    except Exception:
        pass
    return datetime.now()


def list_zram_logs(unit: str = "systemd-zram-setup@zram0.service", count: int = 25) -> List[JournalRecord]:
    """
    Return latest ZRAM-related logs as normalized records.
    Prefers python3-systemd if available; otherwise falls back to `journalctl`.
    """
    if python_journal_available():
        try:
            import systemd.journal  # type: ignore
            reader = systemd.journal.Reader()
            reader.add_match(_SYSTEMD_UNIT=unit)
            reader.seek_tail()
            buf: List[JournalRecord] = []
            for entry in reader:
                ts = entry.get("__REALTIME_TIMESTAMP", datetime.now())
                msg = entry.get("MESSAGE", "No message found.")
                prio = entry.get("PRIORITY", 6)
                rec = JournalRecord(
                    timestamp=_format_ts_safe(ts),
                    priority=int(prio) if isinstance(prio, (int, str)) and str(prio).isdigit() else 6,
                    message=str(msg),
                    fields={k: v for k, v in entry.items() if isinstance(k, str)},
                )
                buf.append(rec)
                if len(buf) >= count:
                    break
            return buf
        except Exception:
            # Fall through to journalctl fallback
            pass

    jr = run(
        [
            "/bin/sh",
            "-lc",
            f"journalctl -u {unit} -n {count} --no-pager --output=short-iso 2>/dev/null || true",
        ],
        check=False,
    )
    lines = [ln for ln in jr.out.splitlines() if ln.strip()]
    records: List[JournalRecord] = []
    for ln in lines:
        ts: datetime = datetime.now()
        msg = ln
        prio = 6
        try:
            first_space = ln.find(" ")
            if first_space > 0:
                ts_str = ln[:first_space]
                ts = _parse_iso_best_effort(ts_str) or datetime.now()
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


# Compatibility shim for legacy utils.get_zram_logs_from_api callers
def get_zram_logs_from_api(unit: str = "systemd-zram-setup@zram0.service", count: int = 25) -> List[Dict[str, Any]]:
    """
    Return logs as a list of dicts compatible with previous utils API.
    """
    recs = list_zram_logs(unit=unit, count=count)
    out: List[Dict[str, Any]] = []
    for r in recs:
        out.append(
            {
                "timestamp": r.timestamp,
                "priority": r.priority,
                "message": r.message,
                **r.fields,
            }
        )
    return out


def systemd_journal_available_flag() -> Tuple[bool, Optional[str]]:
    """
    Returns (available, reason) for python3-systemd availability.
    """
    ok = python_journal_available()
    return ok, None if ok else "python3-systemd not importable"