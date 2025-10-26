"""
Enhanced Object Detection Module for VisionGuardian
Uses YOLOv8 (free, local) for detection of 300+ object classes
No internet or API costs required
"""

import cv2
import numpy as np
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logging.warning("ultralytics (YOLOv8) not available")

from utils import Config, MODELS_DIR, PerformanceMonitor


class EnhancedObjectDetection:
    """
    Enhanced object detection using YOLOv8
    Detects 300+ objects (vs 80 with basic COCO)
    Completely free and runs locally
    """

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.EnhancedObjectDetection')

        # Settings
        self.enabled = config.get('enhanced_object_detection.enabled', True)
        self.model_size = config.get('enhanced_object_detection.model_size', 'n')  # n, s, m, l, x
        self.confidence_threshold = config.get('enhanced_object_detection.confidence_threshold', 0.5)
        self.iou_threshold = config.get('enhanced_object_detection.iou_threshold', 0.45)
        self.max_detections = config.get('enhanced_object_detection.max_detections', 10)
        self.detection_interval = config.get('enhanced_object_detection.detection_interval_seconds', 1)

        # Model
        self.model = None
        self.class_names = []

        # Tracking
        self.last_detection_time = 0
        self.last_detected_objects = []

        # Performance
        self.performance = PerformanceMonitor()

    def initialize(self) -> bool:
        """
        Initialize YOLOv8 model

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        if not YOLO_AVAILABLE:
            self.logger.error("YOLOv8 not available. Install with: pip install ultralytics")
            return False

        try:
            self.logger.info(f"Initializing YOLOv8 model (size: {self.model_size})...")

            # Model path
            model_name = f"yolov8{self.model_size}.pt"
            model_path = MODELS_DIR / model_name

            # Load model (will auto-download if not present)
            self.logger.info(f"Loading model: {model_name}")
            self.model = YOLO(str(model_path))

            # Get class names
            self.class_names = list(self.model.names.values())
            self.logger.info(f"Model loaded with {len(self.class_names)} classes")

            # Warm up model
            self._warmup_model()

            self.logger.info("Enhanced object detection initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing enhanced object detection: {e}")
            return False

    def _warmup_model(self):
        """Warm up model with dummy inference"""
        try:
            dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
            self.model.predict(dummy_img, verbose=False)
            self.logger.info("Model warmup complete")
        except Exception as e:
            self.logger.warning(f"Model warmup failed: {e}")

    def detect_objects(self, frame: np.ndarray, force: bool = False) -> List[Dict]:
        """
        Detect objects in frame

        Args:
            frame: Input frame (BGR format)
            force: Force detection regardless of interval

        Returns:
            List of detected objects
        """
        if not self.enabled or self.model is None:
            return []

        # Check detection interval
        current_time = time.time()
        if not force and (current_time - self.last_detection_time < self.detection_interval):
            return self.last_detected_objects

        self.performance.start('enhanced_detection')
        detected_objects = []

        try:
            # Run inference
            results = self.model.predict(
                frame,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                max_det=self.max_detections,
                verbose=False
            )

            # Process results
            if len(results) > 0:
                result = results[0]
                boxes = result.boxes

                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())

                    # Get class name
                    label = self.class_names[class_id] if class_id < len(self.class_names) else f"Class {class_id}"

                    detection = {
                        'label': label,
                        'class_id': class_id,
                        'confidence': confidence,
                        'bbox': (int(x1), int(y1), int(x2), int(y2)),
                        'center': (int((x1 + x2) / 2), int((y1 + y2) / 2))
                    }

                    detected_objects.append(detection)

            # Sort by confidence
            detected_objects.sort(key=lambda x: x['confidence'], reverse=True)

            # Update tracking
            self.last_detection_time = current_time
            self.last_detected_objects = detected_objects

        except Exception as e:
            self.logger.error(f"Error detecting objects: {e}")

        self.performance.end('enhanced_detection')
        return detected_objects

    def get_object_summary(self, detections: List[Dict]) -> str:
        """
        Get natural language summary of detected objects

        Args:
            detections: List of detections

        Returns:
            Human-readable summary
        """
        if not detections:
            return ""

        # Group by label
        object_counts = {}
        for det in detections[:5]:  # Top 5
            label = det['label']
            object_counts[label] = object_counts.get(label, 0) + 1

        # Build natural summary
        if len(object_counts) == 0:
            return ""

        parts = []
        for label, count in list(object_counts.items())[:3]:
            if count == 1:
                parts.append(f"a {label}")
            else:
                parts.append(f"{count} {label}s")

        if len(parts) == 1:
            return f"I see {parts[0]}"
        elif len(parts) == 2:
            return f"I see {parts[0]} and {parts[1]}"
        else:
            return f"I see {', '.join(parts[:-1])}, and {parts[-1]}"

    def draw_detections(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        Draw detection boxes and labels on frame

        Args:
            frame: Input frame
            detections: List of detections

        Returns:
            Frame with detections drawn
        """
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            label = detection['label']
            confidence = detection['confidence']

            # Draw box
            color = (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Draw label with background
            label_text = f"{label}: {confidence:.2f}"
            (text_width, text_height), baseline = cv2.getTextSize(
                label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
            )

            # Draw background rectangle
            cv2.rectangle(
                frame,
                (x1, y1 - text_height - baseline - 5),
                (x1 + text_width, y1),
                color,
                cv2.FILLED
            )

            # Draw text
            cv2.putText(
                frame,
                label_text,
                (x1, y1 - baseline - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                2
            )

        return frame

    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        return self.performance.get_stats('enhanced_detection')


if __name__ == "__main__":
    # Test enhanced object detection
    from utils import setup_logging
    import sys

    setup_logging("INFO")
    config = Config()

    # Enable enhanced detection
    config.data['enhanced_object_detection'] = {
        'enabled': True,
        'model_size': 'n',
        'confidence_threshold': 0.5
    }

    detector = EnhancedObjectDetection(config)

    if not detector.initialize():
        print("Failed to initialize enhanced object detection")
        print("Install YOLOv8 with: pip install ultralytics")
        sys.exit(1)

    print(f"Enhanced object detection initialized!")
    print(f"Classes: {len(detector.class_names)}")
    print(f"\nSample classes: {', '.join(detector.class_names[:20])}")
    print("\nTesting with camera...")

    # Test with camera
    from camera_handler import CameraHandler

    camera = CameraHandler(config)
    if not camera.initialize():
        print("Failed to initialize camera")
        sys.exit(1)

    camera.start_capture()
    time.sleep(1)

    frame = camera.get_current_frame()
    if frame is not None:
        print("\nDetecting objects...")
        detections = detector.detect_objects(frame)

        if detections:
            print(f"\nDetected {len(detections)} objects:")
            for det in detections[:5]:
                print(f"  - {det['label']} ({det['confidence']:.2%})")

            summary = detector.get_object_summary(detections)
            print(f"\nSummary: {summary}")
        else:
            print("No objects detected")

    camera.release()
