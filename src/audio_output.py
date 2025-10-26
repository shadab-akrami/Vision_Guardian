"""
Audio Output Module for VisionGuardian
Handles text-to-speech and audio announcements with priority system
Optimized for Raspberry Pi 5
"""

import logging
import threading
import time
import queue
from typing import Optional, Dict
from dataclasses import dataclass
from enum import IntEnum
import pyttsx3

try:
    from gtts import gTTS
    import tempfile
    import os
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

from utils import Config


class Priority(IntEnum):
    """Priority levels for announcements"""
    EMERGENCY = 1
    CRITICAL = 2
    HIGH = 3
    MEDIUM = 4
    LOW = 5


@dataclass
class Announcement:
    """Announcement data structure"""
    text: str
    priority: Priority
    timestamp: float
    interruptible: bool = True

    def __lt__(self, other):
        """Compare announcements by priority and timestamp"""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


class AudioOutput:
    """Manages audio output with priority-based announcement system"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.AudioOutput')

        # Audio settings
        self.engine_type = config.get('audio.engine', 'pyttsx3')
        self.voice_speed = config.get('audio.voice_speed', 160)
        self.volume = config.get('audio.volume', 0.9)
        self.language = config.get('audio.language', 'en')
        self.enable_audio_cues = config.get('audio.enable_audio_cues', True)
        self.priority_interrupt = config.get('audio.priority_interrupt', True)

        # TTS engine
        self.tts_engine = None
        self.engine_lock = threading.Lock()

        # Announcement queue
        self.announcement_queue = queue.PriorityQueue()
        self.is_speaking = False
        self.current_announcement = None

        # Threading
        self.speaker_thread = None
        self.is_running = False

        # Performance
        self.announcements_made = 0
        self.announcements_skipped = 0

    def initialize(self) -> bool:
        """
        Initialize audio engine

        Returns:
            True if successful
        """
        try:
            if self.engine_type == 'pyttsx3':
                self.logger.info("Initializing pyttsx3 engine...")
                self.tts_engine = pyttsx3.init()

                # Set properties
                self.tts_engine.setProperty('rate', self.voice_speed)
                self.tts_engine.setProperty('volume', self.volume)

                # Set voice (try to find female voice for better clarity)
                voices = self.tts_engine.getProperty('voices')
                if voices:
                    # Try to select a suitable voice
                    for voice in voices:
                        if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                            self.tts_engine.setProperty('voice', voice.id)
                            break

                self.logger.info("pyttsx3 engine initialized")

            elif self.engine_type == 'gtts':
                if not GTTS_AVAILABLE:
                    self.logger.error("gTTS not available, falling back to pyttsx3")
                    self.engine_type = 'pyttsx3'
                    return self.initialize()
                self.logger.info("Using gTTS engine")

            else:
                self.logger.error(f"Unknown engine type: {self.engine_type}")
                return False

            # Start speaker thread
            self.is_running = True
            self.speaker_thread = threading.Thread(target=self._speaker_loop, daemon=True)
            self.speaker_thread.start()

            self.logger.info("Audio output initialized")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing audio: {e}")
            return False

    def announce(self, text: str, priority: Priority = Priority.MEDIUM,
                 interrupt: bool = None) -> bool:
        """
        Queue announcement for speaking

        Args:
            text: Text to speak
            priority: Priority level
            interrupt: Whether to interrupt current speech (None = use config)

        Returns:
            True if queued successfully
        """
        if not text or not text.strip():
            return False

        if interrupt is None:
            interrupt = self.priority_interrupt

        announcement = Announcement(
            text=text.strip(),
            priority=priority,
            timestamp=time.time(),
            interruptible=interrupt
        )

        try:
            # If high priority and interrupt enabled, clear queue of lower priority items
            if interrupt and priority <= Priority.HIGH:
                if self.is_speaking and self.current_announcement:
                    if self.current_announcement.priority > priority:
                        self._stop_current_speech()

            self.announcement_queue.put(announcement)
            self.logger.debug(f"Queued announcement (P{priority}): {text[:50]}...")
            return True

        except Exception as e:
            self.logger.error(f"Error queuing announcement: {e}")
            return False

    def _speaker_loop(self):
        """Main speaker loop running in background thread"""
        while self.is_running:
            try:
                # Get next announcement (with timeout)
                announcement = self.announcement_queue.get(timeout=0.5)

                self.current_announcement = announcement
                self.is_speaking = True

                # Speak the text
                success = self._speak(announcement.text)

                if success:
                    self.announcements_made += 1
                else:
                    self.announcements_skipped += 1

                self.is_speaking = False
                self.current_announcement = None

            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in speaker loop: {e}")
                time.sleep(0.1)

    def _speak(self, text: str) -> bool:
        """
        Speak text using configured engine

        Args:
            text: Text to speak

        Returns:
            True if successful
        """
        try:
            if self.engine_type == 'pyttsx3':
                return self._speak_pyttsx3(text)
            elif self.engine_type == 'gtts':
                return self._speak_gtts(text)
            else:
                self.logger.error(f"Unknown engine: {self.engine_type}")
                return False

        except Exception as e:
            self.logger.error(f"Error speaking: {e}")
            return False

    def _speak_pyttsx3(self, text: str) -> bool:
        """Speak using pyttsx3"""
        try:
            with self.engine_lock:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            return True
        except Exception as e:
            self.logger.error(f"pyttsx3 error: {e}")
            return False

    def _speak_gtts(self, text: str) -> bool:
        """Speak using gTTS"""
        try:
            # Generate speech
            tts = gTTS(text=text, lang=self.language, slow=False)

            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_file = fp.name
                tts.save(temp_file)

            # Play audio (requires external player like mpg123 or pygame)
            # For Raspberry Pi, we'll use pygame or system command
            try:
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)

                pygame.mixer.music.unload()
            except ImportError:
                # Fallback to system command
                os.system(f'mpg123 -q {temp_file}')

            # Clean up
            os.unlink(temp_file)
            return True

        except Exception as e:
            self.logger.error(f"gTTS error: {e}")
            return False

    def _stop_current_speech(self):
        """Stop current speech"""
        try:
            if self.engine_type == 'pyttsx3':
                with self.engine_lock:
                    self.tts_engine.stop()
            self.is_speaking = False
        except Exception as e:
            self.logger.error(f"Error stopping speech: {e}")

    def play_beep(self, frequency: int = 1000, duration_ms: int = 200):
        """
        Play a beep sound (audio cue)

        Args:
            frequency: Beep frequency in Hz
            duration_ms: Duration in milliseconds
        """
        if not self.enable_audio_cues:
            return

        try:
            # Generate and play beep using numpy and pygame/sounddevice
            # This is a simplified version
            self.logger.debug(f"Beep: {frequency}Hz for {duration_ms}ms")
        except Exception as e:
            self.logger.error(f"Error playing beep: {e}")

    def emergency_announce(self, text: str):
        """Emergency announcement (highest priority, interrupts everything)"""
        self.announce(text, Priority.EMERGENCY, interrupt=True)

    def obstacle_alert(self, distance: float, direction: str):
        """Specialized obstacle alert"""
        text = f"Obstacle {direction}, {distance:.0f} centimeters"
        self.announce(text, Priority.CRITICAL, interrupt=True)

    def person_detected(self, name: str):
        """Announce person detected"""
        text = f"Hello {name}"
        self.announce(text, Priority.HIGH)

    def object_detected(self, objects: list):
        """Announce detected objects"""
        if len(objects) == 1:
            text = f"I see {objects[0]}"
        elif len(objects) == 2:
            text = f"I see {objects[0]} and {objects[1]}"
        else:
            text = f"I see {', '.join(objects[:-1])}, and {objects[-1]}"

        self.announce(text, Priority.MEDIUM)

    def read_text(self, text: str):
        """Read text from OCR"""
        self.announce(text, Priority.MEDIUM)

    def describe_scene(self, description: str):
        """Announce scene description"""
        self.announce(description, Priority.LOW)

    def currency_detected(self, amount: str, currency: str):
        """Announce currency detection"""
        text = f"{amount} {currency}"
        self.announce(text, Priority.HIGH)

    def color_detected(self, color: str):
        """Announce color"""
        text = f"Color: {color}"
        self.announce(text, Priority.MEDIUM)

    def clear_queue(self):
        """Clear announcement queue"""
        while not self.announcement_queue.empty():
            try:
                self.announcement_queue.get_nowait()
            except queue.Empty:
                break

    def get_queue_size(self) -> int:
        """Get number of pending announcements"""
        return self.announcement_queue.qsize()

    def is_busy(self) -> bool:
        """Check if currently speaking"""
        return self.is_speaking

    def wait_until_done(self, timeout: float = 10.0):
        """Wait until all announcements are complete"""
        start_time = time.time()
        while (self.is_speaking or not self.announcement_queue.empty()):
            if time.time() - start_time > timeout:
                self.logger.warning("Timeout waiting for announcements to complete")
                break
            time.sleep(0.1)

    def get_stats(self) -> Dict[str, int]:
        """Get statistics"""
        return {
            'announcements_made': self.announcements_made,
            'announcements_skipped': self.announcements_skipped,
            'queue_size': self.get_queue_size(),
            'is_speaking': self.is_speaking
        }

    def shutdown(self):
        """Shutdown audio output"""
        self.is_running = False

        # Wait for current speech to finish
        self.wait_until_done(timeout=5.0)

        # Stop thread
        if self.speaker_thread:
            self.speaker_thread.join(timeout=2)

        # Cleanup engine
        if self.tts_engine and self.engine_type == 'pyttsx3':
            try:
                self.tts_engine.stop()
            except:
                pass

        self.logger.info("Audio output shutdown")

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()


def test_audio():
    """Test audio output"""
    from utils import setup_logging

    setup_logging("INFO", "audio_test.log")
    config = Config()

    print("Testing Audio Output...")

    with AudioOutput(config) as audio:
        # Test different priorities
        audio.announce("Testing low priority announcement", Priority.LOW)
        time.sleep(0.5)

        audio.announce("Testing medium priority announcement", Priority.MEDIUM)
        time.sleep(0.5)

        audio.announce("Testing high priority announcement", Priority.HIGH)
        time.sleep(0.5)

        audio.emergency_announce("Emergency! This is a critical alert!")

        # Wait for completion
        audio.wait_until_done()

        # Test specialized announcements
        audio.obstacle_alert(50, "ahead")
        audio.person_detected("John")
        audio.object_detected(["chair", "table", "bottle"])
        audio.currency_detected("20", "dollars")
        audio.color_detected("blue")

        # Wait for all announcements
        audio.wait_until_done()

        # Print stats
        stats = audio.get_stats()
        print(f"\nStats: {stats}")


if __name__ == "__main__":
    test_audio()
