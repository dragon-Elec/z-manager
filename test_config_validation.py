import unittest
from core.config_writer import validate_updates, update_zram_config

class TestConfigValidation(unittest.TestCase):
    def test_size_validation(self):
        # Valid
        self.assertIsNone(validate_updates({"zram-size": "512M"}))
        self.assertIsNone(validate_updates({"zram-size": "ram / 2"}))
        self.assertIsNone(validate_updates({"zram-size": "min(ram, 4096)"}))
        
        # Invalid
        self.assertIsNotNone(validate_updates({"zram-size": "512M!"})) # Invalid char
        self.assertIsNotNone(validate_updates({"zram-size": "512M; rm -rf /"})) # Injection attempt

    def test_algo_validation(self):
        # Valid
        self.assertIsNone(validate_updates({"compression-algorithm": "zstd"}))
        self.assertIsNone(validate_updates({"compression-algorithm": "zstd(level=1) lzo-rle"}))
        
        # Invalid
        self.assertIsNotNone(validate_updates({"compression-algorithm": "lz4; reboot"})) # Injection attempt

    def test_global_section_protection(self):
        """Ensure we cannot create a device named 'zram-generator'."""
        success, err, rendered = update_zram_config("zram-generator", {"zram-size": "1G"})
        self.assertFalse(success)
        self.assertIn("reserved", err)

    def test_integration_rejection(self):
        """Ensure update_zram_config actually rejects bad data."""
        success, err, rendered = update_zram_config("zram0", {"zram-size": "512M; ls"})
        self.assertFalse(success)
        self.assertIn("Invalid zram-size", err)

if __name__ == "__main__":
    unittest.main()
