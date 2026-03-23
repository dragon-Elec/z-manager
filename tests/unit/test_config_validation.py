from tests.test_base import *
from core.config_writer import validate_updates, update_zram_config

class TestConfigValidation(BaseTestCase):
    def test_size_validation(self):
        # Valid
        self.assertIsNone(validate_updates({"zram-size": "512M"}))
        self.assertIsNone(validate_updates({"zram-size": "ram / 2"}))
        self.assertIsNone(validate_updates({"zram-size": "min(ram, 4096.5)"}))
        
        # Invalid (Specialized)
        self.assertIsNotNone(validate_updates({"zram-size": "512M!"})) # Invalid char
        self.assertIsNotNone(validate_updates({"zram-size": "512M; rm -rf /"})) # Injection attempt

    def test_injection_hardening(self):
        """CRITICAL: Verify the new Security Hardening (Newline/Section Injection)."""
        # 1. Newline injection in value
        self.assertIsNotNone(validate_updates({"zram-size": "512M\n[malicious]"}))
        self.assertIsNotNone(validate_updates({"compression-algorithm": "zstd\r\nkey=val"}))
        
        # 2. Section injection (starting with '[')
        self.assertIsNotNone(validate_updates({"compression-algorithm": "[zram1]"}))
        
        # 3. Key injection (newlines in keys)
        self.assertIsNotNone(validate_updates({"zram-size\nkey": "value"}))

    def test_algo_validation(self):
        # Valid
        self.assertIsNone(validate_updates({"compression-algorithm": "zstd"}))
        self.assertIsNone(validate_updates({"compression-algorithm": "zstd(level=1) lzo-rle"}))
        
        # Invalid
        self.assertIsNotNone(validate_updates({"compression-algorithm": "lz4; reboot"}))

    def test_swap_priority_validation(self):
        """Verify the new integer-only priority check."""
        self.assertIsNone(validate_updates({"swap-priority": "100"}))
        self.assertIsNone(validate_updates({"swap-priority": "-2"}))
        self.assertIsNotNone(validate_updates({"swap-priority": "100.5"}))
        self.assertIsNotNone(validate_updates({"swap-priority": "high"}))

    def test_global_section_protection(self):
        """Ensure we cannot create a device named 'zram-generator'."""
        success, err, rendered = update_zram_config("zram-generator", {"zram-size": "1G"})
        self.assertFalse(success)
        self.assertIn("reserved", err)

if __name__ == "__main__":
    unittest.main()
