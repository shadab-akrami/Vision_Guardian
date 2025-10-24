"""
VisionGuardian - Main Application
Smart wearable assistant system for visually impaired users
Optimized for Raspberry Pi 5 (64-bit ARM64)
"""

import sys
import os
import logging
import time
import threading
import signal
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils import Config, setup_logging, get_system_info, check_raspberry_pi5
from storage_manager import StorageManager
from camera_handler import CameraHandler
from audio_output import AudioOutput, Priority
from facial_recognition import FacialRecognition
from object_detection import ObjectDetection
from ocr_module import OCRModule
from scene_description import SceneDescription
from obstacle_detection import ObstacleDetection
from currency_detection import CurrencyDetection
from color_detection import ColorDetection
from voice_assistant import VoiceAssistant


class VisionGuardian:
    """Main application class"""

    def __init__(self):
        # Load configuration
        self.config = Config()

        # Setup logging
        log_level = self.config.get('system.log_level', 'INFO')
        self.logger = setup_logging(log_level, 'visionguardian.log')

        self.logger.info("=" * 60)
        self.logger.info("VisionGuardian Starting...")
        self.logger.info("=" * 60)

        # Initialize storage manager first (needed by system check)
        self.storage_manager = StorageManager(self.config)

        # System check
        self._check_system()

        # Initialize other components
        self.camera = None
        self.audio = None
        self.face_recognition = None
        self.object_detection = None
        self.ocr = None
        self.scene_description = None
        self.obstacle_detection = None
        self.currency_detection = None
        self.color_detection = None
        self.voice_assistant = None

        # Application state
        self.is_running = False
        self.active_mode = 'auto'  # auto, obstacle, read, identify, currency, color
        self.last_announcement = ""

        # Feature priorities (from config)
        self.priorities = self.config.get('priorities', {})

        # Processing threads
        self.threads = []

        # Feature enable flags
        self.features_enabled = {
            'facial_recognition': self.config.get('facial_recognition.enabled', True),
            'object_detection': self.config.get('object_detection.enabled', True),
            'ocr': self.config.get('ocr.enabled', True),
            'scene_description': self.config.get('scene_description.enabled', True),
            'obstacle_detection': self.config.get('obstacle_detection.enabled', True),
            'currency_detection': self.config.get('currency_detection.enabled', True),
            'color_detection': self.config.get('color_detection.enabled', True),
            'voice_assistant': self.config.get('voice_assistant.enabled', True),
        }

    def _check_system(self):
        """Check system requirements"""
        self.logger.info("System Information:")
        info = get_system_info()
        for key, value in info.items():
            self.logger.info(f"  {key}: {value}")

        # Check if Raspberry Pi 5
        is_rpi5 = check_raspberry_pi5()
        if not is_rpi5:
            self.logger.warning("Not running on Raspberry Pi 5 - performance may vary")

        # Check storage
        status, message = self.storage_manager.check_storage_health()
        self.logger.info(f"Storage: {message}")

    def initialize(self) -> bool:
        """
        Initialize all components

        Returns:
            True if successful
        """
        try:
            self.logger.info("Initializing components...")

            # Initialize camera
            self.logger.info("Initializing camera...")
            self.camera = CameraHandler(self.config)
            if not self.camera.initialize():
                self.logger.error("Failed to initialize camera")
                return False

            # Initialize audio
            self.logger.info("Initializing audio output...")
            self.audio = AudioOutput(self.config)
            if not self.audio.initialize():
                self.logger.error("Failed to initialize audio")
                return False

            self.audio.announce("VisionGuardian initializing", Priority.HIGH)

            # Initialize facial recognition
            if self.features_enabled['facial_recognition']:
                self.logger.info("Initializing facial recognition...")
                self.face_recognition = FacialRecognition(self.config)
                if self.face_recognition.initialize():
                    self.logger.info("Facial recognition ready")
                else:
                    self.logger.warning("Facial recognition initialization failed")
                    self.features_enabled['facial_recognition'] = False

            # Initialize object detection
            if self.features_enabled['object_detection']:
                self.logger.info("Initializing object detection...")
                self.object_detection = ObjectDetection(self.config)
                if self.object_detection.initialize():
                    self.logger.info("Object detection ready")
                else:
                    self.logger.warning("Object detection initialization failed")
                    self.features_enabled['object_detection'] = False

            # Initialize OCR
            if self.features_enabled['ocr']:
                self.logger.info("Initializing OCR...")
                self.ocr = OCRModule(self.config)
                if self.ocr.initialize():
                    self.logger.info("OCR ready")
                else:
                    self.logger.warning("OCR initialization failed")
                    self.features_enabled['ocr'] = False

            # Initialize scene description
            if self.features_enabled['scene_description']:
                self.scene_description = SceneDescription(self.config)
                if self.scene_description.initialize():
                    self.logger.info("Scene description ready")

            # Initialize obstacle detection
            if self.features_enabled['obstacle_detection']:
                self.obstacle_detection = ObstacleDetection(self.config)
                if self.obstacle_detection.initialize():
                    self.logger.info("Obstacle detection ready")

            # Initialize currency detection
            if self.features_enabled['currency_detection']:
                self.currency_detection = CurrencyDetection(self.config)
                if self.currency_detection.initialize():
                    self.logger.info("Currency detection ready")

            # Initialize color detection
            if self.features_enabled['color_detection']:
                self.color_detection = ColorDetection(self.config)
                self.logger.info("Color detection ready")

            # Initialize voice assistant
            if self.features_enabled['voice_assistant']:
                self.voice_assistant = VoiceAssistant(self.config)
                if self.voice_assistant.initialize():
                    self._setup_voice_commands()
                    self.logger.info("Voice assistant ready")

            self.logger.info("All components initialized successfully")
            self.audio.announce("VisionGuardian ready", Priority.HIGH)

            return True

        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False

    def _setup_voice_commands(self):
        """Setup voice command callbacks"""
        if not self.voice_assistant:
            return

        self.voice_assistant.register_command_callback('read_text', self._cmd_read_text)
        self.voice_assistant.register_command_callback('describe_scene', self._cmd_describe_scene)
        self.voice_assistant.register_command_callback('identify_people', self._cmd_identify_people)
        self.voice_assistant.register_command_callback('detect_color', self._cmd_detect_color)
        self.voice_assistant.register_command_callback('detect_currency', self._cmd_detect_currency)
        self.voice_assistant.register_command_callback('check_obstacles', self._cmd_check_obstacles)
        self.voice_assistant.register_command_callback('show_help', self._cmd_show_help)
        self.voice_assistant.register_command_callback('stop_all', self._cmd_stop)
        self.voice_assistant.register_command_callback('repeat_last', self._cmd_repeat)

    def start(self):
        """Start the application"""
        try:
            self.is_running = True

            # Start camera capture
            self.camera.start_capture()

            # Start processing threads
            self._start_processing_threads()

            # Start voice assistant
            if self.voice_assistant:
                self.voice_assistant.start_listening()

            self.logger.info("VisionGuardian started successfully")

            # Main loop
            self._main_loop()

        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        finally:
            self.shutdown()

    def _start_processing_threads(self):
        """Start background processing threads"""
        # Obstacle detection thread (highest priority)
        if self.features_enabled['obstacle_detection']:
            thread = threading.Thread(target=self._obstacle_detection_loop, daemon=True)
            thread.start()
            self.threads.append(thread)

        # Facial recognition thread
        if self.features_enabled['facial_recognition']:
            thread = threading.Thread(target=self._facial_recognition_loop, daemon=True)
            thread.start()
            self.threads.append(thread)

        # Object detection thread
        if self.features_enabled['object_detection']:
            thread = threading.Thread(target=self._object_detection_loop, daemon=True)
            thread.start()
            self.threads.append(thread)

        # Storage monitoring thread
        thread = threading.Thread(target=self._storage_monitor_loop, daemon=True)
        thread.start()
        self.threads.append(thread)

    def _main_loop(self):
        """Main processing loop"""
        frame_count = 0

        while self.is_running:
            try:
                frame = self.camera.get_current_frame()

                if frame is not None:
                    frame_count += 1

                    # Display FPS (if debug mode)
                    if self.config.get('system.debug_mode', False):
                        fps = self.camera.get_fps()
                        if frame_count % 30 == 0:
                            self.logger.debug(f"FPS: {fps:.1f}")

                time.sleep(0.01)  # Small delay to prevent CPU overload

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(0.1)

    def _obstacle_detection_loop(self):
        """Background thread for obstacle detection"""
        self.logger.info("Obstacle detection thread started")

        while self.is_running:
            try:
                frame = self.camera.get_current_frame()

                if frame is not None and self.obstacle_detection:
                    obstacles = self.obstacle_detection.detect_obstacles(frame)
                    alerts = self.obstacle_detection.get_alerts(obstacles)

                    for alert in alerts:
                        message = self.obstacle_detection.format_alert(alert)
                        self.audio.announce(message, Priority.CRITICAL)

                time.sleep(0.5)  # Check twice per second

            except Exception as e:
                self.logger.error(f"Error in obstacle detection: {e}")
                time.sleep(1)

    def _facial_recognition_loop(self):
        """Background thread for facial recognition"""
        self.logger.info("Facial recognition thread started")

        while self.is_running:
            try:
                frame = self.camera.get_current_frame()

                if frame is not None and self.face_recognition:
                    faces = self.face_recognition.recognize_faces(frame)

                    for face in faces:
                        if face['announce'] and face['is_known']:
                            self.audio.person_detected(face['name'])

                time.sleep(2)  # Check every 2 seconds

            except Exception as e:
                self.logger.error(f"Error in facial recognition: {e}")
                time.sleep(1)

    def _object_detection_loop(self):
        """Background thread for object detection"""
        self.logger.info("Object detection thread started")

        while self.is_running:
            try:
                frame = self.camera.get_current_frame()

                if frame is not None and self.object_detection:
                    objects = self.object_detection.detect_objects(frame)

                    if objects:
                        summary = self.object_detection.get_object_summary(objects)
                        if summary:
                            self.audio.object_detected(summary)

                time.sleep(3)  # Check every 3 seconds

            except Exception as e:
                self.logger.error(f"Error in object detection: {e}")
                time.sleep(1)

    def _storage_monitor_loop(self):
        """Background thread for storage monitoring"""
        self.logger.info("Storage monitor thread started")

        while self.is_running:
            try:
                # Check storage every 5 minutes
                time.sleep(300)

                status, needs_attention = self.storage_manager.monitor_storage()

                if needs_attention:
                    self.logger.warning(status)

                # Perform cleanup if auto-cleanup is enabled
                if self.config.get('storage.auto_cleanup', True):
                    self.storage_manager.perform_cleanup()

            except Exception as e:
                self.logger.error(f"Error in storage monitor: {e}")
                time.sleep(60)

    # Voice command handlers
    def _cmd_read_text(self, command=None):
        """Read text from current view"""
        self.logger.info("Command: Read text")
        frame = self.camera.get_current_frame()

        if frame is not None and self.ocr:
            result = self.ocr.read_text(frame)
            text = self.ocr.format_for_announcement(result)

            if text:
                self.audio.read_text(text)
                self.last_announcement = text
            else:
                self.audio.announce("No text detected", Priority.MEDIUM)

    def _cmd_describe_scene(self, command=None):
        """Describe current scene"""
        self.logger.info("Command: Describe scene")
        frame = self.camera.get_current_frame()

        if frame is not None and self.scene_description:
            description = self.scene_description.describe_scene(frame, force=True)

            if description:
                self.audio.describe_scene(description)
                self.last_announcement = description

    def _cmd_identify_people(self, command=None):
        """Identify people in view"""
        self.logger.info("Command: Identify people")
        frame = self.camera.get_current_frame()

        if frame is not None and self.face_recognition:
            faces = self.face_recognition.recognize_faces(frame)

            if faces:
                known = [f['name'] for f in faces if f['is_known']]
                unknown = len([f for f in faces if not f['is_known']])

                if known:
                    self.audio.announce(f"I see {', '.join(known)}", Priority.HIGH)
                if unknown > 0:
                    self.audio.announce(f"And {unknown} unknown person{'s' if unknown > 1 else ''}", Priority.HIGH)
            else:
                self.audio.announce("No people detected", Priority.MEDIUM)

    def _cmd_detect_color(self, command=None):
        """Detect colors"""
        self.logger.info("Command: Detect color")
        frame = self.camera.get_current_frame()

        if frame is not None and self.color_detection:
            color = self.color_detection.detect_color_at_center(frame)
            self.audio.color_detected(color)

    def _cmd_detect_currency(self, command=None):
        """Detect currency"""
        self.logger.info("Command: Detect currency")
        frame = self.camera.get_current_frame()

        if frame is not None and self.currency_detection:
            detection = self.currency_detection.detect_currency(frame)

            if detection:
                announcement = self.currency_detection.format_announcement(detection)
                self.audio.announce(announcement, Priority.HIGH)
            else:
                self.audio.announce("No currency detected", Priority.MEDIUM)

    def _cmd_check_obstacles(self, command=None):
        """Check for obstacles"""
        self.logger.info("Command: Check obstacles")
        frame = self.camera.get_current_frame()

        if frame is not None and self.obstacle_detection:
            obstacles = self.obstacle_detection.detect_obstacles(frame)

            if obstacles:
                closest = obstacles[0]
                message = self.obstacle_detection.format_alert(closest)
                self.audio.announce(message, Priority.HIGH)
            else:
                self.audio.announce("Path is clear", Priority.MEDIUM)

    def _cmd_show_help(self, command=None):
        """Show help"""
        help_text = "Available commands: read text, describe scene, identify people, detect color, identify money, check obstacles, repeat, stop"
        self.audio.announce(help_text, Priority.HIGH)

    def _cmd_stop(self, command=None):
        """Stop all announcements"""
        self.audio.clear_queue()
        self.audio.announce("Stopped", Priority.HIGH)

    def _cmd_repeat(self, command=None):
        """Repeat last announcement"""
        if self.last_announcement:
            self.audio.announce(self.last_announcement, Priority.HIGH)
        else:
            self.audio.announce("Nothing to repeat", Priority.MEDIUM)

    def shutdown(self):
        """Shutdown application"""
        self.logger.info("Shutting down VisionGuardian...")

        self.is_running = False

        # Stop voice assistant
        if self.voice_assistant:
            self.voice_assistant.stop_listening()

        # Wait for threads
        for thread in self.threads:
            thread.join(timeout=2)

        # Release camera
        if self.camera:
            self.camera.release()

        # Shutdown audio
        if self.audio:
            self.audio.announce("VisionGuardian shutting down", Priority.HIGH)
            self.audio.wait_until_done(timeout=5)
            self.audio.shutdown()

        self.logger.info("VisionGuardian stopped")


def main():
    """Main entry point"""
    print("=" * 60)
    print("VisionGuardian - Smart Assistant for Visually Impaired")
    print("Optimized for Raspberry Pi 5")
    print("=" * 60)
    print()

    # Create application
    app = VisionGuardian()

    # Initialize
    if not app.initialize():
        print("Failed to initialize VisionGuardian")
        return 1

    # Setup signal handlers
    def signal_handler(sig, frame):
        print("\nShutting down...")
        app.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start application
    app.start()

    return 0


if __name__ == "__main__":
    sys.exit(main())
