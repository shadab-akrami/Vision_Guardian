#!/usr/bin/env python3
"""
Visual Test Script for VisionGuardian
Shows camera feed with annotations and displays TTS announcements
Use this to monitor what the system sees and hears
"""

import sys
import os

# Force X11 for display (before importing cv2)
os.environ['QT_QPA_PLATFORM'] = 'xcb'

import cv2
import numpy as np
import time
import threading
from pathlib import Path
from collections import deque

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils import Config, setup_logging
from camera_handler import CameraHandler
from audio_output import AudioOutput, Priority

# Try to import enhanced detection first, fallback to basic
try:
    from enhanced_object_detection import EnhancedObjectDetection
    ENHANCED_AVAILABLE = True
except:
    ENHANCED_AVAILABLE = False

from object_detection import ObjectDetection
from ocr_module import OCRModule
from obstacle_detection import ObstacleDetection
from facial_recognition import FacialRecognition


class VisionTester:
    """Visual testing interface for VisionGuardian"""

    def __init__(self):
        # Setup
        setup_logging("INFO", "vision_test.log")
        self.config = Config()

        # Components
        self.camera = None
        self.object_detector = None
        self.ocr = None
        self.obstacle_detector = None
        self.face_detector = None
        self.audio = None

        # Display settings
        self.window_name = "VisionGuardian - Test Monitor"
        self.display_width = 1280
        self.display_height = 720

        # Announcement tracking
        self.announcements = deque(maxlen=10)
        self.last_announcement = ""
        self.announcement_lock = threading.Lock()

        # Test modes
        self.modes = {
            'o': 'Objects',
            't': 'Text (OCR)',
            'b': 'Obstacles',
            'f': 'Faces',
            'a': 'All'
        }
        self.current_mode = 'o'

        # Camera adjustments (start at zero - camera defaults are good)
        self.brightness_adjust = 0
        self.contrast_adjust = 0
        self.saturation_adjust = 0

        # Statistics
        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()

    def initialize(self):
        """Initialize all components"""
        print("=" * 60)
        print("VisionGuardian Visual Test Monitor")
        print("=" * 60)
        print("\nInitializing components...")

        # Camera
        print("  [1/5] Camera...", end=" ")
        self.camera = CameraHandler(self.config)
        if self.camera.initialize():
            self.camera.start_capture()
            print("OK")
        else:
            print("FAILED")
            return False

        # Object Detection (try enhanced first)
        print("  [2/5] Object Detection...", end=" ")
        enhanced_success = False

        if ENHANCED_AVAILABLE:
            print("(Enhanced YOLOv8)...", end=" ")
            try:
                self.object_detector = EnhancedObjectDetection(self.config)
                if self.object_detector.initialize():
                    print("OK")
                    enhanced_success = True
                else:
                    print("FAILED, trying basic...")
            except Exception as e:
                print(f"ERROR: {e}, trying basic...")

        if not enhanced_success:
            self.object_detector = ObjectDetection(self.config)
            if self.object_detector.initialize():
                print("OK (Basic COCO)")
            else:
                print("FAILED")

        # OCR
        print("  [3/5] Text Recognition...", end=" ")
        self.ocr = OCRModule(self.config)
        if self.ocr.initialize():
            print("OK")
        else:
            print("SKIPPED")

        # Obstacle Detection
        print("  [4/5] Obstacle Detection...", end=" ")
        self.obstacle_detector = ObstacleDetection(self.config)
        if self.obstacle_detector.initialize():
            print("OK")
        else:
            print("SKIPPED")

        # Face Recognition
        print("  [5/5] Face Recognition...", end=" ")
        self.face_detector = FacialRecognition(self.config)
        if self.face_detector.initialize():
            print("OK")
        else:
            print("SKIPPED")

        # Audio (for announcements)
        self.audio = AudioOutput(self.config)
        self.audio.initialize()

        # Intercept audio announcements to display them
        self._setup_audio_interceptor()

        print("\n" + "=" * 60)
        print("Initialization Complete!")
        print("=" * 60)
        return True

    def _setup_audio_interceptor(self):
        """Intercept audio announcements to display them"""
        original_announce = self.audio.announce

        def intercepted_announce(text, priority=Priority.MEDIUM):
            with self.announcement_lock:
                timestamp = time.strftime("%H:%M:%S")
                self.last_announcement = f"[{timestamp}] {text}"
                self.announcements.append(self.last_announcement)
            # Still call original to actually speak
            original_announce(text, priority)

        self.audio.announce = intercepted_announce

    def adjust_frame_colors(self, frame):
        """Adjust frame brightness, contrast, and saturation"""
        adjusted = frame.copy()

        # Apply brightness adjustment
        if self.brightness_adjust != 0:
            adjusted = cv2.convertScaleAbs(adjusted, alpha=1.0, beta=self.brightness_adjust * 2.55)

        # Apply contrast adjustment
        if self.contrast_adjust != 0:
            alpha = 1.0 + (self.contrast_adjust / 100.0)
            adjusted = cv2.convertScaleAbs(adjusted, alpha=alpha, beta=0)

        # Apply saturation adjustment
        if self.saturation_adjust != 0:
            hsv = cv2.cvtColor(adjusted, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = hsv[:, :, 1] * (1.0 + self.saturation_adjust / 100.0)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            adjusted = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        return adjusted

    def process_frame(self, frame):
        """Process frame based on current mode"""
        # Apply additional color adjustments on top of camera settings
        # (Camera already applies base corrections from config)
        # These are for real-time tuning in test mode
        display_frame = self.adjust_frame_colors(frame)
        info_lines = []

        # Process based on mode
        if self.current_mode == 'o' or self.current_mode == 'a':
            # Object detection
            detections = self.object_detector.detect_objects(frame, force=True)
            if detections:
                display_frame = self.object_detector.draw_detections(display_frame, detections)
                summary = self.object_detector.get_object_summary(detections)
                if summary:
                    info_lines.append(f"Objects: {summary}")
                    self.audio.announce(summary, Priority.LOW)

        if self.current_mode == 't' or self.current_mode == 'a':
            # OCR
            if self.ocr and self.ocr.enabled:
                result = self.ocr.read_text(frame)
                if result['text']:
                    info_lines.append(f"Text: {result['text'][:50]}...")
                    if hasattr(self.ocr, 'draw_text_boxes'):
                        display_frame = self.ocr.draw_text_boxes(display_frame, result)

        if self.current_mode == 'b' or self.current_mode == 'a':
            # Obstacle detection
            if self.obstacle_detector and self.obstacle_detector.enabled:
                obstacles = self.obstacle_detector.detect_obstacles(frame)
                if obstacles:
                    alerts = self.obstacle_detector.get_alerts(obstacles)
                    for alert in alerts:
                        info_lines.append(f"Alert: {alert['type']} - {alert['distance']:.0f}cm")

        if self.current_mode == 'f' or self.current_mode == 'a':
            # Face recognition
            if self.face_detector and self.face_detector.enabled:
                faces = self.face_detector.recognize_faces(frame)
                if faces:
                    for face in faces:
                        name = face['name'] if face['is_known'] else "Unknown"
                        info_lines.append(f"Person: {name}")

        return display_frame, info_lines

    def create_display(self, frame, info_lines):
        """Create display with annotations and info panel"""
        # Resize frame to fit display
        h, w = frame.shape[:2]
        scale = min(self.display_width * 0.7 / w, self.display_height / h)
        frame_resized = cv2.resize(frame, None, fx=scale, fy=scale)

        # Create info panel
        panel_width = int(self.display_width * 0.3)
        panel = np.zeros((self.display_height, panel_width, 3), dtype=np.uint8)

        # Draw title
        cv2.putText(panel, "VisionGuardian", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Draw mode
        mode_name = self.modes[self.current_mode]
        cv2.putText(panel, f"Mode: {mode_name}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Draw FPS
        cv2.putText(panel, f"FPS: {self.fps:.1f}", (10, 85),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Draw color adjustments
        cv2.putText(panel, f"Brightness: {self.brightness_adjust:+d}", (10, 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(panel, f"Contrast: {self.contrast_adjust:+d}", (10, 130),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(panel, f"Saturation: {self.saturation_adjust:+d}", (10, 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        # Draw detection info
        y_pos = 180
        cv2.putText(panel, "Detection Info:", (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        y_pos += 25

        for line in info_lines[:5]:
            # Wrap text if too long
            if len(line) > 30:
                line = line[:27] + "..."
            cv2.putText(panel, line, (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            y_pos += 20

        # Draw announcements
        y_pos = 300
        cv2.putText(panel, "Recent Announcements:", (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        y_pos += 25

        with self.announcement_lock:
            for announcement in list(self.announcements)[-5:]:
                # Wrap announcement text
                if len(announcement) > 35:
                    words = announcement.split()
                    line1 = ' '.join(words[:4])
                    line2 = ' '.join(words[4:8])
                    cv2.putText(panel, line1, (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
                    y_pos += 18
                    if line2:
                        cv2.putText(panel, line2, (10, y_pos),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
                        y_pos += 18
                else:
                    cv2.putText(panel, announcement, (10, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
                    y_pos += 20

        # Draw controls
        y_pos = self.display_height - 150
        cv2.putText(panel, "Controls:", (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        y_pos += 25

        controls = [
            "O - Object Detection",
            "T - Text Recognition",
            "B - Obstacle Detection",
            "F - Face Recognition",
            "A - All Features",
            "",
            "1/2 - Brightness +/-",
            "3/4 - Contrast +/-",
            "5/6 - Saturation +/-",
            "0 - Reset Colors",
            "",
            "Q - Quit"
        ]

        for control in controls:
            cv2.putText(panel, control, (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            y_pos += 20

        # Combine frame and panel
        fh, fw = frame_resized.shape[:2]
        ph, pw = panel.shape[:2]

        # Create full display
        display = np.zeros((max(fh, ph), fw + pw, 3), dtype=np.uint8)
        display[:fh, :fw] = frame_resized
        display[:ph, fw:] = panel

        return display

    def run(self):
        """Main test loop"""
        if not self.initialize():
            print("Failed to initialize. Exiting.")
            return

        print("\nTest Monitor Controls:")
        print("  Modes:")
        print("    O - Object Detection")
        print("    T - Text Recognition")
        print("    B - Obstacle Detection")
        print("    F - Face Recognition")
        print("    A - All Features")
        print("\n  Color Adjustments:")
        print("    1/2 - Brightness +/-")
        print("    3/4 - Contrast +/-")
        print("    5/6 - Saturation +/-")
        print("    0   - Reset colors")
        print("\n  Q - Quit")
        print("\n💡 If colors look wrong, adjust using keys 1-6")
        print("Press any key in the window to control...")

        try:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self.window_name, self.display_width, self.display_height)
        except cv2.error as e:
            print(f"\n❌ Cannot create window: {e}")
            print("\n💡 This script requires a display (monitor).")
            print("   Run this on a machine with a display, or use:")
            print("   python3 src/main.py  (for audio-only mode)")
            self.cleanup()
            return

        frame_times = deque(maxlen=30)

        try:
            while True:
                loop_start = time.time()

                # Get frame
                frame = self.camera.get_current_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue

                # Process frame
                processed_frame, info_lines = self.process_frame(frame)

                # Calculate FPS
                self.frame_count += 1
                frame_times.append(time.time())
                if len(frame_times) > 1:
                    self.fps = len(frame_times) / (frame_times[-1] - frame_times[0])

                # Create display
                display = self.create_display(processed_frame, info_lines)

                # Show
                try:
                    cv2.imshow(self.window_name, display)
                except cv2.error as e:
                    print(f"\n❌ Display error: {e}")
                    print("Window closed or display unavailable. Exiting...")
                    break

                # Handle keys
                key = cv2.waitKey(1) & 0xFF

                if key == ord('q') or key == ord('Q') or key == 27:  # Q or ESC
                    break
                elif key == ord('o') or key == ord('O'):
                    self.current_mode = 'o'
                    print("Mode: Object Detection")
                elif key == ord('t') or key == ord('T'):
                    self.current_mode = 't'
                    print("Mode: Text Recognition")
                elif key == ord('b') or key == ord('B'):
                    self.current_mode = 'b'
                    print("Mode: Obstacle Detection")
                elif key == ord('f') or key == ord('F'):
                    self.current_mode = 'f'
                    print("Mode: Face Recognition")
                elif key == ord('a') or key == ord('A'):
                    self.current_mode = 'a'
                    print("Mode: All Features")

                # Color adjustments
                elif key == ord('1'):
                    self.brightness_adjust = min(50, self.brightness_adjust + 5)
                    print(f"Brightness: {self.brightness_adjust:+d}")
                elif key == ord('2'):
                    self.brightness_adjust = max(-50, self.brightness_adjust - 5)
                    print(f"Brightness: {self.brightness_adjust:+d}")
                elif key == ord('3'):
                    self.contrast_adjust = min(50, self.contrast_adjust + 5)
                    print(f"Contrast: {self.contrast_adjust:+d}")
                elif key == ord('4'):
                    self.contrast_adjust = max(-50, self.contrast_adjust - 5)
                    print(f"Contrast: {self.contrast_adjust:+d}")
                elif key == ord('5'):
                    self.saturation_adjust = min(50, self.saturation_adjust + 5)
                    print(f"Saturation: {self.saturation_adjust:+d}")
                elif key == ord('6'):
                    self.saturation_adjust = max(-50, self.saturation_adjust - 5)
                    print(f"Saturation: {self.saturation_adjust:+d}")
                elif key == ord('0'):
                    self.brightness_adjust = 0
                    self.contrast_adjust = 0
                    self.saturation_adjust = 0
                    print("Colors reset to default")

                # Maintain frame rate
                elapsed = time.time() - loop_start
                if elapsed < 0.033:  # Target 30 FPS
                    time.sleep(0.033 - elapsed)

        except KeyboardInterrupt:
            print("\nInterrupted by user")

        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources"""
        print("\nCleaning up...")
        if self.camera:
            self.camera.release()
        if self.audio:
            self.audio.shutdown()
        cv2.destroyAllWindows()
        print("Done!")


def main():
    tester = VisionTester()
    tester.run()


if __name__ == "__main__":
    main()
