#!/usr/bin/env python3
"""
Train facial recognition encodings from known faces
Usage: python3 train_faces.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils import Config, setup_logging, DATA_DIR
from facial_recognition import FacialRecognition


def main():
    print("=" * 60)
    print("VisionGuardian - Facial Recognition Training")
    print("=" * 60)
    print()

    # Setup logging
    setup_logging("INFO", "face_training.log")

    # Load config
    config = Config()

    # Initialize facial recognition
    face_rec = FacialRecognition(config)

    print(f"Known faces directory: {face_rec.known_faces_dir}")
    print()

    # Check for face directories
    known_faces_dir = DATA_DIR / 'known_faces'
    person_dirs = [d for d in known_faces_dir.iterdir() if d.is_dir()]

    if not person_dirs:
        print("No person directories found!")
        print()
        print("Please create directories and add photos:")
        print(f"  {known_faces_dir}/person_name/photo1.jpg")
        print(f"  {known_faces_dir}/person_name/photo2.jpg")
        print()
        return 1

    print(f"Found {len(person_dirs)} person directories:")
    for person_dir in person_dirs:
        photo_count = len(list(person_dir.glob('*.jpg')))
        print(f"  - {person_dir.name}: {photo_count} photos")

    print()
    print("Start training? (y/n): ", end='')
    response = input().strip().lower()

    if response != 'y':
        print("Training cancelled")
        return 0

    print()
    print("Training facial recognition models...")
    print("This may take a few minutes...")
    print()

    # Train faces
    success = face_rec._train_from_directory()

    if success:
        print()
        print("=" * 60)
        print("Training completed successfully!")
        print("=" * 60)
        print()
        print(f"Trained {len(face_rec.known_face_encodings)} face encodings")
        print(f"Known people: {', '.join(face_rec.get_known_people())}")
        print()
        print(f"Encodings saved to: {face_rec.encodings_file}")
        print()
        return 0
    else:
        print()
        print("Training failed! Check logs for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
