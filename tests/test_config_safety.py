import unittest
import os
import shutil
import tempfile
import time
from core.os_utils import atomic_write_to_file

class TestConfigSafety(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.file_path = os.path.join(self.test_dir, "test.conf")

    def tearDown(self):
        # Cleanup
        shutil.rmtree(self.test_dir)

    def test_diff_based_writing(self):
        """Verify that writing the same content updates nothing (no mod time change)."""
        content = "initial_content"
        
        # 1. Initial write
        success, err = atomic_write_to_file(self.file_path, content)
        self.assertTrue(success, f"First write failed: {err}")
        self.assertTrue(os.path.exists(self.file_path))
        
        # Capture stats
        stat_1 = os.stat(self.file_path)
        mtime_1 = stat_1.st_mtime_ns
        
        # Artificial delay to ensure time would change if written
        time.sleep(0.01)

        # 2. Write SAME content
        success, err = atomic_write_to_file(self.file_path, content)
        self.assertTrue(success)
        
        stat_2 = os.stat(self.file_path)
        mtime_2 = stat_2.st_mtime_ns
        
        # Verify mtime is UNCHANGED
        self.assertEqual(mtime_1, mtime_2, "File turned out to be overwritten despite identical content!")
        
        # 3. Write NEW content
        new_content = "new_content"
        success, err = atomic_write_to_file(self.file_path, new_content)
        self.assertTrue(success)
        
        stat_3 = os.stat(self.file_path)
        mtime_3 = stat_3.st_mtime_ns
        
        # Verify mtime CHANGED
        self.assertNotEqual(mtime_2, mtime_3, "File was NOT updated with new content!")
        with open(self.file_path, 'r') as f:
            self.assertEqual(f.read(), new_content)

    def test_backup_creation(self):
        """Verify that a .bak file is created when backup=True."""
        content_1 = "version_1"
        atomic_write_to_file(self.file_path, content_1)
        
        content_2 = "version_2"
        # Write new version with backup enabled
        success, err = atomic_write_to_file(self.file_path, content_2, backup=True)
        self.assertTrue(success, f"Backup write failed: {err}")
        
        # Check Main File
        with open(self.file_path, 'r') as f:
            self.assertEqual(f.read(), content_2)
            
        # Check Backup File
        backup_path = self.file_path + ".bak"
        self.assertTrue(os.path.exists(backup_path), "Backup file was not created!")
        
        with open(backup_path, 'r') as f:
            self.assertEqual(f.read(), content_1, "Backup file content is incorrect!")

    def test_backup_skipped_on_no_change(self):
        """Verify backup is NOT created/overwritten if content didn't change (diff check wins)."""
        content = "static"
        atomic_write_to_file(self.file_path, content)
        
        # Ensure no backup exists initially
        backup_path = self.file_path + ".bak"
        if os.path.exists(backup_path):
            os.remove(backup_path)
            
        # Try writing same content with backup=True
        atomic_write_to_file(self.file_path, content, backup=True)
        
        # Should imply NO backup because write was skipped
        self.assertFalse(os.path.exists(backup_path), "Backup created unnecessarily for identical content!")

if __name__ == "__main__":
    unittest.main()
