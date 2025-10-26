"""
Scene Description Module for VisionGuardian
Provides contextual descriptions of the environment
Optimized for Raspberry Pi 5
"""

import cv2
import numpy as np
import logging
import time
from typing import Dict, List, Optional

from utils import Config, MODELS_DIR


class SceneDescription:
    """Generates contextual scene descriptions"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.SceneDescription')

        # Settings
        self.enabled = config.get('scene_description.enabled', True)
        self.detail_level = config.get('scene_description.detail_level', 'medium')
        self.description_interval = config.get('scene_description.description_interval_seconds', 5)
        self.include_lighting = config.get('scene_description.include_lighting', True)
        self.include_location_type = config.get('scene_description.include_location_type', True)

        # Scene classifier model (if available)
        self.model = None

        # Tracking
        self.last_description_time = 0

        # Scene categories
        self.scene_categories = [
            'indoor', 'outdoor', 'street', 'building', 'office', 'home',
            'kitchen', 'bedroom', 'bathroom', 'living room', 'park', 'store'
        ]

    def initialize(self) -> bool:
        """
        Initialize scene description

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            self.logger.info("Initializing scene description...")

            # Load scene classification model (if available)
            # In production, load trained TFLite model here
            self.logger.info("Using heuristic-based scene description")

            self.logger.info("Scene description initialized")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing scene description: {e}")
            return False

    def describe_scene(self, frame: np.ndarray, objects: List[Dict] = None,
                      force: bool = False) -> Optional[str]:
        """
        Generate scene description

        Args:
            frame: Input frame
            objects: Detected objects (optional)
            force: Force description regardless of interval

        Returns:
            Scene description text
        """
        if not self.enabled:
            return None

        # Check interval
        current_time = time.time()
        if not force and (current_time - self.last_description_time < self.description_interval):
            return None

        try:
            description_parts = []

            # Analyze lighting
            if self.include_lighting:
                lighting = self._analyze_lighting(frame)
                description_parts.append(lighting)

            # Analyze scene type
            if self.include_location_type:
                location = self._analyze_location(frame, objects)
                if location:
                    description_parts.append(location)

            # Analyze composition
            composition = self._analyze_composition(frame)
            if composition:
                description_parts.append(composition)

            # Build description based on detail level
            if self.detail_level == 'low':
                description = description_parts[0] if description_parts else "Scene ahead"
            elif self.detail_level == 'high':
                description = ". ".join(description_parts)
            else:  # medium
                description = ". ".join(description_parts[:2])

            self.last_description_time = current_time
            return description

        except Exception as e:
            self.logger.error(f"Error describing scene: {e}")
            return None

    def _analyze_lighting(self, frame: np.ndarray) -> str:
        """
        Analyze lighting conditions

        Args:
            frame: Input frame

        Returns:
            Lighting description
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Calculate average brightness
        avg_brightness = np.mean(gray)

        if avg_brightness < 50:
            return "Dark environment"
        elif avg_brightness < 100:
            return "Dim lighting"
        elif avg_brightness < 180:
            return "Moderate lighting"
        else:
            return "Bright environment"

    def _analyze_location(self, frame: np.ndarray, objects: List[Dict] = None) -> Optional[str]:
        """
        Analyze location type based on objects and scene

        Args:
            frame: Input frame
            objects: Detected objects

        Returns:
            Location description
        """
        if not objects:
            return None

        # Analyze objects to infer location
        object_labels = [obj['label'] for obj in objects]

        # Indoor indicators
        indoor_objects = ['couch', 'bed', 'dining table', 'tv', 'refrigerator',
                         'oven', 'sink', 'toilet', 'chair', 'desk']
        indoor_count = sum(1 for obj in object_labels if obj in indoor_objects)

        # Outdoor indicators
        outdoor_objects = ['car', 'bicycle', 'tree', 'traffic light', 'stop sign',
                          'bus', 'truck', 'bench']
        outdoor_count = sum(1 for obj in object_labels if obj in outdoor_objects)

        if indoor_count > outdoor_count:
            # Try to identify specific room
            if 'bed' in object_labels:
                return "You appear to be in a bedroom"
            elif 'couch' in object_labels or 'tv' in object_labels:
                return "You appear to be in a living room"
            elif 'refrigerator' in object_labels or 'oven' in object_labels:
                return "You appear to be in a kitchen"
            else:
                return "You appear to be indoors"
        elif outdoor_count > indoor_count:
            if 'car' in object_labels or 'traffic light' in object_labels:
                return "You appear to be on a street"
            else:
                return "You appear to be outdoors"

        return None

    def _analyze_composition(self, frame: np.ndarray) -> Optional[str]:
        """
        Analyze scene composition

        Args:
            frame: Input frame

        Returns:
            Composition description
        """
        h, w = frame.shape[:2]

        # Analyze sky/ceiling (top third)
        top_region = frame[:h//3, :]
        top_brightness = np.mean(cv2.cvtColor(top_region, cv2.COLOR_BGR2GRAY))

        # Analyze ground/floor (bottom third)
        bottom_region = frame[2*h//3:, :]
        bottom_brightness = np.mean(cv2.cvtColor(bottom_region, cv2.COLOR_BGR2GRAY))

        # Analyze edges to detect structures
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        if edge_density > 0.15:
            return "Complex scene with many structures"
        elif edge_density > 0.08:
            return "Moderate scene complexity"
        else:
            return "Simple open scene"

    def get_detailed_description(self, frame: np.ndarray,
                                 faces: List[Dict] = None,
                                 objects: List[Dict] = None,
                                 text: str = None) -> str:
        """
        Generate comprehensive scene description

        Args:
            frame: Input frame
            faces: Detected faces
            objects: Detected objects
            text: Detected text

        Returns:
            Detailed description
        """
        parts = []

        # Basic scene description
        basic_desc = self.describe_scene(frame, objects, force=True)
        if basic_desc:
            parts.append(basic_desc)

        # People
        if faces:
            num_people = len(faces)
            known_people = [f['name'] for f in faces if f['is_known']]

            if known_people:
                if len(known_people) == 1:
                    parts.append(f"{known_people[0]} is present")
                else:
                    parts.append(f"{', '.join(known_people)} are present")

            unknown_count = num_people - len(known_people)
            if unknown_count > 0:
                parts.append(f"{unknown_count} unknown person{'s' if unknown_count > 1 else ''}")

        # Objects
        if objects:
            object_summary = self._summarize_objects(objects)
            if object_summary:
                parts.append(object_summary)

        # Text
        if text and text.strip():
            parts.append(f"Text visible: {text[:50]}")

        return ". ".join(parts) if parts else "No description available"

    def _summarize_objects(self, objects: List[Dict]) -> str:
        """Summarize detected objects"""
        if not objects:
            return ""

        # Group by label
        label_counts = {}
        for obj in objects[:5]:  # Top 5 objects
            label = obj['label']
            label_counts[label] = label_counts.get(label, 0) + 1

        # Format
        if len(label_counts) == 1:
            label, count = list(label_counts.items())[0]
            if count == 1:
                return f"A {label} is visible"
            else:
                return f"{count} {label}s are visible"
        else:
            items = []
            for label, count in list(label_counts.items())[:3]:
                if count == 1:
                    items.append(label)
                else:
                    items.append(f"{count} {label}s")
            return f"Visible objects: {', '.join(items)}"


if __name__ == "__main__":
    from utils import setup_logging
    setup_logging("INFO")

    config = Config()
    scene = SceneDescription(config)

    if scene.initialize():
        print("Scene description initialized")
    else:
        print("Failed to initialize scene description")
