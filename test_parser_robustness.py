
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from core import os_utils

class TestZramctlParser(unittest.TestCase):

    def test_parse_standard_output(self):
        # Standard output from zramctl
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 lz4             4G  4K   74B   12K       4 [SWAP]
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0]['name'], 'zram0')
            self.assertEqual(devices[0]['disksize'], '4G')
            self.assertEqual(devices[0]['algorithm'], 'lz4')
            self.assertEqual(devices[0]['mountpoint'], '[SWAP]')

    def test_parse_no_devices(self):
        # Output when no devices exist (just header? or empty?)
        # Usually zramctl returns just exit code 0 and empty output or just header if no devices
        output = "" 
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            self.assertEqual(len(devices), 0)

    def test_parse_malformed_lines(self):
        # Malformed lines that should be skipped or handled gracefully
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 lz4             4G  4K   74B   12K       4 [SWAP]
GARBAGE_LINE_WITH_NO_STRUCTURE
/dev/zram1 zstd            2G  -    -     -         2
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            # Should get zram0 and zram1, skipping garbage
            # Current implementation might crash or produce weird data on garbage
            self.assertEqual(len(devices), 2) 
            self.assertEqual(devices[0]['name'], 'zram0')
            self.assertEqual(devices[1]['name'], 'zram1')

    def test_parse_unexpected_columns(self):
        # Output with unexpected column spacing or missing columns
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 4G
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            # This is ambiguous. Current parser might fail or return partial data.
            # We want it to be safe.
            self.assertTrue(len(devices) <= 1)

    def test_parse_invalid_values(self):
        # Structure is correct, but values are nonsense
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 lz4             BADSIZE  4K   74B   12K       4 [SWAP]
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            # We want strict validation to REJECT this line
            self.assertEqual(len(devices), 0)

    # ============ Additional Edge Case Tests ============

    def test_parse_whitespace_variations(self):
        # Extra whitespace, tabs, and mixed spacing
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0    lz4          4G    4K   74B   12K       4    [SWAP]
   /dev/zram1 	zstd 	2G  	1M   500K  1.5M      2
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            self.assertEqual(len(devices), 2)
            self.assertEqual(devices[0]['name'], 'zram0')
            self.assertEqual(devices[1]['name'], 'zram1')

    def test_parse_empty_fields(self):
        # Empty or dash values for optional fields
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 lz4             4G  -    -     -        4
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0]['disksize'], '4G')
            # Empty mountpoint should be handled
            self.assertEqual(devices[0]['mountpoint'], '')

    def test_parse_decimal_sizes(self):
        # Decimal size values like 1.5G, 0.5M
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 lz4             1.5G  0.5M   256K   512K       4 [SWAP]
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0]['disksize'], '1.5G')

    def test_parse_various_algorithms(self):
        # Different compression algorithms
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 lz4             4G  4K   74B   12K       4 [SWAP]
/dev/zram1 zstd            2G  1M   500K  1M        2 [SWAP]
/dev/zram2 lzo             1G  2M   1M    1.5M      1 [SWAP]
/dev/zram3 lzo-rle         512M  -    -     -        1
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            self.assertEqual(len(devices), 4)
            self.assertEqual(devices[0]['algorithm'], 'lz4')
            self.assertEqual(devices[1]['algorithm'], 'zstd')
            self.assertEqual(devices[2]['algorithm'], 'lzo')
            self.assertEqual(devices[3]['algorithm'], 'lzo-rle')

    def test_parse_long_mountpoint(self):
        # Very long mountpoint path with spaces
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 lz4             4G  4K   74B   12K       4 /mnt/some very long path/with spaces/and more
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0]['mountpoint'], '/mnt/some very long path/with spaces/and more')

    def test_parse_mixed_valid_invalid(self):
        # Mix of valid and invalid lines - only valid should be parsed
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 lz4             4G  4K   74B   12K       4 [SWAP]
/dev/zram1 lz4             BAD  4K   74B   12K       4 [SWAP]
/dev/zram2 lz4             2G  INVALID   74B   12K       4 [SWAP]
/dev/zram3 zstd            1G  1M   500K  1M        2 [SWAP]
BADDEVICE  lz4             1G  4K   74B   12K       4 [SWAP]
/dev/zram4 lz4             512M  -    -     -        invalid
/dev/zram5 lz4             256M  -    -     -        8 [SWAP]
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            # Only zram0, zram3, zram5 should be valid
            self.assertEqual(len(devices), 3)
            names = [d['name'] for d in devices]
            self.assertIn('zram0', names)
            self.assertIn('zram3', names)
            self.assertIn('zram5', names)

    def test_parse_only_header(self):
        # Just header, no data lines
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            self.assertEqual(len(devices), 0)

    def test_parse_high_stream_count(self):
        # Very high stream count (like on many-core systems)
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 lz4             4G  4K   74B   12K       128 [SWAP]
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0]['streams'], 128)

    def test_parse_compression_ratio(self):
        # Test compression ratio calculation
        # 4K data, 74B compressed = 4096 / 74 = ~55.35
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 lz4             4G  4K   74B   12K       4 [SWAP]
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            self.assertEqual(len(devices), 1)
            self.assertIsNotNone(devices[0].get('ratio'))
            # 4096 / 74 = 55.35 (rounded to 2 decimal places)
            self.assertAlmostEqual(devices[0]['ratio'], 55.35, places=1)

    def test_parse_compression_ratio_with_dash(self):
        # When DATA or COMPR is "-", ratio should be None
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 lz4             4G  -    -     -        4 [SWAP]
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            self.assertEqual(len(devices), 1)
            self.assertIsNone(devices[0].get('ratio'))

    def test_parse_compression_ratio_real_values(self):
        # Real-world-ish values: 1M data compressed to 500K = 2:1 ratio
        output = """NAME       ALGORITHM DISKSIZE  DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 zstd            2G  1M   500K  1M        2 [SWAP]
"""
        with patch('core.os_utils.zramctl_info_all', return_value=output):
            devices = os_utils.parse_zramctl_table()
            self.assertEqual(len(devices), 1)
            # 1M / 500K = 1048576 / 512000 = ~2.05
            self.assertAlmostEqual(devices[0]['ratio'], 2.05, places=1)

if __name__ == '__main__':
    unittest.main()

