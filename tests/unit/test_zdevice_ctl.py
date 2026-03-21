from tests.test_base import *
from unittest.mock import patch, MagicMock

from core.device_management import prober, types as dm_types


class TestListDevices(BaseTestCase):

    @patch('core.device_management.prober.parse_zramctl_table')
    def test_list_devices_returns_device_infos(self, mock_parse):
        mock_parse.return_value = [
            {'name': 'zram0', 'disksize': '4G', 'data-size': '1M', 'compr-size': '500K',
             'algorithm': 'lz4', 'streams': 4, 'mountpoint': '[SWAP]', 'ratio': 2.0},
            {'name': 'zram1', 'disksize': '2G', 'data-size': '-', 'compr-size': '-',
             'algorithm': 'zstd', 'streams': 2, 'mountpoint': '', 'ratio': None},
        ]

        devices = prober.list_devices()

        self.assertEqual(len(devices), 2)
        self.assertIsInstance(devices[0], dm_types.DeviceInfo)
        self.assertEqual(devices[0].name, 'zram0')
        self.assertEqual(devices[0].disksize, '4G')
        self.assertEqual(devices[1].name, 'zram1')

    @patch('core.device_management.prober.parse_zramctl_table')
    def test_list_devices_empty(self, mock_parse):
        mock_parse.return_value = []

        devices = prober.list_devices()

        self.assertEqual(devices, [])


class TestGetWritebackStatus(BaseTestCase):

    @patch('core.device_management.prober.read_file')
    @patch('core.device_management.prober.zram_sysfs_dir')
    @patch('core.device_management.prober.is_block_device')
    def test_get_writeback_status_with_backing(self, mock_is_block_dev, mock_sysfs_dir, mock_read):
        mock_is_block_dev.return_value = True
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

        status = prober.get_writeback_status("zram0")

        self.assertIsInstance(status, dm_types.WritebackStatus)
        self.assertEqual(status.device, "zram0")
        self.assertEqual(status.backing_dev, "/dev/loop0")

    @patch('core.device_management.prober.read_file')
    @patch('core.device_management.prober.zram_sysfs_dir')
    @patch('core.device_management.prober.is_block_device')
    def test_get_writeback_status_no_backing(self, mock_is_block_dev, mock_sysfs_dir, mock_read):
        mock_is_block_dev.return_value = True
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

        status = prober.get_writeback_status("zram0")

        self.assertEqual(status.backing_dev, "none")


class TestDeviceInfoDataclass(BaseTestCase):

    def test_device_info_creation(self):
        info = dm_types.DeviceInfo(
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
        info = dm_types.DeviceInfo(name="zram1")

        self.assertIsNone(info.disksize)
        self.assertIsNone(info.algorithm)
        self.assertIsNone(info.streams)


class TestWritebackStatusDataclass(BaseTestCase):

    def test_writeback_status_creation(self):
        status = dm_types.WritebackStatus(
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


class TestUnitResultDataclass(BaseTestCase):

    def test_unit_result_success(self):
        result = dm_types.UnitResult(
            success=True,
            message="Service restarted",
            service="systemd-zram-setup@zram0.service"
        )
        self.assertTrue(result.success)
        self.assertEqual(result.service, "systemd-zram-setup@zram0.service")

    def test_unit_result_failure(self):
        result = dm_types.UnitResult(
            success=False,
            message="Unit not found"
        )
        self.assertFalse(result.success)


class TestWritebackResultDataclass(BaseTestCase):

    def test_writeback_result_creation(self):
        result = dm_types.WritebackResult(
            success=True,
            device="zram0",
            action="set_writeback",
            details={"backing_dev": "/dev/loop0"}
        )
        self.assertTrue(result.success)
        self.assertEqual(result.device, "zram0")
        self.assertEqual(result.action, "set_writeback")


class TestPersistResultDataclass(BaseTestCase):

    def test_persist_result_creation(self):
        result = dm_types.PersistResult(
            success=True,
            device="zram0",
            applied=True,
            message="Writeback persisted"
        )
        self.assertTrue(result.success)
        self.assertTrue(result.applied)


if __name__ == '__main__':
    unittest.main()
