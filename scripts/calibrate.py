#!/usr/bin/env python3
"""
Calibration tool for VisionGuardian
Calibrates camera for distance estimation
"""

import sys
import cv2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils import Config, setup_logging
from camera_handler import CameraHandler
from obstacle_detection import ObstacleDetection


def calibrate_camera():
    """Calibrate camera focal length for distance estimation"""

    print("=" * 60)
    print("VisionGuardian - Camera Calibration")
    print("=" * 60)
    print()
    print("This tool helps calibrate the camera for accurate distance estimation")
    print()

    # Setup
    setup_logging("INFO", "calibration.log")
    config = Config()

    # Initialize camera
    camera = CameraHandler(config)
    if not camera.initialize():
        print("Failed to initialize camera")
        return 1

    camera.start_capture()

    # Initialize obstacle detection
    obstacle_det = ObstacleDetection(config)
    obstacle_det.initialize()

    print("Instructions:")
    print("  1. Place an object at a known distance (e.g., 100cm)")
    print("  2. Ensure the object is clearly visible in the center of frame")
    print("  3. Press 'c' to capture and measure")
    print("  4. Press 'q' to quit")
    print()

    try:
        while True:
            frame = camera.get_current_frame()

            if frame is not None:
                # Draw center crosshair
                h, w = frame.shape[:2]
                cv2.line(frame, (w//2 - 20, h//2), (w//2 + 20, h//2), (0, 255, 0), 2)
                cv2.line(frame, (w//2, h//2 - 20), (w//2, h//2 + 20), (0, 255, 0), 2)

                cv2.putText(frame, "Press 'c' to calibrate, 'q' to quit",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                cv2.imshow('Calibration', frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif key == ord('c'):
                if frame is not None:
                    print()
                    print("Enter the actual distance to the object (in cm): ", end='')
                    try:
                        actual_distance = float(input())

                        # Detect object width
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        edges = cv2.Canny(gray, 50, 150)
                        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                        if contours:
                            # Find largest contour near center
                            largest_contour = max(contours, key=cv2.contourArea)
                            x, y, width, height = cv2.boundingRect(largest_contour)

                            if width > 0:
                                # Calibrate
                                obstacle_det.calibrate_camera(actual_distance, width)

                                print()
                                print(f"Calibration successful!")
                                print(f"Focal length: {obstacle_det.focal_length:.2f} pixels")
                                print()
                                print("Save this focal length to config/settings.yaml")
                                print("under obstacle_detection settings")
                                print()
                            else:
                                print("Could not detect object width")
                        else:
                            print("No objects detected. Try again.")

                    except ValueError:
                        print("Invalid distance value")

    finally:
        camera.release()
        cv2.destroyAllWindows()

    return 0


def calibrate_audio():
    """Calibrate audio output"""
    print("=" * 60)
    print("Audio Calibration")
    print("=" * 60)
    print()

    setup_logging("INFO")
    config = Config()

    from audio_output import AudioOutput

    audio = AudioOutput(config)
    if not audio.initialize():
        print("Failed to initialize audio")
        return 1

    print("Testing audio output...")
    print()

    speeds = [120, 150, 180, 200]

    for speed in speeds:
        audio.tts_engine.setProperty('rate', speed)
        print(f"Testing voice speed: {speed} WPM")
        audio.announce(f"This is a test at {speed} words per minute", Priority.HIGH)
        audio.wait_until_done()

    print()
    print("Audio test complete")
    print("Update voice_speed in config/settings.yaml with your preferred speed")
    print()

    audio.shutdown()
    return 0


def main():
    print("VisionGuardian Calibration Tool")
    print()
    print("Select calibration type:")
    print("  1. Camera (distance estimation)")
    print("  2. Audio (voice speed)")
    print("  q. Quit")
    print()
    print("Choice: ", end='')

    choice = input().strip().lower()

    if choice == '1':
        return calibrate_camera()
    elif choice == '2':
        return calibrate_audio()
    else:
        print("Cancelled")
        return 0


if __name__ == "__main__":
    sys.exit(main())
