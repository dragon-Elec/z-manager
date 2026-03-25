from tests.test_base import *
import unittest
from unittest.mock import patch, MagicMock

from core.hibernation.prober import (
    check_hibernation_readiness,
    get_resume_offset,
    get_partition_uuid,
    get_memory_info,
    _get_fs_type,
)
from core.utils.swap import detect_resume_swap


class TestProber(BaseTestCase):
    @patch("core.hibernation.prober.read_file")
    @patch("core.hibernation.prober.run")
    @patch("core.hibernation.prober.get_memory_info")
    def test_check_readiness_busctl_yes(self, mock_mem, mock_run, mock_read):
        mock_mem.return_value = (8 * 1024 * 1024 * 1024, 4 * 1024 * 1024 * 1024)
        mock_run.return_value = MagicMock(out='s "yes"', code=0)

        res = check_hibernation_readiness()
        self.assertTrue(res.ready)
        self.assertIn("ready", res.message)

    @patch("core.hibernation.prober.read_file")
    @patch("core.hibernation.prober.run")
    @patch("core.hibernation.prober.get_memory_info")
    def test_check_readiness_busctl_no_fallback(self, mock_mem, mock_run, mock_read):
        mock_mem.return_value = (8 * 1024 * 1024 * 1024, 0)
        mock_run.return_value = MagicMock(out='s "no"', code=0)
        mock_read.return_value = "freeze mem"

        res = check_hibernation_readiness()
        self.assertFalse(res.ready)
        self.assertIn("not support", res.message)

    @patch("core.hibernation.prober.read_file")
    @patch("core.hibernation.prober.run")
    @patch("core.hibernation.prober.get_memory_info")
    def test_check_readiness_busctl_na_fallback_success(
        self, mock_mem, mock_run, mock_read
    ):
        mock_mem.return_value = (8 * 1024 * 1024 * 1024, 0)
        mock_run.return_value = MagicMock(out='s "na"', code=0)
        mock_read.return_value = "freeze mem disk"

        res = check_hibernation_readiness()
        self.assertTrue(res.ready)
        self.assertIn("Hardware supports hibernation", res.message)

    @patch("core.hibernation.prober._get_fs_type")
    @patch("core.hibernation.prober.run")
    def test_get_resume_offset_btrfs(self, mock_run, mock_fs):
        mock_fs.return_value = "btrfs"
        mock_run.return_value = MagicMock(out="12345\n", code=0)
        offset = get_resume_offset("/swapfile")
        self.assertEqual(offset, 12345)
        self.assertIn("inspect-internal", mock_run.call_args[0][0])

    @patch("core.hibernation.prober._get_fs_type")
    @patch("core.hibernation.prober.run")
    def test_get_resume_offset_ext4(self, mock_run, mock_fs):
        mock_fs.return_value = "ext4"
        mock_run.return_value = MagicMock(
            out="""Filesystem type is: ef53
File size of /swapfile is 4294967296 (1048576 blocks, blocksize 4096)
 ext:     logical_offset:        physical_offset: length:   expected: flags:
   0:        0..       0:      34816..     34816:      1:
""",
            code=0,
        )
        offset = get_resume_offset("/swapfile")
        self.assertEqual(offset, 34816)
        self.assertIn("filefrag", mock_run.call_args[0][0])

    @patch("core.hibernation.prober.run")
    def test_get_resume_offset_block_device_returns_zero(self, mock_run):
        with patch("core.hibernation.prober.is_block_device", return_value=True):
            self.assertEqual(get_resume_offset("/dev/sda1"), 0)
        self.assertFalse(mock_run.called)

    @patch("core.hibernation.prober.is_block_device", return_value=False)
    @patch("core.hibernation.prober.run")
    def test_get_partition_uuid_from_file(self, mock_run, mock_is_block):
        mock_run.return_value = MagicMock(code=0, out="/dev/sda2\n")
        mock_run.return_value = MagicMock(code=0, out="abc-123\n")
        res = get_partition_uuid("/swapfile")
        self.assertEqual(res, "abc-123")

    def test_detect_resume_swap_finds_non_zram(self):
        with patch("core.utils.swap.read_file") as mock_read:
            mock_read.return_value = """Filename                Type        Size    Used    Priority
/dev/zram0              partition   4096000 0       100
/swapfile               file        8192000 0       -2"""
            self.assertEqual(detect_resume_swap(), "/swapfile")

    def test_detect_resume_swap_no_swap(self):
        with patch("core.utils.swap.read_file", return_value=""):
            self.assertIsNone(detect_resume_swap())

    def test_get_memory_info(self):
        with patch("core.hibernation.prober.read_file") as mock_read:
            mock_read.return_value = (
                "MemTotal:       16384000 kB\nSwapTotal:       4096000 kB\n"
            )
            ram, swap = get_memory_info()
            self.assertEqual(ram, 16384000 * 1024)
            self.assertEqual(swap, 4096000 * 1024)


if __name__ == "__main__":
    unittest.main()
