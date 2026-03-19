#!/usr/bin/env python3

# test_profiles.py
"""
Unit tests for the profiles module.
Tests profile loading, saving, listing, and deletion with mocked filesystem.
"""

import sys
import os
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from modules import profiles


class TestProfiles(unittest.TestCase):

    def setUp(self):
        """Create a temporary directory for user profiles."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_profile_dir = profiles._PROFILE_DIR
        profiles._PROFILE_DIR = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory and restore original path."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        profiles._PROFILE_DIR = self.original_profile_dir

    # --- get_all_profiles tests ---

    def test_get_all_profiles_returns_builtins(self):
        """Should return at least the built-in profiles."""
        all_profiles = profiles.get_all_profiles()
        self.assertIn("Desktop / Gaming (Recommended)", all_profiles)
        self.assertIn("Server (Conservative)", all_profiles)

    def test_get_all_profiles_includes_user_profiles(self):
        """User profiles should be merged with built-in profiles."""
        # Create a user profile
        user_profile = {"zram-size": "2G", "description": "Test profile"}
        profile_path = Path(self.temp_dir) / "MyCustomProfile.json"
        with profile_path.open("w") as f:
            json.dump(user_profile, f)

        all_profiles = profiles.get_all_profiles()
        self.assertIn("MyCustomProfile", all_profiles)
        self.assertEqual(all_profiles["MyCustomProfile"]["zram-size"], "2G")

    def test_user_profile_can_override_builtin(self):
        """User profile with same name as built-in should override it."""
        # Create a user profile with a built-in name
        override_profile = {"zram-size": "custom", "description": "Override"}
        profile_path = Path(self.temp_dir) / "Desktop / Gaming (Recommended).json"
        # Note: This name has special chars, but Path should handle it
        # Actually, let's use a simpler override test
        profile_path = Path(self.temp_dir) / "Server (Conservative).json"
        with profile_path.open("w") as f:
            json.dump(override_profile, f)

        all_profiles = profiles.get_all_profiles()
        # Should have the overridden value
        self.assertEqual(all_profiles["Server (Conservative)"]["zram-size"], "custom")

    # --- list_profile_names tests ---

    def test_list_profile_names_includes_current_settings(self):
        """Should always include 'Current System Settings' placeholder."""
        names = profiles.list_profile_names()
        self.assertIn("Current System Settings", names)

    def test_list_profile_names_is_sorted(self):
        """Profile names should be returned sorted."""
        names = profiles.list_profile_names()
        self.assertEqual(names, sorted(names))

    # --- load_profile tests ---

    def test_load_profile_builtin(self):
        """Should load a built-in profile by name."""
        profile = profiles.load_profile("Desktop / Gaming (Recommended)")
        self.assertIsNotNone(profile)
        self.assertIn("zram-size", profile)

    def test_load_profile_current_settings_returns_none(self):
        """'Current System Settings' is a UI placeholder, should return None."""
        profile = profiles.load_profile("Current System Settings")
        self.assertIsNone(profile)

    def test_load_profile_nonexistent_returns_none(self):
        """Non-existent profile name should return None."""
        profile = profiles.load_profile("This Profile Does Not Exist")
        self.assertIsNone(profile)

    def test_load_profile_user_profile(self):
        """Should load a user-created profile."""
        user_profile = {"zram-size": "4G", "algorithm": "lz4"}
        profile_path = Path(self.temp_dir) / "UserProfile.json"
        with profile_path.open("w") as f:
            json.dump(user_profile, f)

        loaded = profiles.load_profile("UserProfile")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["zram-size"], "4G")

    # --- save_profile tests ---

    def test_save_profile_creates_file(self):
        """Saving a profile should create a .json file."""
        profile_data = {"zram-size": "8G", "description": "Test save"}
        result = profiles.save_profile("NewProfile", profile_data)

        self.assertTrue(result)
        saved_path = Path(self.temp_dir) / "NewProfile.json"
        self.assertTrue(saved_path.exists())

        with saved_path.open() as f:
            saved = json.load(f)
        self.assertEqual(saved["zram-size"], "8G")

    def test_save_profile_blocks_builtin_names(self):
        """Cannot save a profile with a built-in profile name."""
        profile_data = {"zram-size": "1G"}
        result = profiles.save_profile("Desktop / Gaming (Recommended)", profile_data)
        self.assertFalse(result)

    def test_save_profile_creates_directory_if_missing(self):
        """Should create the profile directory if it doesn't exist."""
        # Point to a non-existent directory
        new_dir = Path(self.temp_dir) / "subdir" / "profiles"
        profiles._PROFILE_DIR = new_dir

        profile_data = {"zram-size": "2G"}
        result = profiles.save_profile("TestProfile", profile_data)

        self.assertTrue(result)
        self.assertTrue(new_dir.exists())

    # --- delete_profile tests ---

    def test_delete_profile_removes_file(self):
        """Deleting a profile should remove the file."""
        profile_path = Path(self.temp_dir) / "ToDelete.json"
        with profile_path.open("w") as f:
            json.dump({"test": True}, f)

        result = profiles.delete_profile("ToDelete")
        self.assertTrue(result)
        self.assertFalse(profile_path.exists())

    def test_delete_profile_blocks_builtin(self):
        """Cannot delete a built-in profile."""
        result = profiles.delete_profile("Desktop / Gaming (Recommended)")
        self.assertFalse(result)

    def test_delete_profile_nonexistent(self):
        """Deleting a non-existent profile should return False."""
        result = profiles.delete_profile("DoesNotExist")
        self.assertFalse(result)

    # --- Edge cases ---

    def test_load_malformed_json(self):
        """Malformed JSON files should be skipped gracefully."""
        bad_path = Path(self.temp_dir) / "BadProfile.json"
        with bad_path.open("w") as f:
            f.write("{ this is not valid json }")

        all_profiles = profiles.get_all_profiles()
        # Should not contain the bad profile
        self.assertNotIn("BadProfile", all_profiles)

    def test_load_non_dict_json(self):
        """JSON files that aren't dicts should be skipped."""
        bad_path = Path(self.temp_dir) / "ArrayProfile.json"
        with bad_path.open("w") as f:
            json.dump([1, 2, 3], f)  # Array, not dict

        all_profiles = profiles.get_all_profiles()
        self.assertNotIn("ArrayProfile", all_profiles)


if __name__ == '__main__':
    unittest.main()
