# z-manager/tests/integration/test_hibernation_readonly.py
"""
Read-only integration tests for core.hibernation.

These tests probe real system state but make no modifications.
Safe to run as unprivileged user. No mocking.
"""

from __future__ import annotations

import pytest

from core.hibernation import prober


pytestmark = pytest.mark.integration


class TestReadinessProbe:
    def test_check_hibernation_readiness(self):
        result = prober.check_hibernation_readiness()
        assert isinstance(result.ready, bool)
        assert isinstance(result.message, str)
        assert result.secure_boot in (
            "disabled",
            "integrity",
            "confidentiality",
            "queried-via-logind",
        )
        assert result.ram_total >= 0
        assert result.swap_total >= 0

    def test_memory_info(self):
        ram, swap = prober.get_memory_info()
        assert ram > 0, "System should have RAM"
        assert swap >= 0


class TestSwapDetection:
    def test_detect_resume_swap_returns_path_or_none(self):
        swap = prober.detect_resume_swap()
        assert swap is None or isinstance(swap, str)

    def test_proc_swaps_readable(self):
        from core.utils.common import read_file

        content = read_file("/proc/swaps")
        assert content is not None
        assert "Filename" in content or content == ""


class TestSystemState:
    def test_power_state_readable(self):
        from core.utils.common import read_file

        state = read_file("/sys/power/state")
        assert state is not None
        assert isinstance(state, str)

    def test_proc_cmdline_readable(self):
        from core.utils.common import read_file

        cmdline = read_file("/proc/cmdline")
        assert cmdline is not None
        assert len(cmdline) > 0

    def test_kernel_lockdown_readable(self):
        from core.utils.common import read_file

        lockdown = read_file("/sys/kernel/security/lockdown")
        assert lockdown is None or isinstance(lockdown, str)
