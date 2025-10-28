"""
Camera Handler for VisionGuardian - USB Webcam Optimized
Rebuilt from scratch based on what actually works on Raspberry Pi
"""

import cv2
import numpy as np
import logging
import threading
import time
from queue import Queue, Empty
from typing import Optional, Tuple

from utils import Config, PerformanceMonitor


class CameraHandler:
    """Simple, reliable camera handler optimized for USB webcams"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.CameraHandler')

        # Camera settings
        self.device_id = config.get('camera.device_id', 0)
        self.resolution_width = config.get('camera.resolution_width', 640)
        self.resolution_height = config.get('camera.resolution_height', 480)
        self.target_fps = config.get('camera.fps', 30)
        self.rotation = config.get('camera.rotation', 0)
        self.flip_horizontal = config.get('camera.flip_horizontal', False)
        self.flip_vertical = config.get('camera.flip_vertical', False)

        # Color correction settings
        self.color_correction_enabled = config.get('camera.color_correction.enabled', False)
        self.brightness_adjust = config.get('camera.color_correction.brightness_adjust', 0)
        self.contrast_adjust = config.get('camera.color_correction.contrast_adjust', 0)
        self.saturation_adjust = config.get('camera.color_correction.saturation_adjust', 0)
        self.gamma = config.get('camera.color_correction.gamma', 1.0)

        # Raw mode
        self.raw_mode = config.get('camera.raw_mode', False)

        # Backend
        self.backend = None
        self.camera = None
        self.is_running = False

        # Threading
        self.capture_thread = None
        self.frame_queue = Queue(maxsize=2)

        # Frame management
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.frame_count = 0

        # Performance
        self.performance = PerformanceMonitor()
        self.fps = 0
        self.last_fps_time = time.time()

    def _try_open_camera(self, device_id: int, backend, backend_name: str) -> bool:
        """
        Try to open camera with minimal settings (like the working test)
        NO time.sleep() calls during warm-up!
        """
        try:
            self.logger.info(f"Trying device {device_id} with {backend_name}...")

            # Open camera (just like working test)
            camera = cv2.VideoCapture(device_id, backend)

            if not camera.isOpened():
                self.logger.debug(f"  Device {device_id} not opened")
                return False

            # Set ONLY resolution and FPS (keep it simple!)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution_width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution_height)
            camera.set(cv2.CAP_PROP_FPS, self.target_fps)

            # Try to set MJPEG format (helps some cameras)
            try:
                camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            except:
                pass

            # Warm up: Read frames FAST with NO delays (critical!)
            # This is what the working test does
            self.logger.info(f"  Warming up (reading frames continuously)...")

            valid_count = 0
            test_frames = []

            # Read 50 frames continuously (no sleep!)
            for i in range(50):
                ret, frame = camera.read()

                if not ret or frame is None:
                    continue

                # Save last 10 frames for testing
                if i >= 40:
                    test_frames.append(frame)

                # Check progress
                if i % 10 == 0 and frame is not None:
                    is_valid = frame.max() > 0 and frame.min() != frame.max()
                    if is_valid:
                        valid_count += 1
                        self.logger.debug(f"    Frame {i}: Valid (pixels: {frame.min()}-{frame.max()})")
                    else:
                        self.logger.debug(f"    Frame {i}: Uniform (value: {frame.min()})")

            # Validate last 10 frames
            if not test_frames:
                self.logger.debug(f"  No frames captured")
                camera.release()
                return False

            valid_frames = 0
            for frame in test_frames:
                if frame.max() > 0 and frame.min() != frame.max():
                    valid_frames += 1

            # Need at least 7/10 valid frames
            if valid_frames >= 7:
                last_frame = test_frames[-1]
                self.camera = camera
                self.backend = backend_name
                self.device_id = device_id

                actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                actual_fps = int(camera.get(cv2.CAP_PROP_FPS))

                self.logger.info(f"✅ SUCCESS! Device {device_id} with {backend_name}")
                self.logger.info(f"   Resolution: {actual_width}x{actual_height} @ {actual_fps}fps")
                self.logger.info(f"   Valid frames: {valid_frames}/10")
                self.logger.info(f"   Pixel range: {last_frame.min()}-{last_frame.max()}")
                return True
            else:
                self.logger.debug(f"  Not enough valid frames ({valid_frames}/10)")
                camera.release()
                return False

        except Exception as e:
            self.logger.debug(f"  Exception: {e}")
            return False

    def initialize(self) -> bool:
        """Initialize camera - try different devices and backends"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("CAMERA INITIALIZATION - USB Webcam Optimized")
            self.logger.info("=" * 60)

            # Try different combinations
            devices_to_try = [0, 1, 2]  # Most common
            backends_to_try = [
                (cv2.CAP_V4L2, "V4L2"),
                (cv2.CAP_ANY, "ANY")
            ]

            for device_id in devices_to_try:
                for backend, backend_name in backends_to_try:
                    if self._try_open_camera(device_id, backend, backend_name):
                        self.logger.info("=" * 60)
                        return True

            # Failed
            self.logger.error("=" * 60)
            self.logger.error("❌ CAMERA INITIALIZATION FAILED")
            self.logger.error("=" * 60)
            self.logger.error("Troubleshooting:")
            self.logger.error("1. Check USB connection")
            self.logger.error("2. Try different USB port")
            self.logger.error("3. Check: ls -l /dev/video*")
            self.logger.error("4. Check: lsusb | grep -i logitech")
            self.logger.error("5. Unplug and replug camera")
            self.logger.error("6. Try: sudo reboot")
            self.logger.error("=" * 60)
            return False

        except Exception as e:
            self.logger.error(f"Critical error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def start_capture(self) -> bool:
        """Start continuous frame capture in background thread"""
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
        """Main capture loop - reads frames continuously"""
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

                # Validate frame
                if frame.size == 0:
                    self.logger.warning("Empty frame")
                    continue

                # Process frame (rotation, flipping, color correction)
                frame = self._process_frame(frame)

                # Update current frame
                with self.frame_lock:
                    self.current_frame = frame
                    self.frame_count += 1

                # Update queue
                try:
                    if self.frame_queue.full():
                        self.frame_queue.get_nowait()
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
        """Process frame (rotation, flipping, color correction)"""
        if self.raw_mode:
            return frame

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

        # Apply color correction
        if self.color_correction_enabled:
            try:
                frame = self._apply_color_correction(frame)
            except Exception as e:
                self.logger.warning(f"Color correction failed: {e}")

        return frame

    def _apply_color_correction(self, frame: np.ndarray) -> np.ndarray:
        """Apply color correction"""
        corrected = frame.copy()

        if self.brightness_adjust != 0:
            corrected = cv2.convertScaleAbs(corrected, alpha=1.0, beta=self.brightness_adjust * 2.55)

        if self.contrast_adjust != 0:
            alpha = 1.0 + (self.contrast_adjust / 100.0)
            corrected = cv2.convertScaleAbs(corrected, alpha=alpha, beta=0)

        if self.saturation_adjust != 0:
            hsv = cv2.cvtColor(corrected, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = hsv[:, :, 1] * (1.0 + self.saturation_adjust / 100.0)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            corrected = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        if self.gamma != 1.0:
            inv_gamma = 1.0 / self.gamma
            table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
            corrected = cv2.LUT(corrected, table)

        return corrected

    def get_frame(self, timeout: float = 0.5) -> Optional[np.ndarray]:
        """Get latest frame from queue"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except Empty:
            return None

    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get current frame (no waiting)"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read a single frame (compatible with cv2.VideoCapture)"""
        frame = self.get_current_frame()
        return (frame is not None, frame)

    def get_fps(self) -> float:
        """Get current FPS"""
        return self.fps

    def get_resolution(self) -> Tuple[int, int]:
        """Get resolution (width, height)"""
        return (self.resolution_width, self.resolution_height)

    def take_snapshot(self, filepath: str) -> bool:
        """Save current frame to file"""
        frame = self.get_current_frame()
        if frame is not None:
            try:
                cv2.imwrite(filepath, frame)
                self.logger.info(f"Snapshot saved: {filepath}")
                return True
            except Exception as e:
                self.logger.error(f"Error saving snapshot: {e}")
        return False

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
