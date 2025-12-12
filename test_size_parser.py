
import sys
import unittest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from core import os_utils

class TestSizeParser(unittest.TestCase):

    def test_standard_units(self):
        self.assertEqual(os_utils.parse_size_to_bytes("1K"), 1024)
        self.assertEqual(os_utils.parse_size_to_bytes("1M"), 1024**2)
        self.assertEqual(os_utils.parse_size_to_bytes("1G"), 1024**3)
        self.assertEqual(os_utils.parse_size_to_bytes("4G"), 4 * 1024**3)

    def test_iec_units(self):
        # These are currently expected to fail or return 0 with the old parser
        self.assertEqual(os_utils.parse_size_to_bytes("1KiB"), 1024)
        self.assertEqual(os_utils.parse_size_to_bytes("1MiB"), 1024**2)
        self.assertEqual(os_utils.parse_size_to_bytes("1GiB"), 1024**3)

    def test_decimals(self):
        self.assertEqual(os_utils.parse_size_to_bytes("1.5K"), 1536)
        self.assertEqual(os_utils.parse_size_to_bytes("0.5M"), 512 * 1024)

    def test_whitespace(self):
        self.assertEqual(os_utils.parse_size_to_bytes(" 1G "), 1024**3)
        self.assertEqual(os_utils.parse_size_to_bytes("1 G"), 1024**3) # Should ideally handle this

    def test_no_units(self):
        self.assertEqual(os_utils.parse_size_to_bytes("1024"), 1024)
        self.assertEqual(os_utils.parse_size_to_bytes("0"), 0)

    def test_invalid(self):
        self.assertEqual(os_utils.parse_size_to_bytes("invalid"), 0)
        self.assertEqual(os_utils.parse_size_to_bytes(""), 0)
        self.assertEqual(os_utils.parse_size_to_bytes(None), 0)

if __name__ == '__main__':
    unittest.main()
