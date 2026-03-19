
import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Adjust path so we can import core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core import hibernate_ctl
from core.os_utils import SystemCommandError

class TestHibernateCtl(unittest.TestCase):

    @patch('core.hibernate_ctl.read_file')
    @patch('core.hibernate_ctl.get_memory_info')
    def test_check_readiness_basic(self, mock_mem, mock_read):
        """Test basic readiness checks."""
        # 1. Happy Path
        mock_mem.return_value = (8*1024*1024*1024, 0) # 8GB RAM, 0 Swap
        mock_read.return_value = "none [integrity]" # Secure boot OK
        
        res = hibernate_ctl.check_hibernation_readiness()
        self.assertTrue(res.ready)
        self.assertEqual(res.secure_boot, "integrity")

        # 2. Secure Boot Blocked
        mock_read.return_value = "none [confidentiality]"
        res = hibernate_ctl.check_hibernation_readiness()
        self.assertFalse(res.ready)
        self.assertIn("confidentiality", res.message)

    @patch('core.hibernate_ctl.get_resume_offset')
    @patch('core.hibernate_ctl.get_partition_uuid')
    @patch('os.chmod')
    @patch('core.hibernate_ctl.run')
    @patch('core.hibernate_ctl._get_fs_type')
    @patch('os.path.exists')
    def test_create_swapfile_ext4(self, mock_exists, mock_fs, mock_run, mock_chmod, mock_uuid, mock_offset):
        """Test swapfile creation on Ext4."""
        mock_exists.return_value = False # New file
        mock_fs.return_value = "ext4"
        mock_uuid.return_value = "uuid-123"
        mock_offset.return_value = 12345
        
        # Mock run to succeed
        mock_run.return_value.code = 0
        
        res = hibernate_ctl.create_swapfile("/swapfile", 1024)
        
        # If failure, print message
        if not res.success:
            print(f"FAIL REASON: {res.message}")
            
        self.assertTrue(res.success)
        
        # Verify calls
        # Should call fallocate, chmod, mkswap. NOT truncate/chattr
        calls = [c[0][0] for c in mock_run.call_args_list]
        
        # Check that we called fallocate
        fallocate_called = any("fallocate" in cmd[0] for cmd in calls)
        self.assertTrue(fallocate_called, "Should use fallocate for Ext4")
        
        # Check NO btrfs commands
        btrfs_called = any("truncate" in cmd[0] for cmd in calls)
        self.assertFalse(btrfs_called, "Should NOT use truncate on Ext4")
        
        mock_chmod.assert_called_with("/swapfile", 0o600)

    @patch('core.hibernate_ctl.get_resume_offset')
    @patch('core.hibernate_ctl.get_partition_uuid')
    @patch('os.chmod')
    @patch('core.hibernate_ctl.run')
    @patch('core.hibernate_ctl._get_fs_type')
    @patch('os.path.exists')
    def test_create_swapfile_btrfs(self, mock_exists, mock_fs, mock_run, mock_chmod, mock_uuid, mock_offset):
        """Test swapfile creation on Btrfs."""
        mock_exists.return_value = False
        mock_fs.return_value = "btrfs"
        mock_run.return_value.code = 0
        mock_uuid.return_value = "uuid-123"
        mock_offset.return_value = 12345
        
        res = hibernate_ctl.create_swapfile("/swapfile", 1024)
        if not res.success:
            print(f"FAIL REASON: {res.message}")

        self.assertTrue(res.success)
        
        calls = [tuple(c[0][0]) for c in mock_run.call_args_list]
        
        # Should force truncate -s 0, chattr +C
        truncate_found = any('truncate' in cmd and '-s' in cmd for cmd in calls)
        chattr_found = any('chattr' in cmd and '+C' in cmd for cmd in calls)
        
        self.assertTrue(truncate_found, "Must truncate to 0 on Btrfs")
        self.assertTrue(chattr_found, "Must disable COW (+C) on Btrfs")

    @patch('core.hibernate_ctl.pkexec_write')
    @patch('core.hibernate_ctl.is_root')
    @patch('core.hibernate_ctl.read_file')
    def test_update_fstab(self, mock_read, mock_root, mock_pkexec):
        """Test fstab updates include 'nofail'."""
        mock_root.return_value = False # User mode, use pkexec
        mock_read.return_value = "# /etc/fstab\nUUID=123 / ext4 defaults 0 1\n"
        mock_pkexec.return_value = (True, "")
        
        success = hibernate_ctl.update_fstab("/swapfile", "uuid-555")
        self.assertTrue(success)
        
        # Verify content written
        args = mock_pkexec.call_args[0]
        path = args[0]
        content = args[1]
        
        self.assertEqual(path, "/etc/fstab")
        self.assertIn("UUID=uuid-555", content)
        self.assertIn("nofail", content)
        self.assertIn("pri=0", content)

if __name__ == '__main__':
    unittest.main()
