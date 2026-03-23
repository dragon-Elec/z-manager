from tests.test_base import *
from core.config import _parse_systemd_cat_config, EffectiveConfig

class TestConfigProvenance(BaseTestCase):
    def test_deep_merge_parsing(self):
        """Verify that we correctly merge and track provenance from multiple files."""
        mock_output = """
# /usr/lib/systemd/zram-generator.conf
[zram0]
zram-size = 512M
compression-algorithm = lzo

# /etc/systemd/zram-generator.conf
[zram0]
zram-size = 4096M

# /usr/lib/systemd/zram-generator.conf.d/10-tweak.conf
[zram0]
swap-priority = 100
"""
        effective = _parse_systemd_cat_config(mock_output)
        
        # 1. Verify Merged Values
        self.assertEqual(effective.config['zram0']['zram-size'], '4096M') # Overridden
        self.assertEqual(effective.config['zram0']['compression-algorithm'], 'lzo') # Inherited
        self.assertEqual(effective.config['zram0']['swap-priority'], '100') # Drop-in
        
        # 2. Verify Provenance (Who owns what?)
        prov = effective.provenance['zram0']
        self.assertEqual(prov['zram-size'], '/etc/systemd/zram-generator.conf')
        self.assertEqual(prov['compression-algorithm'], '/usr/lib/systemd/zram-generator.conf')
        self.assertEqual(prov['swap-priority'], '/usr/lib/systemd/zram-generator.conf.d/10-tweak.conf')

    def test_empty_input(self):
        """Verify robust handling of empty systemd output."""
        effective = _parse_systemd_cat_config("")
        self.assertEqual(len(effective.config), 0)
        self.assertEqual(len(effective.provenance), 0)

if __name__ == "__main__":
    unittest.main()
