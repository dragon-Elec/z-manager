from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, List


# ============ Domain Errors ============

class SystemCommandError(RuntimeError):
    def __init__(self, cmd: List[str], returncode: int, stdout: str, stderr: str):
        super().__init__(f"Command failed: {' '.join(cmd)} (code {returncode})\n{stderr.strip()}")
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class ValidationError(ValueError):
    pass


class NotBlockDeviceError(ValidationError):
    pass


# ============ Low-level helpers ============

@dataclass(frozen=True)
class CmdResult:
    code: int
    out: str
    err: str


def run(cmd: List[str], check: bool = False, env: Optional[Dict[str, str]] = None) -> CmdResult:
    """
    Run a command and capture stdout/stderr. Optionally raise on failure.
    """
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    res = CmdResult(code=proc.returncode, out=proc.stdout, err=proc.stderr)
    if check and proc.returncode != 0:
        raise SystemCommandError(cmd, proc.returncode, proc.stdout, proc.stderr)
    return res


def is_block_device(path: str) -> bool:
    """
    Determine if a given path refers to a block device (by stat).
    """
    try:
        st = os.stat(path)
        # S_IFBLK 0o060000
        return (st.st_mode & 0o170000) == 0o060000
    except FileNotFoundError:
        return False
    except Exception:
        return False


# ============ Sysfs helpers ============

def sysfs_read(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
    except Exception:
        return None


def sysfs_write(path: str, value: str) -> Tuple[bool, Optional[str]]:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(value)
        return True, None
    except Exception as e:
        return False, str(e)


def zram_sysfs_dir(device_name: str) -> str:
    # device_name e.g. "zram0"
    return f"/sys/block/{device_name}"


# ============ zramctl wrappers ============

def zramctl_reset(device_path: str) -> None:
    run(["zramctl", "--reset", device_path], check=True)


def zramctl_create(device_path: str, size: str, algorithm: Optional[str] = None,
                   streams: Optional[int] = None, writeback_device: Optional[str] = None) -> None:
    """
    Create/configure a zram device. zramctl requires size on first setup.
    """
    cmd: List[str] = ["zramctl", device_path, "--size", size]
    if algorithm:
        cmd += ["--algorithm", algorithm]
    if streams:
        cmd += ["--streams", str(streams)]
    if writeback_device:
        cmd += ["--writeback-device", writeback_device]
    run(cmd, check=True)


def zramctl_info_all() -> str:
    """
    Returns text output of `zramctl`.
    """
    return run(["zramctl"], check=False).out


def zramctl_info_json() -> Optional[str]:
    """
    Returns JSON (if supported by zramctl - not always available).
    """
    res = run(["zramctl", "--output-all", "--json"], check=False)
    if res.code == 0:
        return res.out
    return None


# ============ systemd wrappers ============

def systemd_daemon_reload() -> None:
    run(["systemctl", "daemon-reload"], check=True)


def systemd_restart(service: str) -> None:
    run(["systemctl", "restart", service], check=True)


def systemd_try_restart(service: str) -> Tuple[bool, Optional[str]]:
    r = run(["systemctl", "restart", service], check=False)
    if r.code == 0:
        return True, None
    return False, r.err.strip() or r.out.strip() or f"restart {service} failed"


# ============ discovery helpers ============

def parse_zramctl_table() -> List[Dict[str, Any]]:
    """
    Parse `zramctl` default table output to extract basic fields for devices.
    Falls back to naive parsing; for richer data prefer sysfs reads.
    """
    out = zramctl_info_all()
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if not lines:
        return []

    header = lines[0]
    # Heuristic columns; zramctl formats can vary.
    # We'll scan for device paths like /dev/zramN and then split remaining columns.
    devices: List[Dict[str, Any]] = []
    for ln in lines[1:]:
        if "/dev/zram" not in ln:
            continue
        parts = ln.split()
        # Common format: NAME DISKSIZE DATA COMPR TOTAL STREAMS ALG ...
        # NAME is /dev/zramN
        name = parts[0]
        info: Dict[str, Any] = {"name": os.path.basename(name)}
        # Best-effort mapping
        if len(parts) >= 2:
            info["disksize"] = parts[1]
        if len(parts) >= 3:
            info["data-size"] = parts[2]
        if len(parts) >= 4:
            info["compr-size"] = parts[3]
        if len(parts) >= 6:
            # streams often at index 5
            try:
                info["streams"] = int(parts[5])
            except Exception:
                info["streams"] = parts[5]
        if len(parts) >= 7:
            info["algorithm"] = parts[6]
        # ratio is not always present in table; compute elsewhere if needed
        devices.append(info)
    return devices
