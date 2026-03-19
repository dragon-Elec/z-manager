#!/usr/bin/env python3

# test_boot_config.py
"""
Unit tests for the boot_config module.
All tests are fully mocked - no system calls are made.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from core import boot_config


class TestIsKernelParamActive(unittest.TestCase):

    @patch('core.boot_config.read_file')
    def test_is_kernel_param_active_found(self, mock_read_file):
        mock_read_file.return_value = "BOOT_IMAGE=/vmlinuz-6.8.0-49-generic root=UUID=... ro quiet splash zswap.enabled=0"
        self.assertTrue(boot_config.is_kernel_param_active("zswap.enabled=0"))
        self.assertTrue(boot_config.is_kernel_param_active("quiet"))

    @patch('core.boot_config.read_file')
    def test_is_kernel_param_active_not_found(self, mock_read_file):
        mock_read_file.return_value = "BOOT_IMAGE=/vmlinuz-6.8.0-49-generic root=UUID=... ro quiet splash"
        self.assertFalse(boot_config.is_kernel_param_active("zswap.enabled=0"))
        self.assertFalse(boot_config.is_kernel_param_active("psi=1"))

    @patch('core.boot_config.read_file')
    def test_is_kernel_param_active_error(self, mock_read_file):
        mock_read_file.return_value = None  # read_file returns None on error
        self.assertFalse(boot_config.is_kernel_param_active("quiet"))


class TestGetSwappiness(unittest.TestCase):

    @patch('core.boot_config.read_file')
    def test_get_swappiness_normal(self, mock_read):
        mock_read.return_value = "60"
        result = boot_config.get_swappiness()
        self.assertEqual(result, 60)

    @patch('core.boot_config.read_file')
    def test_get_swappiness_custom(self, mock_read):
        mock_read.return_value = "10"
        result = boot_config.get_swappiness()
        self.assertEqual(result, 10)

    @patch('core.boot_config.read_file')
    def test_get_swappiness_none_returns_none(self, mock_read):
        mock_read.return_value = None
        result = boot_config.get_swappiness()
        self.assertIsNone(result)  # Returns None when file unreadable

    @patch('core.boot_config.read_file')
    def test_get_swappiness_invalid_returns_none(self, mock_read):
        mock_read.return_value = "not_a_number"
        result = boot_config.get_swappiness()
        self.assertIsNone(result)  # Returns None for invalid values


class TestTuneResult(unittest.TestCase):
    """Test the TuneResult dataclass."""

    def test_tune_result_creation(self):
        result = boot_config.TuneResult(
            success=True,
            changed=True,
            message="Test message"
        )
        self.assertTrue(result.success)
        self.assertTrue(result.changed)
        self.assertEqual(result.message, "Test message")
        self.assertIsNone(result.action_needed)

    def test_tune_result_with_action_needed(self):
        result = boot_config.TuneResult(
            success=True,
            changed=True,
            message="Test",
            action_needed="run update-grub"
        )
        self.assertEqual(result.action_needed, "run update-grub")


if __name__ == '__main__':
    unittest.main()
