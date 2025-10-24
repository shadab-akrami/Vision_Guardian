"""
Color Detection Module for VisionGuardian
Detects and announces colors of objects
Optimized for Raspberry Pi 5
"""

import cv2
import numpy as np
import logging
from typing import List, Tuple, Dict
import webcolors

from utils import Config


class ColorDetection:
    """Detects dominant colors in image regions"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.ColorDetection')

        self.enabled = config.get('color_detection.enabled', True)
        self.mode = config.get('color_detection.mode', 'dominant')
        self.num_colors = config.get('color_detection.num_colors', 3)
        self.announce_shade = config.get('color_detection.announce_shade', True)

    def get_dominant_color(self, image: np.ndarray, k: int = 3) -> List[Tuple[str, float]]:
        """
        Get dominant colors using K-means clustering

        Args:
            image: Input image region
            k: Number of dominant colors to find

        Returns:
            List of (color_name, percentage) tuples
        """
        if not self.enabled or image is None or image.size == 0:
            return []

        try:
            # Reshape image to be a list of pixels
            pixels = image.reshape(-1, 3).astype(np.float32)

            # Remove very dark pixels (likely shadows)
            brightness = np.mean(pixels, axis=1)
            pixels = pixels[brightness > 30]

            if len(pixels) == 0:
                return []

            # Apply K-means clustering
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
            _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_PP_CENTERS)

            # Count pixels in each cluster
            unique, counts = np.unique(labels, return_counts=True)
            total_pixels = len(labels)

            # Get color names and percentages
            colors = []
            for idx, count in zip(unique, counts):
                center = centers[idx]
                percentage = (count / total_pixels) * 100

                # Convert BGR to RGB
                rgb = tuple(reversed([int(c) for c in center]))

                # Get color name
                color_name = self._get_color_name(rgb)

                colors.append((color_name, percentage))

            # Sort by percentage
            colors.sort(key=lambda x: x[1], reverse=True)

            return colors[:self.num_colors]

        except Exception as e:
            self.logger.error(f"Error detecting colors: {e}")
            return []

    def _get_color_name(self, rgb: Tuple[int, int, int]) -> str:
        """
        Get closest color name for RGB value

        Args:
            rgb: RGB tuple

        Returns:
            Color name
        """
        try:
            # Try to get exact color name
            color_name = webcolors.rgb_to_name(rgb)
            return self._format_color_name(color_name)
        except ValueError:
            # Find closest color
            return self._closest_color_name(rgb)

    def _closest_color_name(self, rgb: Tuple[int, int, int]) -> str:
        """Find closest named color"""
        min_distance = float('inf')
        closest_name = 'unknown'

        for name in webcolors.names('css3'):
            try:
                name_rgb = webcolors.name_to_rgb(name)
                distance = sum((a - b) ** 2 for a, b in zip(rgb, name_rgb))

                if distance < min_distance:
                    min_distance = distance
                    closest_name = name
            except:
                continue

        return self._format_color_name(closest_name)

    def _format_color_name(self, name: str) -> str:
        """Format color name for announcement"""
        # Replace common CSS color names with more natural language
        replacements = {
            'darkblue': 'dark blue',
            'lightblue': 'light blue',
            'darkgreen': 'dark green',
            'lightgreen': 'light green',
            'darkred': 'dark red',
            'lightcoral': 'light red',
            'darkgray': 'dark gray',
            'lightgray': 'light gray',
            'darkorange': 'dark orange',
        }

        return replacements.get(name, name.replace('_', ' '))

    def detect_color_at_center(self, frame: np.ndarray) -> str:
        """
        Detect color at center of frame

        Args:
            frame: Input frame

        Returns:
            Color name
        """
        h, w = frame.shape[:2]
        center_region = frame[h//3:2*h//3, w//3:2*w//3]

        colors = self.get_dominant_color(center_region, k=1)

        if colors:
            return colors[0][0]
        return "unknown"

    def format_color_announcement(self, colors: List[Tuple[str, float]]) -> str:
        """
        Format colors for announcement

        Args:
            colors: List of (color, percentage) tuples

        Returns:
            Formatted announcement string
        """
        if not colors:
            return "No distinct colors detected"

        if len(colors) == 1:
            return f"The color is {colors[0][0]}"

        # Multiple colors
        color_names = [color[0] for color in colors]

        if len(color_names) == 2:
            return f"The colors are {color_names[0]} and {color_names[1]}"
        else:
            return f"The colors are {', '.join(color_names[:-1])}, and {color_names[-1]}"


if __name__ == "__main__":
    from utils import setup_logging
    setup_logging("INFO")

    config = Config()
    color_detector = ColorDetection(config)

    print("Color Detection Module initialized")
