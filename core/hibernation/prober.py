# z-manager/core/hibernation/prober.py
"""
The Safe Zone.
Handles device detection, state reading, and sysfs probing.
No destructive operations or system changes are performed here.
"""

from __future__ import annotations

from core.utils.common import run, SystemCommandError, read_file
from core.utils.block import is_block_device
from core.utils.swap import detect_resume_swap
from .types import HibernateCheckResult


def get_memory_info() -> tuple[int, int]:
    """Returns (ram_total, swap_total) in bytes from /proc/meminfo."""
    mem_total = 0
    swap_total = 0
    content = read_file("/proc/meminfo")
    if not content:
        return 0, 0
    for line in content.splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            if len(parts) >= 2:
                mem_total = int(parts[1]) * 1024
        elif line.startswith("SwapTotal:"):
            parts = line.split()
            if len(parts) >= 2:
                swap_total = int(parts[1]) * 1024
    return mem_total, swap_total


def check_hibernation_readiness() -> HibernateCheckResult:
    """
    Checks system readiness by delegating to systemd-logind with a fallback
    to sysfs parsing.
    """
    secure_boot_mode: str = "queried-via-logind"
    ready = False
    msg = ""

    try:
        res = run(
            [
                "busctl",
                "call",
                "org.freedesktop.login1",
                "/org/freedesktop/login1",
                "org.freedesktop.login1.Manager",
                "CanHibernate",
            ],
            check=True,
        )
        out = res.out.lower()
        if '"yes"' in out:
            ready, msg = True, "System is fully ready for hibernation."
        elif '"challenge"' in out:
            ready, msg = True, "Hibernation available (requires authentication)."
        else:
            raise ValueError(
                f"Logind returned {out.strip()}, triggering manual hardware check."
            )

    except (SystemCommandError, ValueError):
        power_state = read_file("/sys/power/state") or ""
        if "disk" not in power_state:
            ready, msg = (
                False,
                "Hardware/Kernel does not support hibernation ('disk' missing from /sys/power/state).",
            )
            secure_boot_mode = "disabled"
        else:
            ready, msg = (
                True,
                "Hardware supports hibernation (Swap configuration required).",
            )
            secure_boot_mode = "disabled"
            lockdown = read_file("/sys/kernel/security/lockdown") or ""
            if "[integrity]" in lockdown:
                secure_boot_mode = "integrity"
            elif "[confidentiality]" in lockdown:
                secure_boot_mode = "confidentiality"
                ready, msg = (
                    False,
                    "Secure Boot confidentiality is active. Hibernation is blocked.",
                )

    mem_total, swap_total = get_memory_info()
    return HibernateCheckResult(
        ready=ready,
        secure_boot=secure_boot_mode,  # type: ignore[arg-type]
        swap_total=swap_total,
        ram_total=mem_total,
        message=msg,
    )


def _get_fs_type(path: str) -> str | None:
    """Detect filesystem type of the directory containing the path."""
    directory = path.rsplit("/", 1)[0] or "/"
    try:
        res = run(["df", "-T", directory], check=False)
        if res.code == 0:
            lines = res.out.strip().splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 2:
                    return parts[1]
    except Exception:
        pass
    return None


def get_resume_offset(path: str) -> int | None:
    """
    Calculate the physical offset of the swapfile for the kernel resume parameter.
    Uses filesystem-specific tools for high-fidelity offset discovery.
    """
    if is_block_device(path):
        return 0

    match _get_fs_type(path):
        case "btrfs":
            try:
                res = run(
                    ["btrfs", "inspect-internal", "map-swapfile", "-r", path],
                    check=True,
                )
                return int(res.out.strip())
            except (ValueError, SystemCommandError):
                pass
        case _:
            try:
                res = run(["filefrag", "-v", path], check=True)
                for line in res.out.splitlines():
                    if line.strip().startswith("0:"):
                        parts = line.split()
                        if len(parts) >= 4:
                            return int(parts[3].split("..")[0])
            except (ValueError, SystemCommandError, IndexError):
                pass
    return None


def get_partition_uuid(path: str) -> str | None:
    """Get UUID of a partition or the device holding a file."""
    target_dev = path
    if not is_block_device(path):
        try:
            res = run(["df", "--output=source", path], check=False)
            if res.code == 0:
                lines = res.out.strip().splitlines()
                if len(lines) >= 2:
                    target_dev = lines[1]
        except Exception:
            return None

    try:
        res = run(["blkid", "-s", "UUID", "-o", "value", target_dev], check=False)
        if res.code == 0:
            return res.out.strip()
    except Exception:
        pass
    return None
