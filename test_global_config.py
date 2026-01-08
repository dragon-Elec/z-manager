
import unittest
from core.config import read_global_config
from core.config_writer import update_global_config

# Mock read_zram_config to avoid reading real files
from unittest.mock import patch, MagicMock
from configobj import ConfigObj

class TestGlobalConfig(unittest.TestCase):
    
    @patch('core.config.read_zram_config')
    @patch('core.config_writer.read_zram_config')
    def test_global_config_read_write(self, mock_read_writer, mock_read_reader):
        # Setup Mock Config
        mock_cfg = ConfigObj()
        mock_cfg['zram-generator'] = {'conf-file': '/foo/bar'}
        mock_cfg['zram0'] = {'zram-size': 'ram'}
        
        mock_read_reader.return_value = mock_cfg
        mock_read_writer.return_value = mock_cfg
        
        # Test Read
        global_conf = read_global_config()
        self.assertEqual(global_conf['conf-file'], '/foo/bar')
        self.assertNotIn('zram0', global_conf)
        
        # Test Write
        success, err, rendered = update_global_config({'compression-algorithm': 'lz4'})
        self.assertTrue(success)
        self.assertIn('[zram-generator]', rendered)
        self.assertIn('compression-algorithm = lz4', rendered)
        # Should preserve existing
        self.assertIn('conf-file = /foo/bar', rendered)

if __name__ == '__main__':
    unittest.main()
