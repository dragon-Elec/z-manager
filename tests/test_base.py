import unittest
from unittest.mock import patch, MagicMock, mock_open

__all__ = ['BaseTestCase', 'patch', 'MagicMock', 'mock_open', 'unittest']

class BaseTestCase(unittest.TestCase):
    """
    Base class for all z-manager unit tests.
    Provides common mocking utilities and zram-specific assertions.
    """

    def setUp(self):
        super().setUp()
        # Common patches could be added here if they should apply to ALL tests
        # For now, we provide helper methods to apply them selectively.
        pass

    def mock_system_calls(self, read_data=None, run_result=None):
        """ Helper to mock common os_utils functions in one go. """
        patchers = []
        
        if read_data is not None:
            p = patch('core.os_utils.read_file', return_value=read_data)
            patchers.append(p)
            self.mock_read = p.start()
            
        if run_result is not None:
            p = patch('core.os_utils.run', return_value=MagicMock(code=0, out=run_result if isinstance(run_result, str) else ""))
            patchers.append(p)
            self.mock_run = p.start()

        def cleanup():
            for p in patchers:
                p.stop()
        self.addCleanup(cleanup)

    # Custom Assertions
    def assertDeviceActive(self, device_name):
        from core.zdevice_ctl import is_device_active
        self.assertTrue(is_device_active(device_name), f"Expected zram device '{device_name}' to be active/swapon.")

    def assertValidSize(self, size_str):
        from core.os_utils import parse_size_to_bytes
        self.assertGreater(parse_size_to_bytes(size_str), 0, f"Invalid zram size string: '{size_str}'")

    def assertAlgorithm(self, device, expected):
        # This would be for integration tests mostly
        pass
