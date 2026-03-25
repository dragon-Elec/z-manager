from unittest.mock import patch, MagicMock
from pathlib import Path
from tests.test_base import *
from core import boot_config


class TestSysctlTuning(BaseTestCase):
    @patch("core.boot_config.read_file")
    @patch("core.boot_config.atomic_write_to_file")
    @patch("core.boot_config.run")
    @patch("pathlib.Path.exists")
    def test_apply_sysctl_values_success(
        self, mock_exists, mock_run, mock_write, mock_read
    ):
        with (
            patch("core.utils.io.pkexec_write", return_value=(True, None)) as m_write,
            patch(
                "core.utils.privilege.pkexec_sysctl_system", return_value=(True, None)
            ) as m_sysctl,
        ):
            mock_read.return_value = (
                "vm.swappiness = 60\n# comment\nvm.page-cluster = 3"
            )
            mock_write.return_value = (True, None)
            mock_exists.return_value = True

            settings = {"vm.swappiness": "100", "vm.vfs_cache_pressure": "50"}
            result = boot_config.apply_sysctl_values(settings)

            self.assertTrue(result.success)
            self.assertTrue(result.changed)
            self.assertTrue(m_write.called)

    def test_apply_sysctl_values_permission_denied(self):
        with (
            patch("core.boot_config.read_file", return_value="vm.swappiness=60"),
            patch("pathlib.Path.exists", return_value=True),
            patch("core.boot_config.atomic_write_to_file") as mock_write,
            patch(
                "core.utils.io.pkexec_write", return_value=(False, "Permission denied")
            ),
            patch(
                "core.utils.privilege.pkexec_sysctl_system", return_value=(True, None)
            ),
        ):
            settings = {"vm.swappiness": "100"}
            result = boot_config.apply_sysctl_values(settings)

            self.assertFalse(result.success)
            self.assertIn("Permission denied", result.message)
            self.assertFalse(result.changed)
            self.assertFalse(mock_write.called)

    @patch("core.boot_config.read_file")
    @patch("pathlib.Path.exists")
    def test_apply_sysctl_values_no_change(self, mock_exists, mock_read):
        mock_read.return_value = (
            "# Custom Z-Manager Tuning Configuration\nvm.swappiness = 100\n"
        )
        mock_exists.return_value = True

        settings = {"vm.swappiness": "100"}
        result = boot_config.apply_sysctl_values(settings)

        self.assertTrue(result.success)
        self.assertFalse(result.changed)


if __name__ == "__main__":
    unittest.main()
