import unittest
import os
import tempfile
from core.config_writer import update_zram_config

class TestConfigPreservation(unittest.TestCase):
    def setUp(self):
        # Create a temp file with comments
        self.tmp = tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8')
        content = """
# This is my gaming profile
# optimizing for low latency!
[zram0]
zram-size = 4G # plenty for games
compression-algorithm = zstd (level=1)

# Global settings (future proofing)
[zram-generator]
conf-file = /etc/zram-generator.conf
"""
        self.tmp.write(content.strip())
        self.tmp.close()
        
        # Patch core.config.get_active_config_path to return matching path
        from core import config
        self.original_get_path = config.get_active_config_path
        config.get_active_config_path = lambda: self.tmp.name

    def tearDown(self):
        os.unlink(self.tmp.name)
        from core import config
        config.get_active_config_path = self.original_get_path

    def test_comment_preservation(self):
        """Verify that comments are preserved after an update."""
        success, err, rendered = update_zram_config("zram0", {"zram-size": "8G"})
        self.assertTrue(success, f"Update failed: {err}")
        
        self.assertIn("# This is my gaming profile", rendered)
        self.assertIn("# plenty for games", rendered)
        self.assertIn("zram-size = 8G", rendered) # Value updated

    def test_structure_preservation(self):
        """Verify global section is untouched."""
        success, err, rendered = update_zram_config("zram0", {"compression-algorithm": "lz4"})
        self.assertTrue(success)
        
        self.assertIn("[zram-generator]", rendered)
        self.assertIn("conf-file = /etc/zram-generator.conf", rendered)

if __name__ == "__main__":
    unittest.main()
