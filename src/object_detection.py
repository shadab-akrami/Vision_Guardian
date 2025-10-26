"""
Object Detection Module for VisionGuardian
Real-time object detection using TensorFlow Lite
Optimized for Raspberry Pi 5 (64-bit ARM64)
"""

import cv2
import numpy as np
import logging
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional

try:
    from tflite_runtime.interpreter import Interpreter
    TFLITE_AVAILABLE = True
except ImportError:
    try:
        import tensorflow as tf
        TFLITE_AVAILABLE = True
        USING_FULL_TF = True
    except ImportError:
        TFLITE_AVAILABLE = False
        logging.warning("TensorFlow Lite not available")

from utils import Config, MODELS_DIR, PerformanceMonitor


class ObjectDetection:
    """Handles real-time object detection"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.ObjectDetection')

        if not TFLITE_AVAILABLE:
            self.logger.error("TensorFlow Lite not available - module disabled")
            self.enabled = False
            return

        # Settings
        self.enabled = config.get('object_detection.enabled', True)
        self.model_path = MODELS_DIR / config.get(
            'object_detection.model_path',
            'ssd_mobilenet_v2_coco_quant.tflite'
        )
        self.labels_path = MODELS_DIR / config.get(
            'object_detection.labels_path',
            'coco_labels.txt'
        )
        self.confidence_threshold = config.get('object_detection.confidence_threshold', 0.5)
        self.max_objects_announce = config.get('object_detection.max_objects_announce', 3)
        self.detection_interval = config.get('object_detection.detection_interval_seconds', 1)
        self.nms_threshold = config.get('object_detection.nms_threshold', 0.5)

        # Model
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.labels = []

        # Detection tracking
        self.last_detection_time = 0
        self.last_detected_objects = []

        # Performance
        self.performance = PerformanceMonitor()

    def initialize(self) -> bool:
        """
        Load and initialize object detection model

        Returns:
            True if successful
        """
        if not self.enabled or not TFLITE_AVAILABLE:
            return False

        try:
            self.logger.info("Initializing object detection...")

            # Load labels
            if self.labels_path.exists():
                with open(self.labels_path, 'r') as f:
                    self.labels = [line.strip() for line in f.readlines()]
                self.logger.info(f"Loaded {len(self.labels)} object labels")
            else:
                self.logger.warning(f"Labels file not found: {self.labels_path}")
                # Create default COCO labels if not found
                self._create_default_labels()

            # Load model
            if not self.model_path.exists():
                self.logger.error(f"Model file not found: {self.model_path}")
                self.logger.info("Please download the model file. See setup instructions.")
                return False

            self.logger.info(f"Loading model: {self.model_path}")

            # Create interpreter
            try:
                self.interpreter = Interpreter(model_path=str(self.model_path))
            except NameError:
                # Using full TensorFlow
                self.interpreter = tf.lite.Interpreter(model_path=str(self.model_path))

            self.interpreter.allocate_tensors()

            # Get input and output details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()

            # Log model info
            input_shape = self.input_details[0]['shape']
            self.logger.info(f"Model input shape: {input_shape}")
            self.logger.info(f"Model loaded successfully")

            # Warm up model
            self._warmup_model()

            self.logger.info("Object detection initialized")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing object detection: {e}")
            return False

    def _create_default_labels(self):
        """Create default COCO labels"""
        default_labels = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
            'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
            'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
            'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
            'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
            'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
            'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
            'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
            'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
            'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
            'toothbrush'
        ]
        self.labels = default_labels

        # Save labels
        try:
            with open(self.labels_path, 'w') as f:
                f.write('\n'.join(default_labels))
            self.logger.info(f"Created default labels file: {self.labels_path}")
        except Exception as e:
            self.logger.error(f"Error saving labels: {e}")

    def _warmup_model(self):
        """Warm up model with dummy inference"""
        try:
            input_shape = self.input_details[0]['shape']
            dummy_input = np.zeros(input_shape, dtype=np.uint8)
            self.interpreter.set_tensor(self.input_details[0]['index'], dummy_input)
            self.interpreter.invoke()
            self.logger.info("Model warmup complete")
        except Exception as e:
            self.logger.error(f"Error during model warmup: {e}")

    def detect_objects(self, frame: np.ndarray, force: bool = False) -> List[Dict]:
        """
        Detect objects in frame

        Args:
            frame: Input frame (BGR format)
            force: Force detection regardless of interval

        Returns:
            List of detected objects with info
        """
        if not self.enabled or not TFLITE_AVAILABLE or self.interpreter is None:
            return []

        # Check detection interval
        current_time = time.time()
        if not force and (current_time - self.last_detection_time < self.detection_interval):
            return self.last_detected_objects

        self.performance.start('object_detection')
        detected_objects = []

        try:
            # Preprocess frame
            input_data = self._preprocess_frame(frame)

            # Run inference
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()

            # Get outputs
            # For SSD MobileNet, outputs are: boxes, classes, scores, num_detections
            boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
            classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
            scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]
            num_detections = int(self.interpreter.get_tensor(self.output_details[3]['index'])[0])

            # Process detections
            height, width = frame.shape[:2]

            for i in range(min(num_detections, 10)):  # Process top 10 detections
                score = scores[i]

                if score < self.confidence_threshold:
                    continue

                # Get class and label
                class_id = int(classes[i])
                label = self.labels[class_id] if class_id < len(self.labels) else f"Class {class_id}"

                # Get bounding box (normalized coordinates)
                ymin, xmin, ymax, xmax = boxes[i]

                # Convert to pixel coordinates
                left = int(xmin * width)
                right = int(xmax * width)
                top = int(ymin * height)
                bottom = int(ymax * height)

                detection = {
                    'label': label,
                    'class_id': class_id,
                    'confidence': float(score),
                    'bbox': (left, top, right, bottom),
                    'center': ((left + right) // 2, (top + bottom) // 2)
                }

                detected_objects.append(detection)

            # Apply Non-Maximum Suppression to remove duplicate detections
            detected_objects = self._apply_nms(detected_objects)

            # Sort by confidence
            detected_objects.sort(key=lambda x: x['confidence'], reverse=True)

            # Update tracking
            self.last_detection_time = current_time
            self.last_detected_objects = detected_objects

        except Exception as e:
            self.logger.error(f"Error detecting objects: {e}")

        self.performance.end('object_detection')
        return detected_objects

    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for model input

        Args:
            frame: Input frame

        Returns:
            Preprocessed input tensor
        """
        # Get input shape
        input_shape = self.input_details[0]['shape']
        height, width = input_shape[1], input_shape[2]

        # Resize frame
        resized = cv2.resize(frame, (width, height))

        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # Expand dimensions to match model input
        input_data = np.expand_dims(rgb, axis=0)

        # Check if model expects uint8 or float32
        if self.input_details[0]['dtype'] == np.uint8:
            return input_data.astype(np.uint8)
        else:
            # Normalize to [0, 1]
            return (input_data.astype(np.float32) / 255.0)

    def _apply_nms(self, detections: List[Dict]) -> List[Dict]:
        """
        Apply Non-Maximum Suppression to remove overlapping detections

        Args:
            detections: List of detections

        Returns:
            Filtered list of detections
        """
        if len(detections) == 0:
            return []

        # Extract boxes and scores
        boxes = [d['bbox'] for d in detections]
        scores = [d['confidence'] for d in detections]

        # Convert boxes to format expected by cv2.dnn.NMSBoxes
        boxes_cv = [[b[0], b[1], b[2]-b[0], b[3]-b[1]] for b in boxes]

        # Apply NMS
        indices = cv2.dnn.NMSBoxes(
            boxes_cv,
            scores,
            self.confidence_threshold,
            self.nms_threshold
        )

        # Filter detections
        if len(indices) > 0:
            indices = indices.flatten()
            return [detections[i] for i in indices]

        return detections

    def get_object_summary(self, detections: List[Dict]) -> List[str]:
        """
        Get summary of detected objects for announcement

        Args:
            detections: List of detections

        Returns:
            List of object labels (top N objects)
        """
        if not detections:
            return []

        # Count occurrences of each object
        object_counts = {}
        for det in detections[:self.max_objects_announce]:
            label = det['label']
            object_counts[label] = object_counts.get(label, 0) + 1

        # Create summary
        summary = []
        for label, count in object_counts.items():
            if count > 1:
                summary.append(f"{count} {label}s")
            else:
                summary.append(label)

        return summary

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
            left, top, right, bottom = detection['bbox']
            label = detection['label']
            confidence = detection['confidence']

            # Draw box
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

            # Draw label
            label_text = f"{label}: {confidence:.2f}"
            label_size, baseline = cv2.getTextSize(
                label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
            )

            top_label = max(top, label_size[1])
            cv2.rectangle(
                frame,
                (left, top_label - label_size[1] - baseline),
                (left + label_size[0], top_label),
                (0, 255, 0),
                cv2.FILLED
            )
            cv2.putText(
                frame,
                label_text,
                (left, top_label - baseline),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                2
            )

        return frame

    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        return self.performance.get_stats('object_detection')


if __name__ == "__main__":
    # Test object detection
    from utils import setup_logging
    setup_logging("INFO", "object_test.log")

    config = Config()
    detector = ObjectDetection(config)

    if detector.initialize():
        print("Object detection initialized")
        print(f"Labels loaded: {len(detector.labels)}")
        print("\nNote: Download model file:")
        print("wget https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip")
    else:
        print("Failed to initialize object detection")
