from tests.test_base import *
import unittest
from unittest.mock import patch, MagicMock

from core.utils.bootloader import detect_bootloader, detect_initramfs_system
from core.utils.kernel_cmdline import is_kernel_param_active
from core.hibernation.configurator import (
    update_grub_resume,
    configure_initramfs_resume,
)


class TestSystemDetection(BaseTestCase):
    @patch("core.utils.bootloader.shutil.which")
    @patch("core.utils.bootloader.os.path.exists")
    @patch("core.utils.bootloader.os.path.isdir")
    def test_detect_bootloader_grub(self, mock_isdir, mock_exists, mock_which):
        mock_which.side_effect = lambda x: (
            "/usr/sbin/update-grub" if x == "update-grub" else None
        )
        mock_exists.return_value = False
        mock_isdir.return_value = False
        self.assertEqual(detect_bootloader(), "grub")

    @patch("core.utils.bootloader.shutil.which")
    @patch("core.utils.bootloader.os.path.exists")
    @patch("core.utils.bootloader.os.path.isdir")
    def test_detect_bootloader_systemd_boot(self, mock_isdir, mock_exists, mock_which):
        mock_which.side_effect = lambda x: (
            "/usr/bin/bootctl" if x == "bootctl" else None
        )
        mock_exists.return_value = False
        mock_isdir.return_value = False
        self.assertEqual(detect_bootloader(), "systemd-boot")

    @patch("core.utils.bootloader.shutil.which")
    @patch("core.utils.bootloader.os.path.exists")
    @patch("core.utils.bootloader.os.path.isdir")
    def test_detect_initramfs_initramfs_tools(
        self, mock_isdir, mock_exists, mock_which
    ):
        mock_which.side_effect = lambda x: (
            "/usr/sbin/update-initramfs" if x == "update-initramfs" else None
        )
        mock_exists.return_value = False
        mock_isdir.return_value = False
        self.assertEqual(detect_initramfs_system(), "initramfs-tools")

    @patch("core.utils.bootloader.shutil.which")
    @patch("core.utils.bootloader.os.path.exists")
    @patch("core.utils.bootloader.os.path.isdir")
    def test_detect_initramfs_dracut(self, mock_isdir, mock_exists, mock_which):
        mock_which.side_effect = lambda x: "/usr/bin/dracut" if x == "dracut" else None
        mock_exists.return_value = False
        mock_isdir.return_value = False
        self.assertEqual(detect_initramfs_system(), "dracut")


class TestResumeConfig(BaseTestCase):
    @patch("core.hibernation.configurator.pkexec_write")
    @patch("core.utils.bootloader.detect_bootloader")
    def test_update_grub_resume_success(self, mock_detect, mock_write):
        mock_detect.return_value = "grub"
        mock_write.return_value = (True, None)

        ok, msg = update_grub_resume("abc-123", offset=34816)
        self.assertTrue(ok)
        self.assertIn("written", msg.lower())

    @patch("core.utils.bootloader.detect_bootloader")
    def test_update_grub_resume_no_grub(self, mock_detect):
        mock_detect.return_value = "systemd-boot"

        ok, msg = update_grub_resume("abc-123", offset=34816)
        self.assertFalse(ok)
        self.assertIn("GRUB", msg)

    @patch("core.hibernation.configurator.pkexec_write")
    @patch("core.hibernation.configurator.detect_initramfs_system")
    def test_configure_initramfs_resume_success(self, mock_detect, mock_write):
        mock_detect.return_value = "initramfs-tools"
        mock_write.return_value = (True, None)

        ok, msg = configure_initramfs_resume("abc-123", offset=34816)
        self.assertTrue(ok)
        self.assertIn("updated", msg.lower())

    @patch("core.hibernation.configurator.detect_initramfs_system")
    def test_configure_initramfs_resume_unsupported(self, mock_detect):
        mock_detect.return_value = "dracut"

        ok, msg = configure_initramfs_resume("abc-123", offset=34816)
        self.assertTrue(ok)
        self.assertIn("not implemented", msg)


class TestKernelParam(BaseTestCase):
    @patch("core.utils.kernel_cmdline.read_file")
    def test_is_kernel_param_active_present(self, mock_read):
        mock_read.return_value = "quiet resume=UUID=abc-123 resume_offset=34816 splash"
        self.assertTrue(is_kernel_param_active("resume="))

    @patch("core.utils.kernel_cmdline.read_file")
    def test_is_kernel_param_active_missing(self, mock_read):
        mock_read.return_value = "quiet splash"
        self.assertFalse(is_kernel_param_active("resume="))

    @patch("core.utils.kernel_cmdline.read_file")
    def test_is_kernel_param_active_empty_cmdline(self, mock_read):
        mock_read.return_value = ""
        self.assertFalse(is_kernel_param_active("resume="))


if __name__ == "__main__":
    unittest.main()
