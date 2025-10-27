#!/usr/bin/env python3
"""
Camera Backend Diagnostic Tool
Tests all available camera backends and displays results
"""

import sys
import cv2
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def test_picamera2():
    """Test picamera2 backend (Raspberry Pi Camera Module)"""
    print(f"\n{BLUE}[1/3] Testing picamera2 (Raspberry Pi Camera Module)...{RESET}")

    try:
        from picamera2 import Picamera2
        print(f"  {GREEN}✓{RESET} picamera2 library installed")

        try:
            picam2 = Picamera2()
            config = picam2.create_preview_configuration(
                main={"size": (640, 480), "format": "RGB888"}
            )
            picam2.configure(config)
            picam2.start()

            # Capture test frame
            import time
            time.sleep(0.5)
            frame = picam2.capture_array()

            if frame is not None and frame.size > 0:
                # Check frame quality
                if frame.max() == 0:
                    print(f"  {RED}✗{RESET} Camera producing black frames")
                    result = False
                elif frame.min() == frame.max():
                    print(f"  {RED}✗{RESET} Camera producing uniform frames (all {frame.min()})")
                    result = False
                else:
                    print(f"  {GREEN}✓{RESET} Camera working! Pixel range: {frame.min()}-{frame.max()}")
                    print(f"  {GREEN}✓{RESET} Resolution: {frame.shape[1]}x{frame.shape[0]}")
                    result = True
            else:
                print(f"  {RED}✗{RESET} Failed to capture frame")
                result = False

            picam2.stop()
            picam2.close()
            return result

        except Exception as e:
            print(f"  {RED}✗{RESET} Failed to initialize: {e}")
            return False

    except ImportError:
        print(f"  {YELLOW}!{RESET} picamera2 not installed")
        print(f"    Install with: {BLUE}pip install picamera2{RESET}")
        return False

def test_opencv_backend(device_id, backend, backend_name):
    """Test OpenCV with specific backend"""
    try:
        camera = cv2.VideoCapture(device_id, backend)

        if not camera.isOpened():
            return False

        # Set resolution
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Warm up and test
        for i in range(5):
            ret, frame = camera.read()
            if not ret or frame is None:
                continue

            if i == 4:  # Last frame
                if frame.max() == 0:
                    print(f"    Device {device_id}: {RED}✗{RESET} Black frames")
                    camera.release()
                    return False
                elif frame.min() == frame.max():
                    print(f"    Device {device_id}: {RED}✗{RESET} Uniform frames (all {frame.min()})")
                    camera.release()
                    return False
                else:
                    actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"    Device {device_id}: {GREEN}✓{RESET} Working! {actual_width}x{actual_height}, pixels: {frame.min()}-{frame.max()}")
                    camera.release()
                    return True

        camera.release()
        return False

    except Exception as e:
        return False

def test_opencv_v4l2():
    """Test OpenCV with V4L2 backend"""
    print(f"\n{BLUE}[2/3] Testing OpenCV with V4L2 backend...{RESET}")

    found_any = False
    for device_id in [0, 1, 2, 3]:
        if test_opencv_backend(device_id, cv2.CAP_V4L2, "V4L2"):
            found_any = True

    if found_any:
        print(f"  {GREEN}✓{RESET} V4L2 backend working")
    else:
        print(f"  {RED}✗{RESET} V4L2 backend not working on any device")

    return found_any

def test_opencv_any():
    """Test OpenCV with generic backend"""
    print(f"\n{BLUE}[3/3] Testing OpenCV with generic backend...{RESET}")

    found_any = False
    for device_id in [0, 1, 2, 3]:
        if test_opencv_backend(device_id, cv2.CAP_ANY, "ANY"):
            found_any = True

    if found_any:
        print(f"  {GREEN}✓{RESET} Generic backend working")
    else:
        print(f"  {RED}✗{RESET} Generic backend not working on any device")

    return found_any

def main():
    print("=" * 70)
    print(f"{BLUE}VisionGuardian Camera Backend Diagnostic Tool{RESET}")
    print("=" * 70)
    print(f"This tool tests all available camera backends on your system.")
    print(f"It will help identify which camera method works best.")
    print()

    results = {
        'picamera2': False,
        'v4l2': False,
        'generic': False
    }

    # Test all backends
    results['picamera2'] = test_picamera2()
    results['v4l2'] = test_opencv_v4l2()
    results['generic'] = test_opencv_any()

    # Summary
    print("\n" + "=" * 70)
    print(f"{BLUE}SUMMARY{RESET}")
    print("=" * 70)

    working_backends = []
    if results['picamera2']:
        working_backends.append('picamera2')
    if results['v4l2']:
        working_backends.append('OpenCV V4L2')
    if results['generic']:
        working_backends.append('OpenCV Generic')

    if working_backends:
        print(f"{GREEN}✓ SUCCESS!{RESET} Working backends:")
        for backend in working_backends:
            print(f"  • {backend}")

        print(f"\n{GREEN}Your camera is ready to use!{RESET}")
        print(f"The application will automatically use the best available backend.")

    else:
        print(f"{RED}✗ NO WORKING BACKENDS FOUND{RESET}")
        print(f"\n{YELLOW}Troubleshooting steps:{RESET}")
        print(f"1. Check camera connection")
        print(f"2. For Raspberry Pi Camera Module:")
        print(f"   • Enable camera: {BLUE}sudo raspi-config{RESET} → Interface → Camera")
        print(f"   • Install picamera2: {BLUE}pip install picamera2{RESET}")
        print(f"   • Reboot: {BLUE}sudo reboot{RESET}")
        print(f"3. For USB cameras:")
        print(f"   • List devices: {BLUE}ls -l /dev/video*{RESET}")
        print(f"   • Check permissions: {BLUE}sudo usermod -a -G video $USER{RESET}")
        print(f"   • Re-login or reboot")
        print(f"4. Test camera with: {BLUE}libcamera-hello{RESET} (Pi Camera) or {BLUE}cheese{RESET} (USB)")

    print("=" * 70)

if __name__ == "__main__":
    main()
