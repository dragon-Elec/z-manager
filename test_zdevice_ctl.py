#!/usr/bin/env python3

# test_zdevice_ctl.py
"""
Unit tests for the zdevice_ctl module.
All tests are fully mocked - no system calls are made.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from core import zdevice_ctl


class TestListDevices(unittest.TestCase):

    @patch('core.zdevice_ctl.parse_zramctl_table')
    def test_list_devices_returns_device_infos(self, mock_parse):
        mock_parse.return_value = [
            {'name': 'zram0', 'disksize': '4G', 'data-size': '1M', 'compr-size': '500K',
             'algorithm': 'lz4', 'streams': 4, 'mountpoint': '[SWAP]', 'ratio': 2.0},
            {'name': 'zram1', 'disksize': '2G', 'data-size': '-', 'compr-size': '-',
             'algorithm': 'zstd', 'streams': 2, 'mountpoint': '', 'ratio': None},
        ]

        devices = zdevice_ctl.list_devices()

        self.assertEqual(len(devices), 2)
        self.assertIsInstance(devices[0], zdevice_ctl.DeviceInfo)
        self.assertEqual(devices[0].name, 'zram0')
        self.assertEqual(devices[0].disksize, '4G')
        self.assertEqual(devices[1].name, 'zram1')

    @patch('core.zdevice_ctl.parse_zramctl_table')
    def test_list_devices_empty(self, mock_parse):
        mock_parse.return_value = []

        devices = zdevice_ctl.list_devices()

        self.assertEqual(devices, [])


class TestGetWritebackStatus(unittest.TestCase):

    @patch('core.zdevice_ctl.read_file')
    @patch('core.zdevice_ctl.zram_sysfs_dir')
    def test_get_writeback_status_with_backing(self, mock_sysfs_dir, mock_read):
        mock_sysfs_dir.return_value = "/sys/block/zram0"
        
        def read_side_effect(path):
            path_str = str(path)
            values = {
                "/sys/block/zram0/backing_dev": "/dev/loop0",
                "/sys/block/zram0/mem_used_total": "1048576",
                "/sys/block/zram0/orig_data_size": "2097152",
                "/sys/block/zram0/compr_data_size": "524288",
                "/sys/block/zram0/bd_stat": "100 5 0",
            }
            return values.get(path_str)
        
        mock_read.side_effect = read_side_effect

        status = zdevice_ctl.get_writeback_status("zram0")

        self.assertIsInstance(status, zdevice_ctl.WritebackStatus)
        self.assertEqual(status.device, "zram0")
        self.assertEqual(status.backing_dev, "/dev/loop0")

    @patch('core.zdevice_ctl.read_file')
    @patch('core.zdevice_ctl.zram_sysfs_dir')
    def test_get_writeback_status_no_backing(self, mock_sysfs_dir, mock_read):
        mock_sysfs_dir.return_value = "/sys/block/zram0"
        
        def read_side_effect(path):
            path_str = str(path)
            values = {
                "/sys/block/zram0/backing_dev": "none",
                "/sys/block/zram0/mem_used_total": "0",
                "/sys/block/zram0/orig_data_size": "0",
                "/sys/block/zram0/compr_data_size": "0",
                "/sys/block/zram0/bd_stat": None,
            }
            return values.get(path_str)
        
        mock_read.side_effect = read_side_effect

        status = zdevice_ctl.get_writeback_status("zram0")

        self.assertEqual(status.backing_dev, "none")


class TestDeviceInfoDataclass(unittest.TestCase):

    def test_device_info_creation(self):
        info = zdevice_ctl.DeviceInfo(
            name="zram0",
            disksize="4G",
            data_size="1M",
            compr_size="500K",
            ratio="2.0",
            streams=4,
            algorithm="lz4"
        )

        self.assertEqual(info.name, "zram0")
        self.assertEqual(info.disksize, "4G")
        self.assertEqual(info.streams, 4)

    def test_device_info_defaults(self):
        info = zdevice_ctl.DeviceInfo(name="zram1")

        self.assertIsNone(info.disksize)
        self.assertIsNone(info.algorithm)
        self.assertIsNone(info.streams)


class TestWritebackStatusDataclass(unittest.TestCase):

    def test_writeback_status_creation(self):
        status = zdevice_ctl.WritebackStatus(
            device="zram0",
            backing_dev="/dev/loop0",
            mem_used_total="1M",
            orig_data_size="2M",
            compr_data_size="500K",
            num_writeback="100",
            writeback_failed="0"
        )

        self.assertEqual(status.device, "zram0")
        self.assertEqual(status.backing_dev, "/dev/loop0")


class TestUnitResultDataclass(unittest.TestCase):

    def test_unit_result_success(self):
        result = zdevice_ctl.UnitResult(
            success=True,
            message="Service restarted",
            service="systemd-zram-setup@zram0.service"
        )
        self.assertTrue(result.success)
        self.assertEqual(result.service, "systemd-zram-setup@zram0.service")

    def test_unit_result_failure(self):
        result = zdevice_ctl.UnitResult(
            success=False,
            message="Unit not found"
        )
        self.assertFalse(result.success)


class TestWritebackResultDataclass(unittest.TestCase):

    def test_writeback_result_creation(self):
        result = zdevice_ctl.WritebackResult(
            success=True,
            device="zram0",
            action="set_writeback",
            details={"backing_dev": "/dev/loop0"}
        )
        self.assertTrue(result.success)
        self.assertEqual(result.device, "zram0")
        self.assertEqual(result.action, "set_writeback")


class TestPersistResultDataclass(unittest.TestCase):

    def test_persist_result_creation(self):
        result = zdevice_ctl.PersistResult(
            success=True,
            device="zram0",
            applied=True,
            message="Writeback persisted"
        )
        self.assertTrue(result.success)
        self.assertTrue(result.applied)


if __name__ == '__main__':
    unittest.main()
