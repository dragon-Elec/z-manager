from tests.test_base import *
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

from core.hibernation.provisioner import (
    create_swapfile,
    enable_swapon,
    swapoff_swap,
    escape_unit_name,
    generate_swap_unit,
    persist_swap_unit,
    delete_swap,
)


class TestProvisioner(BaseTestCase):
    @patch("core.hibernation.provisioner.get_resume_offset")
    @patch("core.hibernation.provisioner.get_partition_uuid")
    @patch("core.hibernation.provisioner.os.chmod")
    @patch("core.hibernation.provisioner.run")
    @patch("core.hibernation.provisioner._get_fs_type")
    @patch("os.path.exists")
    def test_create_swapfile_ext4(
        self, mock_exists, mock_fs, mock_run, mock_chmod, mock_uuid, mock_offset
    ):
        mock_exists.return_value = False
        mock_fs.return_value = "ext4"
        mock_uuid.return_value = "uuid-123"
        mock_offset.return_value = 12345
        mock_run.return_value = MagicMock(code=0)

        res = create_swapfile("/swapfile", 1024)
        self.assertTrue(res.success)

        calls = [str(c[0][0]) for c in mock_run.call_args_list]
        self.assertTrue(any("fallocate" in cmd for cmd in calls))
        self.assertFalse(any("truncate" in cmd for cmd in calls))

    @patch("core.hibernation.provisioner.get_resume_offset")
    @patch("core.hibernation.provisioner.get_partition_uuid")
    @patch("core.hibernation.provisioner.os.chmod")
    @patch("core.hibernation.provisioner.run")
    @patch("core.hibernation.provisioner._get_fs_type")
    @patch("os.path.exists")
    def test_create_swapfile_btrfs(
        self, mock_exists, mock_fs, mock_run, mock_chmod, mock_uuid, mock_offset
    ):
        mock_exists.return_value = False
        mock_fs.return_value = "btrfs"
        mock_uuid.return_value = "uuid-123"
        mock_offset.return_value = 12345
        mock_run.return_value = MagicMock(code=0)

        res = create_swapfile("/swapfile", 1024)
        self.assertTrue(res.success)

        calls = str([c[0][0] for c in mock_run.call_args_list])
        self.assertIn("truncate", calls)
        self.assertIn("chattr", calls)

    def test_generate_swap_unit_content(self):
        unit_text = generate_swap_unit("/var/swapfile", priority=0)

        self.assertIn("[Unit]", unit_text)
        self.assertIn("Description=Z-Manager Hibernation Swapfile", unit_text)
        self.assertIn("[Swap]", unit_text)
        self.assertIn("What=/var/swapfile", unit_text)
        self.assertIn("Priority=0", unit_text)
        self.assertIn("Options=nofail", unit_text)
        self.assertIn("[Install]", unit_text)
        self.assertIn("WantedBy=multi-user.target", unit_text)

    @patch("core.hibernation.provisioner.run")
    def test_escape_unit_name_systemd_escape(self, mock_run):
        mock_run.return_value = MagicMock(out="var-swapfile.swap\n", code=0)
        self.assertEqual(escape_unit_name("/var/swapfile"), "var-swapfile.swap")

    @patch("core.hibernation.provisioner.run")
    def test_escape_unit_name_fallback(self, mock_run):
        from core.utils.common import SystemCommandError

        mock_run.side_effect = SystemCommandError(
            ["systemd-escape"], 1, "", "not found"
        )
        self.assertEqual(escape_unit_name("/swapfile"), "swapfile.swap")
        self.assertEqual(escape_unit_name("/mnt/data/swap"), "mnt-data-swap.swap")

    @patch("core.hibernation.provisioner.pkexec_systemctl")
    @patch("core.hibernation.provisioner.pkexec_daemon_reload")
    @patch("core.hibernation.provisioner.pkexec_write")
    @patch("core.hibernation.provisioner.run")
    def test_persist_swap_unit_success(
        self, mock_run, mock_pkexec, mock_reload, mock_systemctl
    ):
        mock_pkexec.return_value = (True, "")
        mock_reload.return_value = (True, "")
        mock_systemctl.return_value = (True, "")
        mock_run.return_value = MagicMock(code=0, out="var-swapfile.swap")

        res = persist_swap_unit("/var/swapfile")
        self.assertTrue(res.success)

        args, _ = mock_pkexec.call_args
        self.assertEqual(args[0], "/etc/systemd/system/var-swapfile.swap")
        self.assertTrue(mock_reload.called)
        systemctl_args, _ = mock_systemctl.call_args
        self.assertEqual(systemctl_args[0], "enable")
        self.assertEqual(systemctl_args[1], "var-swapfile.swap")

    @patch("core.hibernation.provisioner.run")
    def test_enable_swapon_success(self, mock_run):
        mock_run.return_value = MagicMock(code=0)
        self.assertTrue(enable_swapon("/swapfile", priority=0))

    @patch("core.hibernation.provisioner.run")
    def test_enable_swapon_failure(self, mock_run):
        from core.utils.common import SystemCommandError

        mock_run.side_effect = SystemCommandError(
            ["swapon"], 1, "", "permission denied"
        )
        self.assertFalse(enable_swapon("/swapfile"))

    @patch("core.hibernation.provisioner.run")
    def test_swapoff_swap_success(self, mock_run):
        mock_run.return_value = MagicMock(code=0)
        self.assertTrue(swapoff_swap("/swapfile"))

    @patch("core.hibernation.provisioner.swapoff_swap")
    @patch("core.hibernation.provisioner.pkexec_systemctl")
    @patch("core.hibernation.provisioner.pkexec_daemon_reload")
    @patch("os.path.exists")
    @patch("os.remove")
    def test_delete_swap_file(
        self, mock_remove, mock_exists, mock_reload, mock_systemctl, mock_swapoff
    ):
        mock_swapoff.return_value = True
        mock_exists.side_effect = lambda p: "/etc/systemd/system/test.swap" in p
        mock_systemctl.return_value = (True, "")
        mock_reload.return_value = (True, "")

        with patch("core.hibernation.provisioner.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.__truediv__ = lambda self, x: (
                f"/etc/systemd/system/{x}"
            )
            with patch(
                "core.hibernation.provisioner.is_block_device", return_value=False
            ):
                res = delete_swap("/swapfile")

        self.assertTrue(res.success)
        self.assertTrue(mock_swapoff.called)


if __name__ == "__main__":
    unittest.main()
