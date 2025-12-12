# Updated: Test Migration (test_parser_robustness.py)

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from core import os_utils

class TestSysfsParser(unittest.TestCase):

    @patch('core.os_utils._scan_zram_devices')
    @patch('core.os_utils._read_zram_sysfs_props')
    def test_parse_standard_device(self, mock_read, mock_scan):
        # Setup mocks
        mock_scan.return_value = ['zram0']
        mock_read.return_value = {
            "name": "zram0",
            "disksize": "4G",
            "data-size": "4K",
            "compr-size": "74B",
            "total-size": "12K",
            "streams": 4,
            "algorithm": "lz4",
            "mountpoint": "[SWAP]",
            "ratio": 55.35
        }

        # Execute
        devices = os_utils.parse_zramctl_table()

        # Assert
        self.assertEqual(len(devices), 1)
        d = devices[0]
        self.assertEqual(d['name'], 'zram0')
        self.assertEqual(d['disksize'], '4G')
        self.assertEqual(d['algorithm'], 'lz4')
        self.assertEqual(d['mountpoint'], '[SWAP]')
        self.assertEqual(d['streams'], 4)

    @patch('core.os_utils._scan_zram_devices')
    @patch('core.os_utils._read_zram_sysfs_props')
    def test_parse_multiple_devices(self, mock_read, mock_scan):
        mock_scan.return_value = ['zram0', 'zram1']
        
        # Side effect to return different props for different devices
        def side_effect(dev_name):
            if dev_name == 'zram0':
                return {"name": "zram0", "disksize": "4G", "algorithm": "lz4", "mountpoint": "[SWAP]"}
            else:
                return {"name": "zram1", "disksize": "2G", "algorithm": "zstd", "mountpoint": ""}
        
        mock_read.side_effect = side_effect

        devices = os_utils.parse_zramctl_table()

        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]['name'], 'zram0')
        self.assertEqual(devices[0]['algorithm'], 'lz4')
        self.assertEqual(devices[1]['name'], 'zram1')
        self.assertEqual(devices[1]['algorithm'], 'zstd')

    @patch('core.os_utils._scan_zram_devices')
    @patch('core.os_utils._read_zram_sysfs_props')
    def test_parse_no_devices(self, mock_read, mock_scan):
        mock_scan.return_value = []
        devices = os_utils.parse_zramctl_table()
        self.assertEqual(len(devices), 0)

    @patch('core.os_utils._scan_zram_devices')
    @patch('core.os_utils._read_zram_sysfs_props')
    def test_handle_read_error(self, mock_read, mock_scan):
        mock_scan.return_value = ['zram0']
        # Simulate an error reading props (e.g. device disappeared)
        mock_read.side_effect = OSError("Device not found")

        devices = os_utils.parse_zramctl_table()
        
        # Should gracefully skip the bad device
        self.assertEqual(len(devices), 0)

    @patch('core.os_utils._scan_zram_devices')
    @patch('core.os_utils._read_zram_sysfs_props')
    def test_skip_unconfigured_devices(self, mock_read, mock_scan):
        mock_scan.return_value = ['zram0']
        # Device exists but has no disksize set (unconfigured)
        mock_read.return_value = {"name": "zram0", "disksize": "-"} # or None

        devices = os_utils.parse_zramctl_table()
        self.assertEqual(len(devices), 0)

if __name__ == '__main__':
    unittest.main()
