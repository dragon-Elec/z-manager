# z-manager/tests/integration/test_hibernation_privileged.py
"""
Privileged integration tests for core.hibernation.

These tests require root and modify real system state:
- Creating/deleting swapfiles
- Writing to /etc/systemd/system/
- Writing to /etc/default/grub.d/
- Running update-grub / update-initramfs

Run with: pytest tests/integration/test_hibernation_privileged.py --privileged
Skipped by default (no root required).
"""

from __future__ import annotations

import os
import pytest

from core.hibernation import provisioner, prober


pytestmark = pytest.mark.privileged


class TestSwapLifecycle:
    """Real swapfile creation and teardown."""

    def test_create_and_remove_swapfile(self, tmp_swap_path):
        size_mb = 64

        res = provisioner.create_swapfile(tmp_swap_path, size_mb)
        assert res.success, res.message
        assert os.path.exists(tmp_swap_path)
        assert os.path.getsize(tmp_swap_path) >= (size_mb * 1024 * 1024) // 2

        enabled = provisioner.enable_swapon(tmp_swap_path, priority=0)
        assert enabled, "swapon failed"

        try:
            swaps = prober.detect_resume_swap()
            assert swaps == tmp_swap_path
        finally:
            ok = provisioner.swapoff_swap(tmp_swap_path)
            assert ok, "swapoff failed"

        teardown = provisioner.delete_swap(tmp_swap_path)
        assert teardown.success, teardown.message
        assert not os.path.exists(tmp_swap_path)

    def test_persist_swap_unit(self, tmp_swap_path):
        size_mb = 64
        provisioner.create_swapfile(tmp_swap_path, size_mb)
        provisioner.enable_swapon(tmp_swap_path)

        try:
            res = provisioner.persist_swap_unit(tmp_swap_path, priority=0)
            assert res.success, res.message
            assert res.unit_name.endswith(".swap")
            unit_path = f"/etc/systemd/system/{res.unit_name}"
            assert os.path.exists(unit_path), f"Unit not written: {unit_path}"

            unit_content = open(unit_path).read()
            assert f"What={tmp_swap_path}" in unit_content
            assert "Priority=0" in unit_content
            assert "nofail" in unit_content
        finally:
            provisioner.swapoff_swap(tmp_swap_path)
            provisioner.delete_swap(tmp_swap_path)


class TestGrubConfig:
    """Real GRUB configuration writes."""

    def test_grub_resume_config_written(self, is_root):
        from core.hibernation import configurator

        ok, msg = configurator.update_grub_resume("test-uuid-1234", offset=12345)
        assert ok, msg

        cfg_path = "/etc/default/grub.d/99-z-manager-resume.cfg"
        assert os.path.exists(cfg_path), f"Config not written: {cfg_path}"

        content = open(cfg_path).read()
        assert "resume=UUID=test-uuid-1234" in content
        assert "resume_offset=12345" in content


class TestSystemDetection:
    """Real system probing without mocking."""

    def test_detect_bootloader(self, is_root):
        from core.hibernation import configurator

        result = configurator.detect_bootloader()
        assert result in ("grub", "systemd-boot", "unknown")

    def test_detect_initramfs_system(self, is_root):
        from core.hibernation import configurator

        result = configurator.detect_initramfs_system()
        assert result in ("initramfs-tools", "dracut", "mkinitcpio", "unknown")

    def test_kernel_params_readable(self, is_root):
        from core.hibernation import configurator

        result = configurator.is_kernel_param_active("BOOT_IMAGE=")
        assert isinstance(result, bool)

    def test_memory_info_readable(self, is_root):
        ram, swap = prober.get_memory_info()
        assert ram > 0, "RAM should be detected"
        assert swap >= 0

    def test_resume_swap_detected(self, is_root):
        swap = prober.detect_resume_swap()
        assert swap is None or isinstance(swap, str)
