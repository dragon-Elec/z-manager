import unittest
from unittest.mock import patch, MagicMock
from tests.test_base import BaseTestCase


class TestHibernateSystemd(BaseTestCase):
    def test_generate_swap_unit_content(self):
        from core.hibernation.provisioner import generate_swap_unit

        unit_text = generate_swap_unit("/var/swapfile", priority=0)

        self.assertIn("[Unit]", unit_text)
        self.assertIn("Description=Z-Manager Hibernation Swapfile", unit_text)
        self.assertIn("[Swap]", unit_text)
        self.assertIn("What=/var/swapfile", unit_text)
        self.assertIn("Priority=0", unit_text)
        self.assertIn("Options=nofail", unit_text)
        self.assertIn("[Install]", unit_text)
        self.assertIn("WantedBy=multi-user.target", unit_text)

    def test_escape_unit_name(self):
        from core.hibernation.provisioner import escape_unit_name

        self.assertEqual(escape_unit_name("/var/swapfile"), "var-swapfile.swap")
        self.assertEqual(escape_unit_name("/swapfile"), "swapfile.swap")
        self.assertEqual(escape_unit_name("/mnt/data/swap"), "mnt-data-swap.swap")

    @patch("core.hibernation.provisioner.pkexec_systemctl")
    @patch("core.hibernation.provisioner.pkexec_daemon_reload")
    @patch("core.hibernation.provisioner.pkexec_write")
    @patch("core.hibernation.provisioner.run")
    def test_persist_swap_unit_calls(
        self, mock_run, mock_pkexec, mock_reload, mock_systemctl
    ):
        from core.hibernation.provisioner import persist_swap_unit

        mock_pkexec.return_value = (True, "")
        mock_reload.return_value = (True, "")
        mock_systemctl.return_value = (True, "")
        mock_run.return_value = MagicMock(code=0, out="var-swapfile.swap")

        res = persist_swap_unit("/var/swapfile")

        self.assertTrue(res.success)

        args, _ = mock_pkexec.call_args
        self.assertEqual(args[0], "/etc/systemd/system/var-swapfile.swap")

        self.assertTrue(mock_reload.called)
        self.assertTrue(mock_systemctl.called)

        systemctl_args, _ = mock_systemctl.call_args
        self.assertEqual(systemctl_args[0], "enable")
        self.assertEqual(systemctl_args[1], "var-swapfile.swap")


if __name__ == "__main__":
    unittest.main()
