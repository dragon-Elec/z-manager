# zman/core/utils/common.py
"""
Base utility layer: execution and command handling.
"""
from __future__ import annotations

import subprocess
import logging
from dataclasses import dataclass
from typing import Iterator
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class CmdResult:
    code: int
    out: str
    err: str

class SystemCommandError(RuntimeError):
    def __init__(self, cmd: list[str], returncode: int, stdout: str, stderr: str):
        super().__init__(f"Command failed: {' '.join(cmd)} (code {returncode})\n{stderr.strip()}")
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

class ValidationError(ValueError):
    pass

class NotBlockDeviceError(ValidationError):
    pass

def run(cmd: list[str], check: bool = False, env: dict[str, str] | None = None) -> CmdResult:
    """Run a command and capture stdout/stderr."""
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    res = CmdResult(code=proc.returncode, out=proc.stdout, err=proc.stderr)
    if check and proc.returncode != 0:
        raise SystemCommandError(cmd, proc.returncode, proc.stdout, proc.stderr)
    return res

def read_file(path: str | Path) -> str | None:
    """Safely reads a sysfs or config file with broad exception handling."""
    p = Path(path)
    try:
        return p.read_text(encoding="utf-8").strip()
    except Exception:
        # Broad catch to match monolith's resilience against I/O or permission issues
        return None

def stream_command(cmd: list[str], env: dict[str, str] | None = None, input_text: str | None = None) -> Iterator[str]:
    """Run a command and yield its stdout line by line."""
    stdin_arg = subprocess.PIPE if input_text else None
    
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=stdin_arg,
        text=True,
        env=env,
        bufsize=1
    ) as proc:
        if input_text and proc.stdin:
            try:
                proc.stdin.write(input_text)
                proc.stdin.close()
            except BrokenPipeError:
                pass

        if proc.stdout:
            yield from (line.rstrip() for line in proc.stdout)

        if proc.wait() != 0:
            raise SystemCommandError(cmd, proc.returncode, "<Stream Output>", "<Stream Output>")
