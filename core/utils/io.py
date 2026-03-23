# zman/core/utils/io.py
"""
Filesystem and privileged writing utilities.
"""
from __future__ import annotations
import os
import shutil
import tempfile
import subprocess
from pathlib import Path

def is_root() -> bool:
    """Check if process has root privileges."""
    return os.geteuid() == 0

def atomic_write_to_file(file_path: str | Path, content: str, backup: bool = False) -> tuple[bool, str | None]:
    """Safely writes content to a file using atomic move."""
    path = Path(file_path)
    try:
        if path.exists():
            try:
                if path.read_text(encoding="utf-8") == content:
                    return True, None
            except Exception:
                pass
            if backup:
                shutil.copy2(path, path.with_suffix(f"{path.suffix}.bak"))

        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=path.parent, text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        shutil.move(temp_path, path)
        path.chmod(0o644)
        return True, None
    except Exception as e:
        return False, f"Z-Manager System Error: {e}"

def sysfs_write(path: str | Path, value: str) -> None:
    """Directly writes to a sysfs node."""
    Path(path).write_text(value, encoding="utf-8")

def _get_helper_path() -> str:
    """Path to zman-helper script."""
    return str(Path(__file__).parent.parent / "zman_helper.py")

def pkexec_write(file_path: str | Path, content: str) -> tuple[bool, str | None]:
    """Write to a protected file via pkexec."""
    if is_root():
        return atomic_write_to_file(file_path, content, backup=True)
    
    try:
        proc = subprocess.run(
            ["pkexec", _get_helper_path(), "write", str(file_path)],
            input=content,
            text=True,
            capture_output=True
        )
        if proc.returncode == 0:
            return True, None
        return False, proc.stderr.strip() or f"pkexec write failed (code {proc.returncode})"
    except Exception as e:
        return False, f"Z-Manager System Error: {e}"
