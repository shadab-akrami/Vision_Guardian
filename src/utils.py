"""
Utility functions for VisionGuardian
Optimized for Raspberry Pi 5 (64-bit ARM64)
"""

import os
import yaml
import logging
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import numpy as np
import cv2
import psutil
import platform


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"
CACHE_DIR = PROJECT_ROOT / "cache"

# Ensure directories exist
for directory in [MODELS_DIR, DATA_DIR, LOGS_DIR, CACHE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


class Config:
    """Configuration manager for loading and accessing settings"""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load configuration from YAML file"""
        config_path = CONFIG_DIR / "settings.yaml"
        try:
            with open(config_path, 'r') as f:
                self._config = yaml.safe_load(f)
            logging.info(f"Configuration loaded from {config_path}")
        except FileNotFoundError:
            logging.error(f"Configuration file not found: {config_path}")
            self._config = {}
        except yaml.YAMLError as e:
            logging.error(f"Error parsing configuration: {e}")
            self._config = {}

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        Example: config.get('camera.resolution_width', 640)
        """
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default

        return value if value is not None else default

    def reload(self):
        """Reload configuration from file"""
        self._load_config()


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Setup logging configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path

    Returns:
        Logger instance
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Setup handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # File handler
    if log_file:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOGS_DIR / log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=handlers,
        format=log_format
    )

    return logging.getLogger('VisionGuardian')


def get_system_info() -> Dict[str, Any]:
    """
    Get system information for Raspberry Pi 5

    Returns:
        Dictionary with system information
    """
    info = {
        'platform': platform.system(),
        'platform_release': platform.release(),
        'platform_version': platform.version(),
        'architecture': platform.machine(),
        'processor': platform.processor(),
        'cpu_count': psutil.cpu_count(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
        'memory_available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_total_gb': round(psutil.disk_usage('/').total / (1024**3), 2),
        'disk_used_gb': round(psutil.disk_usage('/').used / (1024**3), 2),
        'disk_free_gb': round(psutil.disk_usage('/').free / (1024**3), 2),
        'disk_percent': psutil.disk_usage('/').percent,
    }

    return info


def check_storage_space(threshold_gb: float = 5.0) -> Tuple[bool, float]:
    """
    Check available storage space

    Args:
        threshold_gb: Minimum required free space in GB

    Returns:
        Tuple of (is_sufficient, free_gb)
    """
    disk = psutil.disk_usage('/')
    free_gb = disk.free / (1024**3)
    return (free_gb >= threshold_gb, free_gb)


def check_raspberry_pi5() -> bool:
    """
    Check if running on Raspberry Pi 5 with 64-bit OS

    Returns:
        True if running on compatible system
    """
    try:
        # Check architecture
        arch = platform.machine()
        if arch != 'aarch64':
            logging.warning(f"Not running on 64-bit ARM architecture (detected: {arch})")
            return False

        # Check if it's a Raspberry Pi
        try:
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read()
                if 'Raspberry Pi 5' in model:
                    logging.info(f"Detected: {model.strip()}")
                    return True
                else:
                    logging.warning(f"Not Raspberry Pi 5 (detected: {model.strip()})")
        except FileNotFoundError:
            logging.warning("Could not detect Raspberry Pi model")
    except Exception as e:
        logging.error(f"Error checking Raspberry Pi: {e}")

    return False


def preprocess_image(image: np.ndarray, target_size: Optional[Tuple[int, int]] = None,
                     enhance: bool = True) -> np.ndarray:
    """
    Preprocess image for better detection results

    Args:
        image: Input image
        target_size: Optional resize target (width, height)
        enhance: Whether to enhance image quality

    Returns:
        Preprocessed image
    """
    if target_size:
        image = cv2.resize(image, target_size)

    if enhance:
        # Enhance contrast
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        image = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    return image


def calculate_distance_from_width(known_width_cm: float, focal_length: float,
                                   perceived_width_px: int, image_width_px: int) -> float:
    """
    Calculate distance to object using perceived width

    Args:
        known_width_cm: Actual width of object in cm
        focal_length: Camera focal length (calibrated)
        perceived_width_px: Width of object in pixels
        image_width_px: Total image width in pixels

    Returns:
        Distance in centimeters
    """
    if perceived_width_px == 0:
        return 0

    # Calculate distance using similar triangles
    distance = (known_width_cm * focal_length) / perceived_width_px
    return distance


def draw_text_with_background(image: np.ndarray, text: str, position: Tuple[int, int],
                               font_scale: float = 0.6, thickness: int = 2,
                               text_color: Tuple[int, int, int] = (255, 255, 255),
                               bg_color: Tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
    """
    Draw text with background on image

    Args:
        image: Input image
        text: Text to draw
        position: (x, y) position
        font_scale: Font scale
        thickness: Text thickness
        text_color: Text color (B, G, R)
        bg_color: Background color (B, G, R)

    Returns:
        Image with text drawn
    """
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Get text size
    (text_width, text_height), baseline = cv2.getTextSize(
        text, font, font_scale, thickness
    )

    x, y = position

    # Draw background rectangle
    cv2.rectangle(
        image,
        (x, y - text_height - baseline),
        (x + text_width, y + baseline),
        bg_color,
        -1
    )

    # Draw text
    cv2.putText(
        image,
        text,
        (x, y),
        font,
        font_scale,
        text_color,
        thickness,
        cv2.LINE_AA
    )

    return image


def fps_counter():
    """
    Generator for calculating FPS

    Yields:
        Current FPS
    """
    frame_count = 0
    start_time = time.time()

    while True:
        frame_count += 1
        elapsed = time.time() - start_time

        if elapsed > 1.0:
            fps = frame_count / elapsed
            frame_count = 0
            start_time = time.time()
            yield fps
        else:
            yield 0


class PerformanceMonitor:
    """Monitor performance metrics"""

    def __init__(self):
        self.metrics = {}
        self.start_times = {}

    def start(self, name: str):
        """Start timing a metric"""
        self.start_times[name] = time.time()

    def end(self, name: str):
        """End timing a metric and store the duration"""
        if name in self.start_times:
            duration = time.time() - self.start_times[name]
            if name not in self.metrics:
                self.metrics[name] = []
            self.metrics[name].append(duration)
            del self.start_times[name]

    def get_average(self, name: str) -> Optional[float]:
        """Get average time for a metric"""
        if name in self.metrics and len(self.metrics[name]) > 0:
            return sum(self.metrics[name]) / len(self.metrics[name])
        return None

    def get_stats(self, name: str) -> Optional[Dict[str, float]]:
        """Get statistics for a metric"""
        if name not in self.metrics or len(self.metrics[name]) == 0:
            return None

        values = self.metrics[name]
        return {
            'count': len(values),
            'average': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'latest': values[-1]
        }

    def reset(self):
        """Reset all metrics"""
        self.metrics = {}
        self.start_times = {}

    def get_report(self) -> Dict[str, Dict[str, float]]:
        """Get full performance report"""
        report = {}
        for name in self.metrics:
            report[name] = self.get_stats(name)
        return report


def save_json(data: Dict, filepath: Path):
    """Save data to JSON file"""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def load_json(filepath: Path) -> Optional[Dict]:
    """Load data from JSON file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading JSON from {filepath}: {e}")
        return None


def get_timestamp() -> str:
    """Get current timestamp string"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_readable_timestamp() -> str:
    """Get human-readable timestamp"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    # Test utilities
    print("VisionGuardian Utilities Test")
    print("=" * 50)

    # Test system info
    print("\nSystem Information:")
    info = get_system_info()
    for key, value in info.items():
        print(f"  {key}: {value}")

    # Test Raspberry Pi check
    print(f"\nRaspberry Pi 5 Check: {check_raspberry_pi5()}")

    # Test storage check
    sufficient, free_gb = check_storage_space()
    print(f"\nStorage Check: {'OK' if sufficient else 'WARNING'}")
    print(f"  Free space: {free_gb:.2f} GB")

    # Test config
    config = Config()
    print(f"\nCamera Resolution: {config.get('camera.resolution_width')}x{config.get('camera.resolution_height')}")
    print(f"Audio Engine: {config.get('audio.engine')}")
    print(f"Debug Mode: {config.get('system.debug_mode')}")
