import os
import shutil
import tempfile
from pathlib import Path
from tests.test_base import *
from core.config import load_effective_config_state

class TestConfigSystemdIntegration(BaseTestCase):
    def setUp(self):
        # Create a temporary 'Mock Root'
        self.test_dir = tempfile.mkdtemp()
        self.mock_root = Path(self.test_dir)
        
        # Setup Hierarchy: /etc and /usr/lib
        self.etc_dir = self.mock_root / "etc/systemd"
        self.usr_lib_dir = self.mock_root / "usr/lib/systemd/zram-generator.conf.d"
        
        self.etc_dir.mkdir(parents=True)
        self.usr_lib_dir.mkdir(parents=True)

    def tearDown(self):
        # Cleanup the mock root
        shutil.rmtree(self.test_dir)

    def test_real_systemd_analyze_merging(self):
        """
        Verify that our engine correctly interacts with the real systemd-analyze binary
        using a mock filesystem root.
        """
        # 1. Seed Vendor Default (Low Priority)
        vendor_file = self.mock_root / "usr/lib/systemd/zram-generator.conf"
        vendor_file.parent.mkdir(parents=True, exist_ok=True)
        vendor_file.write_text("[zram0]\nzram-size = 512M\nalgo = lzo\n")
        
        # 2. Seed Vendor Drop-in (Medium Priority)
        dropin_file = self.usr_lib_dir / "10-tweak.conf"
        dropin_file.write_text("[zram0]\nalgo = lz4\n")
        
        # 3. Seed Admin Override (High Priority)
        admin_file = self.etc_dir / "zram-generator.conf"
        admin_file.write_text("[zram0]\nzram-size = 4096M\n")

        # 4. Call our engine with the mock root
        # This will run: systemd-analyze --root=... cat-config systemd/zram-generator.conf
        effective = load_effective_config_state(root=str(self.mock_root))
        
        # 5. Assert the 'Hierarchy of Truth' was respected by the real binary + our parser
        self.assertEqual(effective.config['zram0']['zram-size'], '4096M') # Admin wins
        self.assertEqual(effective.config['zram0']['algo'], 'lz4') # Drop-in wins over vendor default
        
        # 6. Verify Provenance mapping correctly reflects the mock root paths
        # Note: systemd-analyze output will include the absolute paths of the files it found
        prov = effective.provenance['zram0']
        self.assertIn("etc/systemd/zram-generator.conf", prov['zram-size'])
        self.assertIn("usr/lib/systemd/zram-generator.conf.d/10-tweak.conf", prov['algo'])

if __name__ == "__main__":
    unittest.main()
