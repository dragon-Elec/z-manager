from unittest.mock import patch, MagicMock
from pathlib import Path
import os
import shutil
from tests.test_base import *
from core import boot_config


class TestSystemDetection(BaseTestCase):

    @patch('shutil.which')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_detect_bootloader_grub(self, mock_isdir, mock_exists, mock_which):
        # Mocking update-grub found
        mock_which.side_effect = lambda x: "/usr/sbin/update-grub" if x == "update-grub" else None
        mock_exists.return_value = False
        mock_isdir.return_value = False
        self.assertEqual(boot_config.detect_bootloader(), "grub")

    @patch('shutil.which')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_detect_bootloader_systemd_boot(self, mock_isdir, mock_exists, mock_which):
        # Mocking bootctl found
        mock_which.side_effect = lambda x: "/usr/bin/bootctl" if x == "bootctl" else None
        mock_exists.return_value = False
        mock_isdir.side_effect = lambda x: x == "/boot/efi/loader"
        self.assertEqual(boot_config.detect_bootloader(), "systemd-boot")

    @patch('shutil.which')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_detect_initramfs_initramfs_tools(self, mock_isdir, mock_exists, mock_which):
        mock_which.side_effect = lambda x: "/usr/sbin/update-initramfs" if x == "update-initramfs" else None
        mock_exists.return_value = False
        mock_isdir.return_value = False
        self.assertEqual(boot_config.detect_initramfs_system(), "initramfs-tools")

    @patch('shutil.which')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_detect_initramfs_dracut(self, mock_isdir, mock_exists, mock_which):
        mock_which.side_effect = lambda x: "/usr/bin/dracut" if x == "dracut" else None
        mock_exists.return_value = False
        mock_isdir.return_value = False
        self.assertEqual(boot_config.detect_initramfs_system(), "dracut")


class TestSysctlTuning(BaseTestCase):

    @patch('core.boot_config.read_file')
    @patch('core.boot_config.atomic_write_to_file')
    @patch('core.boot_config.run')
    @patch('pathlib.Path.exists')
    def test_apply_sysctl_values_success(self, mock_exists, mock_run, mock_write, mock_read):
        # We need to patch the nested imports inside the function
        with patch('core.utils.io.pkexec_write', return_value=(True, None)) as m_write, \
             patch('core.utils.privilege.pkexec_sysctl_system', return_value=(True, None)) as m_sysctl:

            mock_read.return_value = "vm.swappiness = 60\n# comment\nvm.page-cluster = 3"
            mock_write.return_value = (True, None)
            mock_exists.return_value = True

            settings = {"vm.swappiness": "100", "vm.vfs_cache_pressure": "50"}
            result = boot_config.apply_sysctl_values(settings)

            self.assertTrue(result.success)
            self.assertTrue(result.changed)
            self.assertTrue(m_write.called)

    def test_apply_sysctl_values_permission_denied(self):
        """Verify graceful handling when user cancels pkexec dialog."""
        with patch('core.boot_config.read_file', return_value="vm.swappiness=60"), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('core.boot_config.atomic_write_to_file') as mock_write, \
             patch('core.utils.io.pkexec_write', return_value=(False, "Permission denied")), \
             patch('core.utils.privilege.pkexec_sysctl_system', return_value=(True, None)):

            settings = {"vm.swappiness": "100"}
            result = boot_config.apply_sysctl_values(settings)

            self.assertFalse(result.success)
            self.assertIn("Permission denied", result.message)
            self.assertFalse(result.changed)
            # atomic_write_to_file is NOT called because pkexec failed
            self.assertFalse(mock_write.called)

    @patch('core.boot_config.read_file')
    @patch('pathlib.Path.exists')
    def test_apply_sysctl_values_no_change(self, mock_exists, mock_read):
        mock_read.return_value = "# Custom Z-Manager Tuning Configuration\nvm.swappiness = 100\n"
        mock_exists.return_value = True
        
        settings = {"vm.swappiness": "100"}
        result = boot_config.apply_sysctl_values(settings)
        
        self.assertTrue(result.success)
        self.assertFalse(result.changed)


if __name__ == '__main__':
    unittest.main()
