"""
Facial Recognition Module for VisionGuardian
Recognizes and announces familiar people
Optimized for Raspberry Pi 5 (64-bit ARM64)
"""

import cv2
import numpy as np
import logging
import pickle
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logging.warning("face_recognition library not available")

from utils import Config, DATA_DIR, get_timestamp, PerformanceMonitor


class FacialRecognition:
    """Handles facial recognition for identifying known people"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.FacialRecognition')

        if not FACE_RECOGNITION_AVAILABLE:
            self.logger.error("face_recognition not available - module disabled")
            self.enabled = False
            return

        # Settings
        self.enabled = config.get('facial_recognition.enabled', True)
        self.model = config.get('facial_recognition.model', 'hog')
        self.tolerance = config.get('facial_recognition.tolerance', 0.6)
        self.max_faces = config.get('facial_recognition.max_faces_in_frame', 5)
        self.announce_unknown = config.get('facial_recognition.announce_unknown', False)
        self.save_unknown = config.get('facial_recognition.save_unknown_faces', False)

        # Data paths
        self.known_faces_dir = DATA_DIR / 'known_faces'
        self.unknown_faces_dir = DATA_DIR / 'unknown_faces'
        self.encodings_file = DATA_DIR / 'face_encodings.pkl'

        # Create directories
        self.known_faces_dir.mkdir(parents=True, exist_ok=True)
        if self.save_unknown:
            self.unknown_faces_dir.mkdir(parents=True, exist_ok=True)

        # Known faces database
        self.known_face_encodings = []
        self.known_face_names = []

        # Recognition tracking
        self.last_recognition_time = {}
        self.recognition_interval = config.get('facial_recognition.recognition_interval_seconds', 2)

        # Performance
        self.performance = PerformanceMonitor()

    def initialize(self) -> bool:
        """
        Load known faces and encodings

        Returns:
            True if successful
        """
        if not self.enabled or not FACE_RECOGNITION_AVAILABLE:
            return False

        try:
            self.logger.info("Initializing facial recognition...")

            # Try to load existing encodings
            if self.encodings_file.exists():
                self.logger.info("Loading existing face encodings...")
                self._load_encodings()
            else:
                self.logger.info("Training face encodings from images...")
                self._train_from_directory()

            self.logger.info(f"Loaded {len(self.known_face_names)} known faces")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing facial recognition: {e}")
            return False

    def _train_from_directory(self) -> bool:
        """
        Train face encodings from known_faces directory

        Directory structure:
        known_faces/
            person1/
                image1.jpg
                image2.jpg
            person2/
                image1.jpg
        """
        self.known_face_encodings = []
        self.known_face_names = []

        try:
            # Iterate through person directories
            for person_dir in self.known_faces_dir.iterdir():
                if not person_dir.is_dir():
                    continue

                person_name = person_dir.name
                self.logger.info(f"Training faces for: {person_name}")

                # Process each image for this person
                for image_path in person_dir.glob('*.jpg'):
                    try:
                        # Load image
                        image = face_recognition.load_image_file(str(image_path))

                        # Get face encodings
                        encodings = face_recognition.face_encodings(image, model=self.model)

                        if encodings:
                            # Use first face found
                            self.known_face_encodings.append(encodings[0])
                            self.known_face_names.append(person_name)
                            self.logger.info(f"  Added encoding from {image_path.name}")
                        else:
                            self.logger.warning(f"  No face found in {image_path.name}")

                    except Exception as e:
                        self.logger.error(f"  Error processing {image_path}: {e}")

            # Save encodings
            if self.known_face_encodings:
                self._save_encodings()
                self.logger.info(f"Trained {len(self.known_face_encodings)} face encodings")
                return True
            else:
                self.logger.warning("No faces trained")
                return False

        except Exception as e:
            self.logger.error(f"Error training faces: {e}")
            return False

    def _save_encodings(self):
        """Save face encodings to file"""
        try:
            data = {
                'encodings': self.known_face_encodings,
                'names': self.known_face_names
            }
            with open(self.encodings_file, 'wb') as f:
                pickle.dump(data, f)
            self.logger.info(f"Saved encodings to {self.encodings_file}")
        except Exception as e:
            self.logger.error(f"Error saving encodings: {e}")

    def _load_encodings(self):
        """Load face encodings from file"""
        try:
            with open(self.encodings_file, 'rb') as f:
                data = pickle.load(f)
            self.known_face_encodings = data['encodings']
            self.known_face_names = data['names']
            self.logger.info(f"Loaded {len(self.known_face_names)} face encodings")
        except Exception as e:
            self.logger.error(f"Error loading encodings: {e}")

    def recognize_faces(self, frame: np.ndarray) -> List[Dict]:
        """
        Recognize faces in frame

        Args:
            frame: Input frame (BGR format)

        Returns:
            List of recognized faces with info
        """
        if not self.enabled or not FACE_RECOGNITION_AVAILABLE:
            return []

        self.performance.start('face_recognition')
        recognized_faces = []

        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Detect face locations
            face_locations = face_recognition.face_locations(
                rgb_frame,
                model=self.model,
                number_of_times_to_upsample=1
            )

            if not face_locations:
                self.performance.end('face_recognition')
                return []

            # Limit number of faces
            face_locations = face_locations[:self.max_faces]

            # Get face encodings
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            # Match faces
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                name = "Unknown"
                confidence = 0.0

                if self.known_face_encodings:
                    # Compare with known faces
                    matches = face_recognition.compare_faces(
                        self.known_face_encodings,
                        face_encoding,
                        tolerance=self.tolerance
                    )

                    # Calculate face distances
                    face_distances = face_recognition.face_distance(
                        self.known_face_encodings,
                        face_encoding
                    )

                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)

                        if matches[best_match_index]:
                            name = self.known_face_names[best_match_index]
                            confidence = 1.0 - face_distances[best_match_index]

                # Check if we should announce this person
                announce = self._should_announce(name)

                face_info = {
                    'name': name,
                    'confidence': confidence,
                    'location': (top, right, bottom, left),
                    'announce': announce,
                    'is_known': name != "Unknown"
                }

                recognized_faces.append(face_info)

                # Save unknown face if enabled
                if name == "Unknown" and self.save_unknown:
                    self._save_unknown_face(frame, (top, right, bottom, left))

        except Exception as e:
            self.logger.error(f"Error recognizing faces: {e}")

        self.performance.end('face_recognition')
        return recognized_faces

    def _should_announce(self, name: str) -> bool:
        """
        Check if person should be announced based on time interval

        Args:
            name: Person's name

        Returns:
            True if should announce
        """
        current_time = time.time()

        # Check if enough time has passed since last announcement
        if name in self.last_recognition_time:
            time_since_last = current_time - self.last_recognition_time[name]
            if time_since_last < self.recognition_interval:
                return False

        # Check announcement settings
        if name == "Unknown" and not self.announce_unknown:
            return False

        # Update last recognition time
        self.last_recognition_time[name] = current_time
        return True

    def _save_unknown_face(self, frame: np.ndarray, location: Tuple[int, int, int, int]):
        """Save unknown face image"""
        try:
            top, right, bottom, left = location

            # Extract face region with some padding
            padding = 20
            face_img = frame[
                max(0, top-padding):min(frame.shape[0], bottom+padding),
                max(0, left-padding):min(frame.shape[1], right+padding)
            ]

            # Save with timestamp
            timestamp = get_timestamp()
            filename = self.unknown_faces_dir / f"unknown_{timestamp}.jpg"
            cv2.imwrite(str(filename), face_img)
            self.logger.debug(f"Saved unknown face: {filename.name}")

        except Exception as e:
            self.logger.error(f"Error saving unknown face: {e}")

    def add_known_face(self, name: str, image_path: str) -> bool:
        """
        Add a new known face to the database

        Args:
            name: Person's name
            image_path: Path to face image

        Returns:
            True if successful
        """
        try:
            # Create person directory
            person_dir = self.known_faces_dir / name
            person_dir.mkdir(exist_ok=True)

            # Load and encode face
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image, model=self.model)

            if not encodings:
                self.logger.error(f"No face found in {image_path}")
                return False

            # Add to database
            self.known_face_encodings.append(encodings[0])
            self.known_face_names.append(name)

            # Copy image to person directory
            import shutil
            dest_path = person_dir / Path(image_path).name
            shutil.copy(image_path, dest_path)

            # Save encodings
            self._save_encodings()

            self.logger.info(f"Added {name} to known faces")
            return True

        except Exception as e:
            self.logger.error(f"Error adding known face: {e}")
            return False

    def remove_known_face(self, name: str) -> bool:
        """
        Remove a person from known faces database

        Args:
            name: Person's name

        Returns:
            True if successful
        """
        try:
            # Remove from lists
            indices_to_remove = [i for i, n in enumerate(self.known_face_names) if n == name]

            for index in sorted(indices_to_remove, reverse=True):
                del self.known_face_encodings[index]
                del self.known_face_names[index]

            # Save updated encodings
            self._save_encodings()

            self.logger.info(f"Removed {name} from known faces ({len(indices_to_remove)} encodings)")
            return True

        except Exception as e:
            self.logger.error(f"Error removing known face: {e}")
            return False

    def get_known_people(self) -> List[str]:
        """Get list of known people"""
        return list(set(self.known_face_names))

    def draw_faces(self, frame: np.ndarray, faces: List[Dict]) -> np.ndarray:
        """
        Draw face boxes and labels on frame

        Args:
            frame: Input frame
            faces: List of face info dicts

        Returns:
            Frame with faces drawn
        """
        for face in faces:
            top, right, bottom, left = face['location']
            name = face['name']
            confidence = face['confidence']

            # Draw box
            color = (0, 255, 0) if face['is_known'] else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            # Draw label
            label = f"{name}"
            if face['is_known']:
                label += f" ({confidence:.2f})"

            cv2.rectangle(frame, (left, bottom - 25), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, label, (left + 6, bottom - 6),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return frame

    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        return self.performance.get_stats('face_recognition')


if __name__ == "__main__":
    # Test facial recognition
    from utils import setup_logging
    setup_logging("INFO", "face_test.log")

    config = Config()
    face_rec = FacialRecognition(config)

    if face_rec.initialize():
        print(f"Known people: {face_rec.get_known_people()}")
        print("\nPlace sample images in data/known_faces/[person_name]/ directory")
        print("Then run training again")
    else:
        print("Failed to initialize facial recognition")
