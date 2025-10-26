"""
Obstacle Detection Module for VisionGuardian
Detects obstacles and estimates distances for navigation safety
Optimized for Raspberry Pi 5
"""

import cv2
import numpy as np
import logging
import time
from typing import List, Dict, Tuple, Optional

from utils import Config, MODELS_DIR, PerformanceMonitor


class ObstacleDetection:
    """Detects obstacles and estimates distances"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.ObstacleDetection')

        # Settings
        self.enabled = config.get('obstacle_detection.enabled', True)
        self.min_distance = config.get('obstacle_detection.min_distance_cm', 150)
        self.warning_distance = config.get('obstacle_detection.warning_distance_cm', 100)
        self.detection_zones = config.get('obstacle_detection.detection_zones', 3)
        self.alert_interval = config.get('obstacle_detection.alert_interval_seconds', 2)
        self.use_depth = config.get('obstacle_detection.use_depth_estimation', True)

        # Depth estimation model (if available)
        self.depth_model = None

        # Zone tracking
        self.last_alert_time = {}
        self.zone_names = ['left', 'center', 'right']

        # Camera calibration (should be calibrated for specific camera)
        self.focal_length = 600  # pixels (approximate, needs calibration)
        self.known_width = 60    # cm (average person width)

        # Performance
        self.performance = PerformanceMonitor()

    def initialize(self) -> bool:
        """
        Initialize obstacle detection

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            self.logger.info("Initializing obstacle detection...")

            # Try to load depth estimation model if enabled
            if self.use_depth:
                try:
                    self._load_depth_model()
                except Exception as e:
                    self.logger.warning(f"Could not load depth model: {e}")
                    self.use_depth = False

            self.logger.info("Obstacle detection initialized")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing obstacle detection: {e}")
            return False

    def _load_depth_model(self):
        """Load depth estimation model (MiDaS or similar)"""
        # Placeholder for depth model loading
        # In production, load MiDaS TFLite model here
        self.logger.info("Depth estimation not yet implemented")
        pass

    def detect_obstacles(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect obstacles in frame

        Args:
            frame: Input frame

        Returns:
            List of obstacle detections with distances
        """
        if not self.enabled:
            return []

        self.performance.start('obstacle_detection')
        obstacles = []

        try:
            # Simple obstacle detection using edge detection and contours
            obstacles = self._detect_using_contours(frame)

            # Filter by distance threshold
            obstacles = [obs for obs in obstacles if obs['distance'] <= self.min_distance]

            # Sort by distance (closest first)
            obstacles.sort(key=lambda x: x['distance'])

        except Exception as e:
            self.logger.error(f"Error detecting obstacles: {e}")

        self.performance.end('obstacle_detection')
        return obstacles

    def _detect_using_contours(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect obstacles using edge detection and contours

        Args:
            frame: Input frame

        Returns:
            List of obstacles
        """
        h, w = frame.shape[:2]
        obstacles = []

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)

        # Dilate edges to close gaps
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Divide frame into zones
        zone_width = w // self.detection_zones

        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by minimum area
            if area < 1000:
                continue

            # Get bounding box
            x, y, width, height = cv2.boundingRect(contour)

            # Determine zone
            zone_idx = min(x // zone_width, self.detection_zones - 1)
            zone = self.zone_names[zone_idx] if zone_idx < len(self.zone_names) else 'center'

            # Estimate distance based on object width
            if width > 0:
                distance = self._estimate_distance(width, w)
            else:
                distance = 999  # Unknown distance

            # Check if in lower half of frame (more likely to be an obstacle in path)
            in_path = y > h // 3

            obstacle = {
                'bbox': (x, y, x + width, y + height),
                'center': (x + width // 2, y + height // 2),
                'zone': zone,
                'distance': distance,
                'width': width,
                'height': height,
                'in_path': in_path,
                'severity': 'critical' if distance < self.warning_distance else 'warning'
            }

            obstacles.append(obstacle)

        return obstacles

    def _estimate_distance(self, perceived_width: int, image_width: int) -> float:
        """
        Estimate distance to obstacle using pinhole camera model

        Args:
            perceived_width: Width of object in pixels
            image_width: Total image width

        Returns:
            Estimated distance in cm
        """
        if perceived_width == 0:
            return 999

        # Simple distance estimation (needs camera calibration for accuracy)
        distance = (self.known_width * self.focal_length) / perceived_width

        # Clamp to reasonable range
        distance = max(10, min(distance, 500))

        return distance

    def get_alerts(self, obstacles: List[Dict]) -> List[Dict]:
        """
        Get obstacle alerts that should be announced

        Args:
            obstacles: List of detected obstacles

        Returns:
            List of obstacles that need alerts
        """
        current_time = time.time()
        alerts = []

        for obstacle in obstacles:
            zone = obstacle['zone']

            # Check if enough time has passed since last alert for this zone
            if zone in self.last_alert_time:
                if current_time - self.last_alert_time[zone] < self.alert_interval:
                    continue

            # Check if obstacle is in path and within warning distance
            if obstacle['in_path'] and obstacle['distance'] <= self.min_distance:
                alerts.append(obstacle)
                self.last_alert_time[zone] = current_time

        return alerts

    def format_alert(self, obstacle: Dict) -> str:
        """
        Format obstacle alert for announcement

        Args:
            obstacle: Obstacle dictionary

        Returns:
            Alert text
        """
        zone = obstacle['zone']
        distance = obstacle['distance']
        severity = obstacle['severity']

        if severity == 'critical':
            return f"Warning! Obstacle {zone}, {distance:.0f} centimeters"
        else:
            return f"Obstacle {zone}, {distance:.0f} centimeters"

    def draw_obstacles(self, frame: np.ndarray, obstacles: List[Dict]) -> np.ndarray:
        """
        Draw obstacle markers on frame

        Args:
            frame: Input frame
            obstacles: List of obstacles

        Returns:
            Frame with obstacles drawn
        """
        h, w = frame.shape[:2]

        # Draw zones
        zone_width = w // self.detection_zones
        for i in range(1, self.detection_zones):
            x = i * zone_width
            cv2.line(frame, (x, 0), (x, h), (100, 100, 100), 1)

        # Draw obstacles
        for obstacle in obstacles:
            x1, y1, x2, y2 = obstacle['bbox']
            zone = obstacle['zone']
            distance = obstacle['distance']

            # Color based on severity
            if obstacle['severity'] == 'critical':
                color = (0, 0, 255)  # Red
            else:
                color = (0, 255, 255)  # Yellow

            # Draw box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Draw distance label
            label = f"{zone}: {distance:.0f}cm"
            cv2.putText(frame, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return frame

    def calibrate_camera(self, known_distance_cm: float, measured_width_px: int):
        """
        Calibrate camera focal length using known distance

        Args:
            known_distance_cm: Known distance to object
            measured_width_px: Measured width of object in pixels
        """
        self.focal_length = (measured_width_px * known_distance_cm) / self.known_width
        self.logger.info(f"Camera calibrated: focal length = {self.focal_length}")

    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        return self.performance.get_stats('obstacle_detection')


if __name__ == "__main__":
    from utils import setup_logging
    setup_logging("INFO")

    config = Config()
    detector = ObstacleDetection(config)

    if detector.initialize():
        print("Obstacle detection initialized")
    else:
        print("Failed to initialize obstacle detection")
