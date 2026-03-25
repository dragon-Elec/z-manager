from tests.test_base import *
import os
from core.utils.block import check_device_safety

class TestDeviceSafety(BaseTestCase):
    def test_zram0_safety(self):
        """Active zram device should be flagged unsafe or at least checked."""
        # Note: zram devices might return True/False depending on if they are formatted/mounted.
        # check_device_safety uses `blkid`. If zram0 has swap signature, it returns False, "Has filesystem: swap"
        is_safe, reason = check_device_safety("/dev/zram0")
        print(f"zram0 safety: {is_safe}, {reason}")
        # We expect it to be UNSAFE because it's an active swap
        self.assertFalse(is_safe, f"Active zram0 should be unsafe. Reason: {reason}")

    def test_root_safety(self):
        """Root partition should be unsafe."""
        # We need to find the root device.
        from core.utils.common import run
        mounts = run(["findmnt", "/", "-o", "SOURCE", "-n"]).out.strip()
        if mounts:
             # Strip subvolume info e.g. /dev/sda2[/@] -> /dev/sda2
             if "[" in mounts:
                 mounts = mounts.split("[")[0]
             
             print(f"Testing active root device: {mounts}")
             is_safe, reason = check_device_safety(mounts)
             print(f"Root safety: {is_safe}, {reason}")
             self.assertFalse(is_safe, "Active root partition must be UNSAFE")

    def test_dummy_file_safety(self):
        """A simple file path should be safe (it's not a block device with a filesystem)."""
        # check_device_safety currently checks if it's a block device first.
        # If it's a file, it might rely on it NOT being a block device.
        dummy = "/tmp/test_swapfile"
        # We don't create it, just check path
        # Actually check_device_safety checks `blkid <path>`. 
        # `blkid` on a non-existent file fails or returns nothing.
        # If file exists and is empty, blkid returns nothing -> Safe.
        if os.path.exists(dummy):
            os.remove(dummy)
        with open(dummy, 'w') as f:
            f.write("0"*1024) # Write some zeros
        
        is_safe, reason = check_device_safety(dummy)
        print(f"Dummy file safety: {is_safe}, {reason}")
        self.assertTrue(is_safe, "Regular file should be SAFE for swapon/mkswap (as long as it's not a block dev with FS)")
        os.remove(dummy)

if __name__ == '__main__':
    unittest.main()
