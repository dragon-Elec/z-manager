#!/usr/bin/env python3

# test_journal.py
"""
Unit tests for the journal module.
Tests log retrieval and parsing with mocked systemd journal.
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from modules import journal


class TestJournalHelpers(unittest.TestCase):

    def test_format_ts_safe_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = journal._format_ts_safe(dt)
        self.assertIsInstance(result, datetime)

    def test_format_ts_safe_timestamp(self):
        ts = 1705316400.0  # Some Unix timestamp
        result = journal._format_ts_safe(ts)
        self.assertIsInstance(result, datetime)

    def test_format_ts_safe_string(self):
        ts_str = "2024-01-15T10:30:00"
        result = journal._format_ts_safe(ts_str)
        self.assertIsInstance(result, datetime)

    def test_format_ts_safe_invalid(self):
        result = journal._format_ts_safe("garbage")
        self.assertIsInstance(result, datetime)  # Should return current time

    def test_format_ts_safe_none(self):
        result = journal._format_ts_safe(None)
        self.assertIsInstance(result, datetime)


class TestParseIsoBestEffort(unittest.TestCase):

    def test_parse_iso_valid(self):
        result = journal._parse_iso_best_effort("2024-01-15T10:30:00")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_parse_iso_with_timezone(self):
        result = journal._parse_iso_best_effort("2024-01-15T10:30:00+05:30")
        self.assertIsNotNone(result)

    def test_parse_iso_invalid(self):
        result = journal._parse_iso_best_effort("not a date")
        self.assertIsNone(result)


class TestPythonJournalAvailable(unittest.TestCase):

    @patch('modules.journal.run')
    def test_python_journal_available_true(self, mock_run):
        mock_run.return_value = MagicMock(code=0)
        result = journal.python_journal_available()
        self.assertTrue(result)

    @patch('modules.journal.run')
    def test_python_journal_available_false(self, mock_run):
        mock_run.return_value = MagicMock(code=1)
        result = journal.python_journal_available()
        self.assertFalse(result)


class TestSystemdJournalAvailableFlag(unittest.TestCase):

    @patch('modules.journal.python_journal_available')
    def test_available(self, mock_pja):
        mock_pja.return_value = True
        available, reason = journal.systemd_journal_available_flag()
        self.assertTrue(available)
        self.assertIsNone(reason)

    @patch('modules.journal.python_journal_available')
    def test_not_available(self, mock_pja):
        mock_pja.return_value = False
        available, reason = journal.systemd_journal_available_flag()
        self.assertFalse(available)
        self.assertIsNotNone(reason)


class TestListZramLogs(unittest.TestCase):

    @patch('modules.journal.run')
    def test_list_zram_logs_fallback(self, mock_run):
        """Test journalctl fallback when python3-systemd is not available."""
        mock_run.return_value = MagicMock(
            code=0,
            out="""2024-01-15T10:30:00+0530 zram0: Started zram device
2024-01-15T10:30:01+0530 zram0: Swap enabled
"""
        )

        # Force ImportError for systemd.journal
        with patch.dict('sys.modules', {'systemd': None, 'systemd.journal': None}):
            records = journal.list_zram_logs(count=2)

        # Should return JournalRecord objects
        self.assertIsInstance(records, list)

    @patch('modules.journal.run')
    def test_list_zram_logs_empty(self, mock_run):
        """Test with no log output."""
        mock_run.return_value = MagicMock(code=0, out="")

        with patch.dict('sys.modules', {'systemd': None, 'systemd.journal': None}):
            records = journal.list_zram_logs()

        self.assertEqual(records, [])


class TestGetZramLogsFromApi(unittest.TestCase):

    @patch('modules.journal.list_zram_logs')
    def test_returns_dicts(self, mock_list):
        mock_list.return_value = [
            journal.JournalRecord(
                timestamp=datetime.now(),
                priority=6,
                message="Test message",
                fields={"source": "test"}
            )
        ]

        result = journal.get_zram_logs_from_api()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("timestamp", result[0])
        self.assertIn("priority", result[0])
        self.assertIn("message", result[0])


if __name__ == '__main__':
    unittest.main()
