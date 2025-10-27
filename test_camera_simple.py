#!/usr/bin/env python3
"""
Simple Camera Test - Diagnose camera issues
No color correction, no processing - just raw camera feed
"""

import cv2
import numpy as np
import sys

def test_camera():
    print("=" * 60)
    print("Simple Camera Test")
    print("=" * 60)

    # Try to open camera
    print("\n[1/4] Opening camera...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ FAILED: Cannot open camera")
        print("\nTroubleshooting:")
        print("  1. Check camera is connected")
        print("  2. Try: ls /dev/video*")
        print("  3. Try: v4l2-ctl --list-devices")
        return False

    print("✅ Camera opened successfully")

    # Get camera properties
    print("\n[2/4] Camera properties:")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps}")

    # Try to read a frame
    print("\n[3/4] Reading test frame...")
    ret, frame = cap.read()

    if not ret or frame is None:
        print("❌ FAILED: Cannot read frame")
        print("\nFrame read returned:", ret)
        print("Frame is None:", frame is None)
        cap.release()
        return False

    print("✅ Frame read successfully")
    print(f"  Frame shape: {frame.shape}")
    print(f"  Frame dtype: {frame.dtype}")
    print(f"  Frame min/max: {frame.min()}/{frame.max()}")

    # Check if frame is all zeros (grey)
    if frame.max() == 0:
        print("⚠️  WARNING: Frame is all black (zeros)")
    elif frame.min() == frame.max():
        print("⚠️  WARNING: Frame is uniform (all same value)")
    else:
        print("✅ Frame has valid data")

    # Display test
    print("\n[4/4] Display test...")
    print("  Opening window (press 'q' to quit)...")

    try:
        cv2.namedWindow("Camera Test", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Camera Test", 800, 600)
    except Exception as e:
        print(f"⚠️  WARNING: Cannot create window: {e}")
        print("  You may be running headless or without display")
        print("  This is OK - camera is working!")
        cap.release()
        return True

    frame_count = 0
    print("\n✅ Camera is working! Press 'q' to quit")
    print("\nWhat you should see:")
    print("  - Live video feed from camera")
    print("  - Natural colors (same as on Windows)")
    print("  - Smooth motion")

    while True:
        ret, frame = cap.read()

        if not ret or frame is None:
            print(f"\n⚠️  Frame {frame_count}: Failed to read")
            continue

        frame_count += 1

        # Add info overlay
        text = f"Frame: {frame_count} | Press 'q' to quit"
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                   0.7, (0, 255, 0), 2)

        # Display info every 30 frames
        if frame_count % 30 == 0:
            print(f"  Frame {frame_count}: OK (min={frame.min()}, max={frame.max()})")

        try:
            cv2.imshow("Camera Test", frame)
        except Exception as e:
            print(f"❌ Display error: {e}")
            break

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # q or ESC
            print("\n✅ Test completed successfully!")
            break

    cap.release()
    cv2.destroyAllWindows()
    return True

def diagnose_grey_screen():
    """Diagnose why screen might be grey"""
    print("\n" + "=" * 60)
    print("GREY SCREEN DIAGNOSTICS")
    print("=" * 60)

    print("\nCommon causes of grey/black screen:")
    print("  1. Camera not capturing (check cables)")
    print("  2. Wrong camera device (try device_id: 1 instead of 0)")
    print("  3. Camera needs warm-up time")
    print("  4. Permissions issue (check /dev/video0)")
    print("  5. Display server not running (X11/Wayland)")

    print("\nQuick checks:")

    # Check video devices
    import subprocess
    try:
        result = subprocess.run(['ls', '/dev/video*'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ Video devices found: {result.stdout.strip()}")
        else:
            print(f"  ❌ No video devices found")
    except:
        print("  ⚠️  Cannot check video devices (ls not available)")

    # Check v4l2
    try:
        result = subprocess.run(['v4l2-ctl', '--list-devices'],
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            print(f"  ✅ v4l2-ctl output:\n{result.stdout}")
        else:
            print(f"  ❌ v4l2-ctl failed")
    except:
        print("  ⚠️  v4l2-ctl not available")

    print("\nTrying different camera devices...")
    for device_id in range(3):
        cap = cv2.VideoCapture(device_id)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"  ✅ Device {device_id}: Working! (resolution: {frame.shape})")
                if frame.max() > 0:
                    print(f"     Has valid data (max pixel value: {frame.max()})")
                else:
                    print(f"     ⚠️  Data is all zeros (might need warm-up)")
            else:
                print(f"  ⚠️  Device {device_id}: Opened but cannot read frames")
            cap.release()
        else:
            print(f"  ❌ Device {device_id}: Cannot open")

def main():
    print("\n🔍 VisionGuardian Camera Diagnostic Tool\n")

    # First run diagnostics
    diagnose_grey_screen()

    print("\n" + "=" * 60)
    input("\nPress Enter to start camera test...")

    # Then test camera
    success = test_camera()

    if not success:
        print("\n" + "=" * 60)
        print("TROUBLESHOOTING STEPS")
        print("=" * 60)
        print("""
1. Check camera connection:
   lsusb                    # See if camera is detected
   v4l2-ctl --list-devices  # List video devices

2. Check permissions:
   ls -l /dev/video0        # Check permissions
   sudo usermod -a -G video $USER  # Add user to video group
   # Then logout and login again

3. Try different camera:
   # Edit config/settings.yaml
   camera:
     device_id: 1  # Try 1 instead of 0

4. Test camera directly:
   ffplay /dev/video0       # Test with ffplay

5. Check for conflicts:
   fuser /dev/video0        # See if another program is using camera

6. Restart camera:
   sudo rmmod uvcvideo      # Remove driver
   sudo modprobe uvcvideo   # Reload driver
""")
    else:
        print("\n✅ Camera is working properly!")
        print("\nIf VisionGuardian still shows grey:")
        print("  1. Check that camera device_id is correct in config")
        print("  2. Make sure display server is running (not SSH without X11)")
        print("  3. Try: export DISPLAY=:0 before running")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
