
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from modules import psi

class TestPsi(unittest.TestCase):

    def test_get_psi_success(self):
        # Mock content for /proc/pressure/memory
        content = "some avg10=0.00 avg60=0.00 avg300=0.00 total=0\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=0"
        
        with patch('modules.psi.read_file', return_value=content):
            stats = psi.get_psi("memory")
            self.assertIsNotNone(stats)
            self.assertEqual(stats.resource, "memory")
            self.assertEqual(stats.some_avg10, 0.00)
            self.assertEqual(stats.full_total, 0)

    def test_get_psi_not_found(self):
        # Simulate file not found (read_file returns None)
        with patch('modules.psi.read_file', return_value=None):
            stats = psi.get_psi("memory")
            self.assertIsNone(stats)

    def test_get_psi_malformed(self):
        # Simulate malformed content
        content = "GARBAGE"
        with patch('modules.psi.read_file', return_value=content):
            # Should catch exception and return None
            stats = psi.get_psi("memory")
            self.assertIsNone(stats)

if __name__ == '__main__':
    unittest.main()
