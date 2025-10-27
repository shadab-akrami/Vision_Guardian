"""
Camera Handler for VisionGuardian
Manages webcam capture and frame processing
Optimized for Raspberry Pi 5 with multiple backend support
"""

import cv2
import numpy as np
import logging
import threading
import time
from queue import Queue, Empty
from typing import Optional, Tuple, Callable

from utils import Config, PerformanceMonitor

# Try to import picamera2 for Raspberry Pi camera modules
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False


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

        # Color correction settings
        self.color_correction_enabled = config.get('camera.color_correction.enabled', True)
        self.brightness_adjust = config.get('camera.color_correction.brightness_adjust', 0)
        self.contrast_adjust = config.get('camera.color_correction.contrast_adjust', 5)
        self.saturation_adjust = config.get('camera.color_correction.saturation_adjust', 0)
        self.gamma = config.get('camera.color_correction.gamma', 1.0)

        # Raw mode - bypass ALL processing (for debugging)
        self.raw_mode = config.get('camera.raw_mode', False)

        # Backend selection
        self.backend = None  # Will be set during initialization
        self.camera = None
        self.picam2 = None  # For picamera2 backend
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

    def _init_picamera2(self) -> bool:
        """Try to initialize using picamera2 (Raspberry Pi camera modules)"""
        if not PICAMERA2_AVAILABLE:
            return False

        try:
            self.logger.info("Attempting picamera2 backend (Raspberry Pi Camera Module)...")
            self.picam2 = Picamera2()

            # Configure camera
            config = self.picam2.create_preview_configuration(
                main={"size": (self.resolution_width, self.resolution_height), "format": "RGB888"},
                controls={"FrameRate": self.target_fps}
            )
            self.picam2.configure(config)
            self.picam2.start()

            # Warm up
            time.sleep(0.5)
            test_frame = self.picam2.capture_array()

            if test_frame is not None and test_frame.size > 0:
                # Check if we're getting valid data
                if test_frame.max() == 0:
                    self.logger.warning("picamera2: producing black frames")
                    self.picam2.stop()
                    return False
                elif test_frame.min() == test_frame.max():
                    self.logger.warning(f"picamera2: producing uniform frames (all {test_frame.min()})")
                    self.picam2.stop()
                    return False
                else:
                    self.backend = "picamera2"
                    self.logger.info(f"✅ picamera2 initialized successfully (pixel range: {test_frame.min()}-{test_frame.max()})")
                    return True

            return False

        except Exception as e:
            self.logger.debug(f"picamera2 failed: {e}")
            if self.picam2:
                try:
                    self.picam2.stop()
                except:
                    pass
            return False

    def _init_opencv(self, device_id: int, backend) -> bool:
        """Try to initialize using OpenCV with specified backend"""
        try:
            backend_name = {cv2.CAP_V4L2: "V4L2", cv2.CAP_ANY: "ANY"}.get(backend, str(backend))
            self.logger.info(f"Attempting OpenCV backend {backend_name} with device {device_id}...")

            camera = cv2.VideoCapture(device_id, backend)
            if not camera.isOpened():
                return False

            # Set camera properties
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution_width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution_height)
            camera.set(cv2.CAP_PROP_FPS, self.target_fps)

            # Try to set camera parameters (may not work on all cameras)
            try:
                if self.config.get('camera.auto_focus', True):
                    camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)

                brightness = self.config.get('camera.brightness', 50)
                contrast = self.config.get('camera.contrast', 50)
                saturation = self.config.get('camera.saturation', 50)
                camera.set(cv2.CAP_PROP_BRIGHTNESS, brightness / 100.0)
                camera.set(cv2.CAP_PROP_CONTRAST, contrast / 100.0)
                camera.set(cv2.CAP_PROP_SATURATION, saturation / 100.0)

                if self.config.get('camera.auto_white_balance', True):
                    camera.set(cv2.CAP_PROP_AUTO_WB, 1)

                if self.config.get('camera.auto_exposure', True):
                    camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
            except:
                self.logger.debug("Some camera properties not supported, continuing...")

            # Warm up and test
            for i in range(10):
                ret, frame = camera.read()
                if not ret or frame is None:
                    continue

                if i == 9:  # Last frame
                    if frame.max() == 0:
                        self.logger.warning(f"OpenCV {backend_name}: producing black frames")
                        camera.release()
                        return False
                    elif frame.min() == frame.max():
                        self.logger.warning(f"OpenCV {backend_name}: producing uniform frames (all {frame.min()})")
                        camera.release()
                        return False
                    else:
                        self.camera = camera
                        self.backend = f"opencv_{backend_name.lower()}"
                        actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                        actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        actual_fps = int(camera.get(cv2.CAP_PROP_FPS))
                        self.logger.info(f"✅ OpenCV {backend_name} initialized: {actual_width}x{actual_height} @ {actual_fps}fps (pixel range: {frame.min()}-{frame.max()})")
                        return True

            camera.release()
            return False

        except Exception as e:
            self.logger.debug(f"OpenCV backend {backend_name} failed: {e}")
            return False

    def initialize(self) -> bool:
        """
        Initialize camera with automatic backend detection

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("CAMERA INITIALIZATION - Multi-Backend Support")
            self.logger.info("=" * 60)

            # Strategy 1: Try picamera2 first (best for Raspberry Pi camera modules)
            if PICAMERA2_AVAILABLE:
                self.logger.info("[1/3] Trying picamera2 (Raspberry Pi Camera Module)...")
                if self._init_picamera2():
                    self.logger.info(f"✅ SUCCESS! Using backend: {self.backend}")
                    self._log_camera_status()
                    return True
                self.logger.info("   picamera2 not available or not working")
            else:
                self.logger.info("[1/3] picamera2 library not installed (install with: pip install picamera2)")

            # Strategy 2: Try OpenCV with V4L2 backend and multiple device IDs
            self.logger.info("[2/3] Trying OpenCV with V4L2 backend...")
            device_ids_to_try = [self.device_id, 0, 1, 2]  # Try configured ID first, then common ones
            for dev_id in device_ids_to_try:
                if self._init_opencv(dev_id, cv2.CAP_V4L2):
                    self.device_id = dev_id  # Update to working device ID
                    self.logger.info(f"✅ SUCCESS! Using backend: {self.backend} with device {dev_id}")
                    self._log_camera_status()
                    return True
            self.logger.info("   V4L2 backend not working")

            # Strategy 3: Try OpenCV with generic backend
            self.logger.info("[3/3] Trying OpenCV with generic backend...")
            for dev_id in device_ids_to_try:
                if self._init_opencv(dev_id, cv2.CAP_ANY):
                    self.device_id = dev_id
                    self.logger.info(f"✅ SUCCESS! Using backend: {self.backend} with device {dev_id}")
                    self._log_camera_status()
                    return True

            # All strategies failed
            self.logger.error("=" * 60)
            self.logger.error("❌ ALL CAMERA BACKENDS FAILED")
            self.logger.error("=" * 60)
            self.logger.error("Troubleshooting steps:")
            self.logger.error("1. Check camera connection (USB or ribbon cable)")
            self.logger.error("2. For Raspberry Pi Camera Module:")
            self.logger.error("   - Enable camera: sudo raspi-config → Interface → Camera")
            self.logger.error("   - Install picamera2: pip install picamera2")
            self.logger.error("3. For USB cameras:")
            self.logger.error("   - List devices: ls -l /dev/video*")
            self.logger.error("   - Check permissions: sudo usermod -a -G video $USER")
            self.logger.error("4. Try rebooting the system")
            self.logger.error("=" * 60)
            return False

        except Exception as e:
            self.logger.error(f"Critical error during camera initialization: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def _log_camera_status(self):
        """Log current camera configuration"""
        self.logger.info("Camera Configuration:")
        self.logger.info(f"  Backend: {self.backend}")
        self.logger.info(f"  Device ID: {self.device_id}")
        self.logger.info(f"  Resolution: {self.resolution_width}x{self.resolution_height}")
        self.logger.info(f"  Target FPS: {self.target_fps}")
        self.logger.info(f"  Raw Mode: {self.raw_mode}")
        self.logger.info(f"  Color Correction: {self.color_correction_enabled}")
        self.logger.info("=" * 60)

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

                # Capture frame based on backend
                frame = None
                if self.backend == "picamera2" and self.picam2:
                    # picamera2 backend
                    frame = self.picam2.capture_array()
                    # Convert RGB to BGR for OpenCV compatibility
                    if frame is not None and len(frame.shape) == 3:
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    ret = frame is not None
                elif self.camera:
                    # OpenCV backend
                    ret, frame = self.camera.read()
                else:
                    self.logger.error("No camera backend available")
                    break

                if not ret or frame is None:
                    self.logger.warning("Failed to capture frame")
                    time.sleep(0.1)
                    continue

                # Validate frame data
                if frame.size == 0:
                    self.logger.warning("Captured empty frame")
                    continue

                # Check for grey/black frames
                if self.frame_count % 100 == 0:  # Check every 100 frames
                    if frame.max() == 0:
                        self.logger.error("Camera producing BLACK frames (all zeros)")
                    elif frame.min() == frame.max():
                        self.logger.error(f"Camera producing UNIFORM frames (all {frame.min()})")
                        # Get R, G, B values
                        if len(frame.shape) == 3 and frame.shape[2] == 3:
                            b, g, r = frame[0, 0]
                            self.logger.error(f"  Uniform pixel value: R:{r} G:{g} B:{b}")
                    elif frame.max() < 10:
                        self.logger.warning(f"Camera producing very DARK frames (max={frame.max()})")

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
        # RAW MODE - Return frame as-is with NO processing
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

        # Apply color correction (only if explicitly enabled)
        if self.color_correction_enabled:
            try:
                frame = self._apply_color_correction(frame)
            except Exception as e:
                self.logger.warning(f"Color correction failed: {e}, using original frame")

        return frame

    def _apply_color_correction(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply color correction to frame for natural colors

        Args:
            frame: Input frame

        Returns:
            Color-corrected frame
        """
        corrected = frame.copy()

        # Apply brightness adjustment
        if self.brightness_adjust != 0:
            corrected = cv2.convertScaleAbs(corrected, alpha=1.0, beta=self.brightness_adjust * 2.55)

        # Apply contrast adjustment
        if self.contrast_adjust != 0:
            alpha = 1.0 + (self.contrast_adjust / 100.0)
            corrected = cv2.convertScaleAbs(corrected, alpha=alpha, beta=0)

        # Apply saturation adjustment
        if self.saturation_adjust != 0:
            hsv = cv2.cvtColor(corrected, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = hsv[:, :, 1] * (1.0 + self.saturation_adjust / 100.0)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            corrected = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # Apply gamma correction
        if self.gamma != 1.0:
            inv_gamma = 1.0 / self.gamma
            table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
            corrected = cv2.LUT(corrected, table)

        return corrected

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

        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
            except:
                pass
            self.picam2 = None
            self.logger.info("picamera2 released")

        if self.camera:
            self.camera.release()
            self.camera = None
            self.logger.info("OpenCV camera released")

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
