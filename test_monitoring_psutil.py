
import sys
import unittest
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from modules import monitoring

class TestMonitoringPsutil(unittest.TestCase):

    def test_watch_system_stats(self):
        # Create the generator with a short interval for testing
        gen = monitoring.watch_system_stats(interval=0.1)
        
        # Fetch a few samples
        samples = []
        for _ in range(3):
            stats = next(gen)
            samples.append(stats)
            
        self.assertEqual(len(samples), 3)
        
        for stats in samples:
            # Check types and ranges
            self.assertIsInstance(stats, monitoring.SystemStats)
            self.assertIsInstance(stats.cpu_percent, float)
            self.assertIsInstance(stats.memory_percent, float)
            self.assertIsInstance(stats.memory_used, int)
            self.assertIsInstance(stats.memory_total, int)
            
            self.assertGreaterEqual(stats.cpu_percent, 0.0)
            self.assertLessEqual(stats.cpu_percent, 100.0)
            
            self.assertGreaterEqual(stats.memory_percent, 0.0)
            self.assertLessEqual(stats.memory_percent, 100.0)
            
            self.assertGreater(stats.memory_total, 0)
            self.assertGreaterEqual(stats.memory_used, 0)
            self.assertLessEqual(stats.memory_used, stats.memory_total)

if __name__ == '__main__':
    unittest.main()
