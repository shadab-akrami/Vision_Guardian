"""
Camera Handler for VisionGuardian
Manages webcam capture and frame processing
Optimized for Raspberry Pi 5
"""

import cv2
import numpy as np
import logging
import threading
import time
from queue import Queue, Empty
from typing import Optional, Tuple, Callable

from utils import Config, PerformanceMonitor


class CameraHandler:
    """Handles camera operations with threading for optimal performance"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.CameraHandler')

        # Camera settings
        self.device_id = config.get('camera.device_id', 0)
        self.resolution_width = config.get('camera.resolution_width', 640)
        self.resolution_height = config.get('camera.resolution_height', 480)
        self.target_fps = config.get('camera.fps', 15)
        self.rotation = config.get('camera.rotation', 0)
        self.flip_horizontal = config.get('camera.flip_horizontal', False)
        self.flip_vertical = config.get('camera.flip_vertical', False)

        # Camera object
        self.camera = None
        self.is_running = False

        # Threading
        self.capture_thread = None
        self.frame_queue = Queue(maxsize=2)  # Small queue to avoid lag

        # Frame management
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.frame_count = 0

        # Performance monitoring
        self.performance = PerformanceMonitor()
        self.fps = 0
        self.last_fps_time = time.time()

    def initialize(self) -> bool:
        """
        Initialize camera

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Initializing camera {self.device_id}...")

            # Try different backends for Raspberry Pi
            backends = [cv2.CAP_V4L2, cv2.CAP_ANY]

            for backend in backends:
                self.camera = cv2.VideoCapture(self.device_id, backend)
                if self.camera.isOpened():
                    self.logger.info(f"Camera opened with backend: {backend}")
                    break

            if not self.camera or not self.camera.isOpened():
                self.logger.error("Failed to open camera")
                return False

            # Set camera properties
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution_height)
            self.camera.set(cv2.CAP_PROP_FPS, self.target_fps)

            # Enable auto settings
            if self.config.get('camera.auto_focus', True):
                self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)

            # Set brightness and contrast
            brightness = self.config.get('camera.brightness', 50)
            contrast = self.config.get('camera.contrast', 50)
            self.camera.set(cv2.CAP_PROP_BRIGHTNESS, brightness / 100.0)
            self.camera.set(cv2.CAP_PROP_CONTRAST, contrast / 100.0)

            # Verify settings
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.camera.get(cv2.CAP_PROP_FPS))

            self.logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps} FPS")

            # Warm up camera
            for _ in range(10):
                self.camera.read()

            self.logger.info("Camera ready")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing camera: {e}")
            return False

    def start_capture(self) -> bool:
        """
        Start continuous frame capture in background thread

        Returns:
            True if started successfully
        """
        if self.is_running:
            self.logger.warning("Capture already running")
            return True

        if not self.camera or not self.camera.isOpened():
            self.logger.error("Camera not initialized")
            return False

        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

        self.logger.info("Capture thread started")
        return True

    def stop_capture(self):
        """Stop frame capture"""
        self.is_running = False

        if self.capture_thread:
            self.capture_thread.join(timeout=2)
            self.capture_thread = None

        self.logger.info("Capture stopped")

    def _capture_loop(self):
        """Main capture loop running in background thread"""
        frame_interval = 1.0 / self.target_fps
        last_capture_time = time.time()

        while self.is_running:
            try:
                current_time = time.time()

                # Rate limiting
                if current_time - last_capture_time < frame_interval:
                    time.sleep(0.001)
                    continue

                self.performance.start('frame_capture')

                # Capture frame
                ret, frame = self.camera.read()

                if not ret or frame is None:
                    self.logger.warning("Failed to capture frame")
                    time.sleep(0.1)
                    continue

                # Process frame
                frame = self._process_frame(frame)

                # Update current frame
                with self.frame_lock:
                    self.current_frame = frame
                    self.frame_count += 1

                # Update queue (non-blocking)
                try:
                    if self.frame_queue.full():
                        self.frame_queue.get_nowait()  # Remove old frame
                    self.frame_queue.put_nowait(frame)
                except:
                    pass

                self.performance.end('frame_capture')

                # Calculate FPS
                if current_time - self.last_fps_time >= 1.0:
                    self.fps = self.frame_count / (current_time - self.last_fps_time)
                    self.frame_count = 0
                    self.last_fps_time = current_time

                last_capture_time = current_time

            except Exception as e:
                self.logger.error(f"Error in capture loop: {e}")
                time.sleep(0.1)

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Process frame (rotation, flipping, etc.)

        Args:
            frame: Raw frame from camera

        Returns:
            Processed frame
        """
        # Apply rotation
        if self.rotation == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif self.rotation == 270:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # Apply flipping
        if self.flip_horizontal and self.flip_vertical:
            frame = cv2.flip(frame, -1)
        elif self.flip_horizontal:
            frame = cv2.flip(frame, 1)
        elif self.flip_vertical:
            frame = cv2.flip(frame, 0)

        return frame

    def get_frame(self, timeout: float = 0.5) -> Optional[np.ndarray]:
        """
        Get latest frame from queue

        Args:
            timeout: Timeout in seconds

        Returns:
            Frame or None if timeout
        """
        try:
            return self.frame_queue.get(timeout=timeout)
        except Empty:
            return None

    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Get current frame (no waiting)

        Returns:
            Current frame or None
        """
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read a single frame (compatible with cv2.VideoCapture interface)

        Returns:
            Tuple of (success, frame)
        """
        frame = self.get_current_frame()
        return (frame is not None, frame)

    def get_fps(self) -> float:
        """Get current FPS"""
        return self.fps

    def get_resolution(self) -> Tuple[int, int]:
        """Get current resolution (width, height)"""
        return (self.resolution_width, self.resolution_height)

    def take_snapshot(self, filepath: str) -> bool:
        """
        Save current frame to file

        Args:
            filepath: Path to save image

        Returns:
            True if successful
        """
        frame = self.get_current_frame()
        if frame is not None:
            try:
                cv2.imwrite(filepath, frame)
                self.logger.info(f"Snapshot saved: {filepath}")
                return True
            except Exception as e:
                self.logger.error(f"Error saving snapshot: {e}")
        return False

    def set_brightness(self, value: int):
        """Set camera brightness (0-100)"""
        if self.camera:
            self.camera.set(cv2.CAP_PROP_BRIGHTNESS, value / 100.0)

    def set_contrast(self, value: int):
        """Set camera contrast (0-100)"""
        if self.camera:
            self.camera.set(cv2.CAP_PROP_CONTRAST, value / 100.0)

    def get_performance_stats(self) -> dict:
        """Get performance statistics"""
        stats = self.performance.get_stats('frame_capture')
        if stats:
            stats['fps'] = self.fps
        return stats or {'fps': self.fps}

    def release(self):
        """Release camera resources"""
        self.stop_capture()

        if self.camera:
            self.camera.release()
            self.camera = None
            self.logger.info("Camera released")

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        self.start_capture()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()


def test_camera():
    """Test camera handler"""
    from utils import setup_logging

    setup_logging("INFO", "camera_test.log")
    config = Config()

    print("Testing Camera Handler...")
    print("Press 'q' to quit")

    with CameraHandler(config) as camera:
        time.sleep(1)  # Let camera warm up

        while True:
            frame = camera.get_current_frame()

            if frame is not None:
                # Display FPS
                fps = camera.get_fps()
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                cv2.imshow('Camera Test', frame)

            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()

        # Print stats
        stats = camera.get_performance_stats()
        print(f"\nPerformance Stats: {stats}")


if __name__ == "__main__":
    test_camera()
