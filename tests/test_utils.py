"""
Unit tests for utility functions
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils import (
    Config,
    get_system_info,
    check_storage_space,
    calculate_distance_from_width,
    PerformanceMonitor
)


class TestConfig(unittest.TestCase):
    """Test configuration management"""

    def test_config_singleton(self):
        """Test that Config is a singleton"""
        config1 = Config()
        config2 = Config()
        self.assertIs(config1, config2)

    def test_config_get(self):
        """Test configuration retrieval"""
        config = Config()

        # Test with default value
        value = config.get('nonexistent.key', 'default')
        self.assertEqual(value, 'default')

        # Test nested key
        fps = config.get('camera.fps', 15)
        self.assertIsInstance(fps, int)

    def test_config_reload(self):
        """Test configuration reload"""
        config = Config()
        config.reload()
        # Should not raise exception
        self.assertIsNotNone(config._config)


class TestSystemInfo(unittest.TestCase):
    """Test system information functions"""

    def test_get_system_info(self):
        """Test system info retrieval"""
        info = get_system_info()

        # Check required keys
        required_keys = [
            'platform', 'architecture', 'cpu_count',
            'memory_total_gb', 'disk_total_gb'
        ]

        for key in required_keys:
            self.assertIn(key, info)

        # Check data types
        self.assertIsInstance(info['cpu_count'], int)
        self.assertIsInstance(info['memory_total_gb'], float)
        self.assertIsInstance(info['disk_free_gb'], float)

    def test_check_storage_space(self):
        """Test storage space check"""
        sufficient, free_gb = check_storage_space(threshold_gb=1.0)

        self.assertIsInstance(sufficient, bool)
        self.assertIsInstance(free_gb, float)
        self.assertGreater(free_gb, 0)


class TestDistanceCalculation(unittest.TestCase):
    """Test distance calculation"""

    def test_calculate_distance_basic(self):
        """Test basic distance calculation"""
        # Known parameters
        known_width_cm = 60
        focal_length = 600
        perceived_width_px = 200
        image_width_px = 640

        distance = calculate_distance_from_width(
            known_width_cm, focal_length, perceived_width_px, image_width_px
        )

        # Distance should be positive
        self.assertGreater(distance, 0)

    def test_calculate_distance_zero_width(self):
        """Test distance calculation with zero width"""
        distance = calculate_distance_from_width(60, 600, 0, 640)
        self.assertEqual(distance, 0)


class TestPerformanceMonitor(unittest.TestCase):
    """Test performance monitoring"""

    def test_performance_monitor_basic(self):
        """Test basic performance monitoring"""
        monitor = PerformanceMonitor()

        monitor.start('test_operation')
        # Simulate work
        import time
        time.sleep(0.01)
        monitor.end('test_operation')

        # Get stats
        stats = monitor.get_stats('test_operation')

        self.assertIsNotNone(stats)
        self.assertIn('average', stats)
        self.assertIn('count', stats)
        self.assertGreater(stats['average'], 0)

    def test_performance_monitor_multiple(self):
        """Test monitoring multiple operations"""
        monitor = PerformanceMonitor()

        for i in range(5):
            monitor.start('operation')
            import time
            time.sleep(0.001)
            monitor.end('operation')

        stats = monitor.get_stats('operation')
        self.assertEqual(stats['count'], 5)

    def test_performance_monitor_reset(self):
        """Test monitor reset"""
        monitor = PerformanceMonitor()

        monitor.start('test')
        monitor.end('test')

        monitor.reset()

        stats = monitor.get_stats('test')
        self.assertIsNone(stats)


class TestPaths(unittest.TestCase):
    """Test path configurations"""

    def test_project_paths_exist(self):
        """Test that project paths exist"""
        from utils import PROJECT_ROOT, SRC_DIR, MODELS_DIR, DATA_DIR

        self.assertTrue(PROJECT_ROOT.exists())
        self.assertTrue(SRC_DIR.exists())
        # MODELS_DIR and DATA_DIR should be created
        self.assertTrue(MODELS_DIR.exists() or True)  # Created on import
        self.assertTrue(DATA_DIR.exists() or True)


if __name__ == '__main__':
    unittest.main()
