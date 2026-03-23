from tests.test_base import *
import sys
import os
from unittest.mock import patch, MagicMock

from core import hibernate_ctl
from core.os_utils import SystemCommandError

class TestHibernateCtl(BaseTestCase):

    @patch('core.hibernate_ctl.run')
    @patch('core.hibernate_ctl.get_memory_info')
    def test_check_readiness_busctl(self, mock_mem, mock_run):
        """Test systemd-logind delegation via busctl."""
        # 1. Happy Path: logind says "yes"
        mock_mem.return_value = (8*1024*1024*1024, 4*1024*1024*1024)
        mock_run.return_value = MagicMock(out='s "yes"', code=0)
        
        res = hibernate_ctl.check_hibernation_readiness()
        self.assertTrue(res.ready)
        self.assertIn("ready", res.message)

        # 2. Blocked: logind says "no" (e.g. Secure Boot)
        mock_run.return_value = MagicMock(out='s "no"', code=0)
        res = hibernate_ctl.check_hibernation_readiness()
        self.assertFalse(res.ready)
        self.assertIn("disabled", res.message)

        # 3. Not Supported: logind says "na"
        mock_run.return_value = MagicMock(out='s "na"', code=0)
        res = hibernate_ctl.check_hibernation_readiness()
        self.assertFalse(res.ready)
        self.assertIn("not supported", res.message)

    @patch('core.hibernate_ctl._get_fs_type')
    @patch('core.hibernate_ctl.run')
    def test_get_resume_offset_logic(self, mock_run, mock_fs):
        """Verify filesystem-specific offset calculation logic."""
        # 1. Btrfs
        mock_fs.return_value = "btrfs"
        mock_run.return_value = MagicMock(out="12345\n", code=0)
        offset = hibernate_ctl.get_resume_offset("/swapfile")
        self.assertEqual(offset, 12345)
        self.assertIn("inspect-internal", mock_run.call_args[0][0])

        # 2. Ext4
        mock_fs.return_value = "ext4"
        mock_run.return_value = MagicMock(out="""Filesystem type is: ef53
File size of /swapfile is 4294967296 (1048576 blocks, blocksize 4096)
 ext:     logical_offset:        physical_offset: length:   expected: flags:
   0:        0..       0:      34816..     34816:      1:
""", code=0)
        offset = hibernate_ctl.get_resume_offset("/swapfile")
        self.assertEqual(offset, 34816)
        self.assertIn("filefrag", mock_run.call_args[0][0])

    @patch('core.hibernate_ctl.get_resume_offset')
    @patch('core.hibernate_ctl.get_partition_uuid')
    @patch('os.chmod')
    @patch('core.hibernate_ctl.run')
    @patch('core.hibernate_ctl._get_fs_type')
    @patch('os.path.exists')
    def test_create_swapfile_ext4(self, mock_exists, mock_fs, mock_run, mock_chmod, mock_uuid, mock_offset):
        """Test swapfile creation on Ext4."""
        mock_exists.return_value = False 
        mock_fs.return_value = "ext4"
        mock_uuid.return_value = "uuid-123"
        mock_offset.return_value = 12345
        mock_run.return_value.code = 0
        
        res = hibernate_ctl.create_swapfile("/swapfile", 1024)
        self.assertTrue(res.success)
        
        calls = [c[0][0] for c in mock_run.call_args_list]
        self.assertTrue(any("fallocate" in str(cmd) for cmd in calls))
        self.assertFalse(any("truncate" in str(cmd) for cmd in calls))

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
        self.assertTrue(res.success)
        
        calls = [str(c[0][0]) for c in mock_run.call_args_list]
        self.assertTrue(any('truncate' in cmd for cmd in calls))
        self.assertTrue(any('chattr' in cmd for cmd in calls))

if __name__ == '__main__':
    unittest.main()
