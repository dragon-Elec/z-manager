from tests.test_base import *
from core.utils import units as os_utils

class TestSizeParser(BaseTestCase):

    def test_standard_units(self):
        self.assertEqual(os_utils.parse_size_to_bytes("1K"), 1024)
        self.assertEqual(os_utils.parse_size_to_bytes("1M"), 1024**2)
        self.assertEqual(os_utils.parse_size_to_bytes("1G"), 1024**3)
        self.assertEqual(os_utils.parse_size_to_bytes("4G"), 4 * 1024**3)

    def test_iec_units(self):
        """Verify modern IEC units (KiB, MiB, GiB) are handled via normalization."""
        self.assertEqual(os_utils.parse_size_to_bytes("1KiB"), 1024)
        self.assertEqual(os_utils.parse_size_to_bytes("1MiB"), 1024**2)
        self.assertEqual(os_utils.parse_size_to_bytes("1GiB"), 1024**3)

    def test_decimals(self):
        self.assertEqual(os_utils.parse_size_to_bytes("1.5K"), 1536)
        self.assertEqual(os_utils.parse_size_to_bytes("0.5M"), 512 * 1024)

    def test_whitespace(self):
        self.assertEqual(os_utils.parse_size_to_bytes(" 1G "), 1024**3)
        self.assertEqual(os_utils.parse_size_to_bytes("1 G"), 1024**3)

    def test_no_units(self):
        self.assertEqual(os_utils.parse_size_to_bytes("1024"), 1024)
        self.assertEqual(os_utils.parse_size_to_bytes("0"), 0)

    def test_invalid(self):
        self.assertEqual(os_utils.parse_size_to_bytes("invalid"), 0)
        self.assertEqual(os_utils.parse_size_to_bytes(""), 0)
        self.assertEqual(os_utils.parse_size_to_bytes(None), 0)

if __name__ == '__main__':
    unittest.main()
