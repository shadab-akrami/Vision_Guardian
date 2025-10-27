#!/usr/bin/env python3
"""
Minimal Camera Test - No Processing Whatsoever
Just opens camera and displays raw feed
"""

import cv2
import sys

def test_all_cameras():
    """Test all available camera devices"""
    print("=" * 70)
    print("MINIMAL CAMERA TEST - NO PROCESSING")
    print("=" * 70)
    print("\nThis script tests cameras with ZERO processing.")
    print("If this works, the issue is in VisionGuardian's processing pipeline.")
    print("If this doesn't work, the issue is camera hardware/drivers.\n")

    working_devices = []

    # Test devices 0-3
    for device_id in range(4):
        print(f"\n[Testing Device {device_id}]")
        print("-" * 40)

        cap = cv2.VideoCapture(device_id)

        if not cap.isOpened():
            print(f"  ✗ Cannot open device {device_id}")
            continue

        print(f"  ✓ Device {device_id} opened successfully")

        # Get properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        print(f"  Resolution: {width}x{height} @ {fps} FPS")

        # Warm up camera
        print(f"  Warming up (30 frames)...")
        for i in range(30):
            cap.read()

        # Test read
        ret, frame = cap.read()

        if not ret or frame is None:
            print(f"  ✗ Cannot read frames from device {device_id}")
            cap.release()
            continue

        print(f"  ✓ Frame captured successfully")
        print(f"  Frame shape: {frame.shape}")
        print(f"  Frame dtype: {frame.dtype}")
        print(f"  Pixel range: {frame.min()} to {frame.max()}")

        # Check frame validity
        if frame.max() == 0:
            print(f"  ⚠️  WARNING: Frame is all BLACK (all zeros)")
        elif frame.min() == frame.max():
            print(f"  ⚠️  WARNING: Frame is UNIFORM (all pixels same value)")
        else:
            print(f"  ✓ Frame has VALID data")
            working_devices.append(device_id)

        cap.release()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if not working_devices:
        print("\n❌ NO WORKING CAMERAS FOUND")
        print("\nTroubleshooting:")
        print("  1. Check camera is properly connected")
        print("  2. Try: ls /dev/video*")
        print("  3. Try: v4l2-ctl --list-devices")
        print("  4. Check permissions: ls -l /dev/video0")
        print("  5. Add user to video group: sudo usermod -a -G video $USER")
        return None

    print(f"\n✓ Found {len(working_devices)} working camera(s): {working_devices}")
    print(f"\nRecommended device_id: {working_devices[0]}")

    return working_devices

def display_camera(device_id):
    """Display live feed from camera"""
    print(f"\n" + "=" * 70)
    print(f"DISPLAYING CAMERA {device_id}")
    print("=" * 70)
    print("\nOpening camera with ZERO processing...")
    print("This is PURE RAW camera feed - exactly as camera captures it.")
    print("\nControls:")
    print("  Press 'q' to quit")
    print("  Press 'n' to try next camera")
    print("\n")

    cap = cv2.VideoCapture(device_id)

    if not cap.isOpened():
        print(f"❌ Cannot open camera {device_id}")
        return False

    # Warm up
    for _ in range(30):
        cap.read()

    print("✓ Camera ready! Opening window...\n")

    try:
        cv2.namedWindow(f"Camera {device_id} - RAW FEED", cv2.WINDOW_NORMAL)
        cv2.resizeWindow(f"Camera {device_id} - RAW FEED", 800, 600)
    except Exception as e:
        print(f"⚠️  Cannot create window: {e}")
        print("You may be running headless. Try with display enabled.")
        cap.release()
        return False

    frame_count = 0

    while True:
        ret, frame = cap.read()

        if not ret or frame is None:
            print(f"⚠️  Frame {frame_count}: Read failed")
            continue

        frame_count += 1

        # ZERO PROCESSING - Just add frame counter
        info_text = f"Frame: {frame_count} | Device: {device_id} | Press 'q' to quit, 'n' for next camera"
        cv2.putText(frame, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Show pixel range every 30 frames
        if frame_count % 30 == 0:
            print(f"  Frame {frame_count}: min={frame.min()}, max={frame.max()}")

        try:
            cv2.imshow(f"Camera {device_id} - RAW FEED", frame)
        except Exception as e:
            print(f"❌ Display error: {e}")
            break

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # q or ESC
            print(f"\n✓ Closed camera {device_id}")
            break
        elif key == ord('n'):  # next camera
            print(f"\n→ Switching to next camera...")
            break

    cap.release()
    cv2.destroyAllWindows()
    return True

def main():
    print("\n🎥 VisionGuardian - Minimal Camera Test\n")

    # First, detect all cameras
    working_devices = test_all_cameras()

    if not working_devices:
        print("\n❌ Cannot proceed - no working cameras found")
        sys.exit(1)

    # Ask user which camera to display
    print("\n" + "=" * 70)
    print("DISPLAY TEST")
    print("=" * 70)

    if len(working_devices) == 1:
        print(f"\nOnly one camera found: device {working_devices[0]}")
        print("Will display this camera...")
        input("\nPress Enter to continue...")
        display_camera(working_devices[0])
    else:
        print(f"\nMultiple cameras found: {working_devices}")

        # Display each working camera
        for device_id in working_devices:
            print(f"\n→ Testing device {device_id}...")
            input(f"Press Enter to display camera {device_id}...")

            display_camera(device_id)

            if device_id != working_devices[-1]:
                try:
                    choice = input("\nTry next camera? (y/n): ").strip().lower()
                    if choice != 'y':
                        break
                except KeyboardInterrupt:
                    break

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("\nResults:")
    print(f"  Working cameras: {working_devices}")
    print(f"\nIf you saw COLORS in the display:")
    print(f"  → Camera hardware is WORKING")
    print(f"  → Issue is in VisionGuardian's processing pipeline")
    print(f"  → Update config/settings.yaml with working device_id: {working_devices[0]}")
    print(f"\nIf you saw GREY in the display:")
    print(f"  → Camera hardware/driver issue")
    print(f"  → Check camera connections and drivers")
    print(f"  → Try different USB port")
    print("\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
