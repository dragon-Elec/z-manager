import unittest
from unittest.mock import patch, MagicMock
from tests.test_base import BaseTestCase
from core import hibernate_ctl

class TestHibernateSystemd(BaseTestCase):
    """
    TDD for the 'fstab Exit' refactor.
    Ensures hibernation swap is managed via systemd .swap units, not /etc/fstab.
    """

    def test_generate_swap_unit_content(self):
        """Verify the INI-style content for a standard swapfile unit."""
        # This function doesn't exist yet, it's our target.
        unit_text = hibernate_ctl.generate_swap_unit("/var/swapfile", priority=0)
        
        self.assertIn("[Unit]", unit_text)
        self.assertIn("Description=Z-Manager Hibernation Swapfile", unit_text)
        self.assertIn("[Swap]", unit_text)
        self.assertIn("What=/var/swapfile", unit_text)
        self.assertIn("Priority=0", unit_text)
        self.assertIn("Options=nofail", unit_text)
        self.assertIn("[Install]", unit_text)
        self.assertIn("WantedBy=multi-user.target", unit_text)

    def test_escape_unit_name(self):
        """Verify that paths are correctly escaped for systemd unit filenames."""
        # /var/swapfile -> var-swapfile.swap
        # /swapfile -> swapfile.swap
        # /mnt/data/swap -> mnt-data-swap.swap
        self.assertEqual(hibernate_ctl.escape_unit_name("/var/swapfile"), "var-swapfile.swap")
        self.assertEqual(hibernate_ctl.escape_unit_name("/swapfile"), "swapfile.swap")
        self.assertEqual(hibernate_ctl.escape_unit_name("/mnt/data/swap"), "mnt-data-swap.swap")

    @patch("core.hibernate_ctl.pkexec_write")
    @patch("core.hibernate_ctl.run")
    def test_persist_swap_unit_calls(self, mock_run, mock_pkexec):
        """Verify the orchestration sequence: Write -> Reload -> Enable."""
        mock_pkexec.return_value = (True, "")
        mock_run.return_value = MagicMock(code=0)
        
        # This function doesn't exist yet.
        success, msg = hibernate_ctl.persist_swap_unit("/var/swapfile")
        
        self.assertTrue(success)
        
        # 1. Verify Write to correct location
        # The first arg to pkexec_write should be the .swap unit path
        args, kwargs = mock_pkexec.call_args
        self.assertEqual(args[0], "/etc/systemd/system/var-swapfile.swap")
        
        # 2. Verify systemd commands
        # Should call daemon-reload and enable --now
        calls = [call[0][0] for call in mock_run.call_args_list]
        self.assertTrue(any("daemon-reload" in str(c) for c in calls))
        self.assertTrue(any("enable" in str(c) and "now" in str(c) for c in calls))

if __name__ == "__main__":
    unittest.main()
