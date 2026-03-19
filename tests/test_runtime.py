#!/usr/bin/env python3

# test_runtime.py
"""
Unit tests for the runtime module.
Tests CPU governor, I/O scheduler, and kernel parameter functions with mocked sysfs.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from modules import runtime


class TestCpuGovernor(unittest.TestCase):

    @patch('modules.runtime.read_file')
    def test_get_available_cpu_governors(self, mock_read):
        mock_read.return_value = "performance powersave ondemand"
        governors = runtime.get_available_cpu_governors()
        self.assertEqual(governors, ["performance", "powersave", "ondemand"])

    @patch('modules.runtime.read_file')
    def test_get_available_cpu_governors_empty(self, mock_read):
        mock_read.return_value = None
        governors = runtime.get_available_cpu_governors()
        self.assertEqual(governors, [])

    @patch('modules.runtime.read_file')
    def test_get_current_cpu_governor(self, mock_read):
        mock_read.return_value = "performance"
        governor = runtime.get_current_cpu_governor()
        self.assertEqual(governor, "performance")

    @patch('modules.runtime.read_file')
    def test_get_current_cpu_governor_unknown(self, mock_read):
        mock_read.return_value = None
        governor = runtime.get_current_cpu_governor()
        self.assertEqual(governor, "unknown")

    @patch('modules.runtime.sysfs_write')
    @patch('modules.runtime.get_available_cpu_governors')
    @patch.object(Path, 'glob')
    def test_set_cpu_governor_success(self, mock_glob, mock_available, mock_write):
        mock_available.return_value = ["performance", "powersave"]
        # sysfs_write returns None on success, raises on error
        mock_write.return_value = None
        # Mock glob to return some CPU paths
        mock_glob.return_value = [
            Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
            Path("/sys/devices/system/cpu/cpu1/cpufreq/scaling_governor"),
        ]

        result = runtime.set_cpu_governor("performance")
        self.assertTrue(result)

    @patch('modules.runtime.get_available_cpu_governors')
    def test_set_cpu_governor_invalid(self, mock_available):
        mock_available.return_value = ["performance", "powersave"]
        result = runtime.set_cpu_governor("invalid_governor")
        self.assertFalse(result)


class TestIoScheduler(unittest.TestCase):

    @patch('modules.runtime.read_file')
    def test_get_available_io_schedulers(self, mock_read):
        mock_read.return_value = "none [mq-deadline] kyber bfq"
        schedulers = runtime.get_available_io_schedulers("sda")
        self.assertEqual(schedulers, ["none", "mq-deadline", "kyber", "bfq"])

    @patch('modules.runtime.read_file')
    def test_get_available_io_schedulers_empty(self, mock_read):
        mock_read.return_value = None
        schedulers = runtime.get_available_io_schedulers("sda")
        self.assertEqual(schedulers, [])

    @patch('modules.runtime.read_file')
    def test_get_current_io_scheduler(self, mock_read):
        mock_read.return_value = "none [mq-deadline] kyber bfq"
        scheduler = runtime.get_current_io_scheduler("sda")
        self.assertEqual(scheduler, "mq-deadline")

    @patch('modules.runtime.read_file')
    def test_get_current_io_scheduler_no_brackets(self, mock_read):
        mock_read.return_value = "none mq-deadline kyber bfq"
        scheduler = runtime.get_current_io_scheduler("sda")
        self.assertEqual(scheduler, "unknown")

    @patch('modules.runtime.read_file')
    def test_get_current_io_scheduler_empty(self, mock_read):
        mock_read.return_value = None
        scheduler = runtime.get_current_io_scheduler("sda")
        self.assertEqual(scheduler, "unknown")

    @patch('modules.runtime.sysfs_write')
    @patch('modules.runtime.get_available_io_schedulers')
    def test_set_io_scheduler_success(self, mock_available, mock_write):
        mock_available.return_value = ["none", "mq-deadline", "kyber"]
        # sysfs_write returns None on success
        mock_write.return_value = None

        result = runtime.set_io_scheduler("sda", "kyber")
        self.assertTrue(result)

    @patch('modules.runtime.get_available_io_schedulers')
    def test_set_io_scheduler_invalid(self, mock_available):
        mock_available.return_value = ["none", "mq-deadline"]
        result = runtime.set_io_scheduler("sda", "invalid_scheduler")
        self.assertFalse(result)

    def test_set_io_scheduler_empty_device(self):
        result = runtime.set_io_scheduler("", "mq-deadline")
        self.assertFalse(result)

    def test_set_io_scheduler_whitespace_device(self):
        result = runtime.set_io_scheduler("   ", "mq-deadline")
        self.assertFalse(result)


class TestVfsCachePressure(unittest.TestCase):

    @patch('modules.runtime.read_file')
    def test_get_vfs_cache_pressure(self, mock_read):
        mock_read.return_value = "100"
        value = runtime.get_vfs_cache_pressure()
        self.assertEqual(value, 100)

    @patch('modules.runtime.read_file')
    def test_get_vfs_cache_pressure_custom(self, mock_read):
        mock_read.return_value = "50"
        value = runtime.get_vfs_cache_pressure()
        self.assertEqual(value, 50)

    @patch('modules.runtime.read_file')
    def test_get_vfs_cache_pressure_invalid(self, mock_read):
        mock_read.return_value = "not_a_number"
        value = runtime.get_vfs_cache_pressure()
        self.assertEqual(value, 100)  # Should return default

    @patch('modules.runtime.read_file')
    def test_get_vfs_cache_pressure_none(self, mock_read):
        mock_read.return_value = None
        value = runtime.get_vfs_cache_pressure()
        self.assertEqual(value, 100)  # Should return default

    @patch('modules.runtime.sysfs_write')
    def test_set_vfs_cache_pressure_success(self, mock_write):
        mock_write.return_value = None
        result = runtime.set_vfs_cache_pressure(50)
        self.assertTrue(result)
        mock_write.assert_called_once()

    def test_set_vfs_cache_pressure_invalid_negative(self):
        result = runtime.set_vfs_cache_pressure(-1)
        self.assertFalse(result)

    def test_set_vfs_cache_pressure_invalid_too_high(self):
        result = runtime.set_vfs_cache_pressure(501)
        self.assertFalse(result)

    @patch('modules.runtime.sysfs_write')
    def test_set_vfs_cache_pressure_boundary_low(self, mock_write):
        mock_write.return_value = None
        result = runtime.set_vfs_cache_pressure(0)
        self.assertTrue(result)

    @patch('modules.runtime.sysfs_write')
    def test_set_vfs_cache_pressure_boundary_high(self, mock_write):
        mock_write.return_value = None
        result = runtime.set_vfs_cache_pressure(500)
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
