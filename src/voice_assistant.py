"""
Voice Assistant Module for VisionGuardian
Handles voice commands and speech recognition
Optimized for Raspberry Pi 5
"""

import logging
import threading
import time
from typing import Optional, Callable, Dict

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    logging.warning("speech_recognition not available")

from utils import Config


class VoiceAssistant:
    """Handles voice commands and speech recognition"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.VoiceAssistant')

        if not SR_AVAILABLE:
            self.logger.error("speech_recognition not available")
            self.enabled = False
            return

        # Settings
        self.enabled = config.get('voice_assistant.enabled', True)
        self.wake_word = config.get('voice_assistant.wake_word', 'hey guardian')
        self.timeout = config.get('voice_assistant.timeout_seconds', 5)
        self.ambient_noise_duration = config.get('voice_assistant.ambient_noise_duration', 1)
        self.energy_threshold = config.get('voice_assistant.energy_threshold', 4000)

        # Speech recognizer
        self.recognizer = None
        self.microphone = None

        # Listening state
        self.is_listening = False
        self.listen_thread = None

        # Command callbacks
        self.command_callbacks = {}

        # Supported commands
        self.commands = {
            'read text': 'read_text',
            'what do you see': 'describe_scene',
            'who is here': 'identify_people',
            'what color': 'detect_color',
            'identify money': 'detect_currency',
            'any obstacles': 'check_obstacles',
            'help': 'show_help',
            'stop': 'stop_all',
            'exit': 'exit_app',
            'repeat': 'repeat_last',
        }

    def initialize(self) -> bool:
        """
        Initialize voice assistant

        Returns:
            True if successful
        """
        if not self.enabled or not SR_AVAILABLE:
            self.logger.warning("Voice assistant disabled or SpeechRecognition not available")
            return False

        try:
            self.logger.info("Initializing voice assistant...")

            # Initialize recognizer
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = self.energy_threshold

            # Initialize microphone
            try:
                self.microphone = sr.Microphone()
            except Exception as mic_error:
                self.logger.error(f"No microphone found: {mic_error}")
                self.logger.info("Voice commands will not be available")
                self.microphone = None
                self.enabled = False
                return False

            # Adjust for ambient noise
            with self.microphone as source:
                self.logger.info("Calibrating for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=self.ambient_noise_duration)

            self.logger.info(f"Voice assistant initialized (wake word: '{self.wake_word}')")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing voice assistant: {e}")
            self.logger.info("Voice commands will not be available. System will continue without voice control.")
            self.microphone = None
            self.enabled = False
            return False

    def start_listening(self):
        """Start listening for voice commands in background"""
        if not self.enabled or self.is_listening:
            return

        # Check if microphone is available
        if self.microphone is None:
            self.logger.warning("Cannot start listening: microphone not available")
            return

        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        self.logger.info("Started listening for voice commands")

    def stop_listening(self):
        """Stop listening for voice commands"""
        self.is_listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2)
        self.logger.info("Stopped listening")

    def _listen_loop(self):
        """Main listening loop"""
        while self.is_listening:
            try:
                # Listen for wake word
                command = self._listen_for_command()

                if command:
                    self.logger.info(f"Heard command: {command}")

                    # Check if it's a wake word
                    if self.wake_word.lower() in command.lower():
                        self._execute_callback('wake_word_detected')

                        # Listen for actual command
                        time.sleep(0.5)
                        actual_command = self._listen_for_command()

                        if actual_command:
                            self._process_command(actual_command)
                    else:
                        # Direct command without wake word
                        self._process_command(command)

            except Exception as e:
                self.logger.error(f"Error in listen loop: {e}")
                time.sleep(1)

    def _listen_for_command(self) -> Optional[str]:
        """
        Listen for and recognize voice command

        Returns:
            Recognized text or None
        """
        # Check if microphone is available
        if self.microphone is None:
            self.logger.debug("Microphone not available")
            return None

        try:
            with self.microphone as source:
                # Listen
                audio = self.recognizer.listen(source, timeout=self.timeout, phrase_time_limit=5)

            # Recognize speech using Google Speech Recognition
            try:
                text = self.recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                self.logger.debug("Could not understand audio")
                return None
            except sr.RequestError as e:
                self.logger.error(f"Speech recognition error: {e}")
                return None

        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            self.logger.error(f"Error listening: {e}")
            return None

    def _process_command(self, command: str):
        """
        Process recognized command

        Args:
            command: Command text
        """
        command_lower = command.lower()

        # Find matching command
        for keyword, action in self.commands.items():
            if keyword in command_lower:
                self.logger.info(f"Executing action: {action}")
                self._execute_callback(action, command)
                return

        # No matching command
        self.logger.warning(f"Unknown command: {command}")
        self._execute_callback('unknown_command', command)

    def _execute_callback(self, action: str, command: str = None):
        """Execute registered callback for action"""
        if action in self.command_callbacks:
            try:
                callback = self.command_callbacks[action]
                if command:
                    callback(command)
                else:
                    callback()
            except Exception as e:
                self.logger.error(f"Error executing callback for {action}: {e}")

    def register_command_callback(self, action: str, callback: Callable):
        """
        Register callback for command action

        Args:
            action: Action name
            callback: Callback function
        """
        self.command_callbacks[action] = callback
        self.logger.debug(f"Registered callback for: {action}")

    def listen_once(self) -> Optional[str]:
        """
        Listen for a single command (blocking)

        Returns:
            Recognized text or None
        """
        if not self.enabled:
            return None

        return self._listen_for_command()

    def get_available_commands(self) -> Dict[str, str]:
        """Get dictionary of available commands"""
        return self.commands.copy()

    def add_command(self, keyword: str, action: str):
        """
        Add custom command

        Args:
            keyword: Command keyword
            action: Action identifier
        """
        self.commands[keyword.lower()] = action
        self.logger.info(f"Added command: {keyword} -> {action}")


def test_voice_assistant():
    """Test voice assistant"""
    from utils import setup_logging

    setup_logging("INFO")
    config = Config()

    assistant = VoiceAssistant(config)

    if not assistant.initialize():
        print("Failed to initialize voice assistant")
        return

    print(f"Voice assistant ready!")
    print(f"Say '{assistant.wake_word}' followed by a command")
    print("\nAvailable commands:")
    for cmd in assistant.get_available_commands():
        print(f"  - {cmd}")
    print("\nListening...")

    # Register test callbacks
    def on_wake_word():
        print("Wake word detected! Listening for command...")

    def on_command(action):
        def handler(command=None):
            print(f"Action: {action}")
            if command:
                print(f"Command: {command}")

        return handler

    assistant.register_command_callback('wake_word_detected', on_wake_word)
    for action in assistant.get_available_commands().values():
        assistant.register_command_callback(action, on_command(action))

    # Start listening
    assistant.start_listening()

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        assistant.stop_listening()


if __name__ == "__main__":
    test_voice_assistant()
