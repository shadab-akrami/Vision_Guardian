#!/usr/bin/env python3
"""
Logitech USB Webcam Fix for Raspberry Pi
Diagnoses and fixes the uniform gray pixels issue
"""

import cv2
import numpy as np
import subprocess
import time

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def run_command(cmd):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout
    except:
        return ""

def check_video_devices():
    """Check available video devices"""
    print(f"\n{BLUE}[1/6] Checking video devices...{RESET}")

    output = run_command("ls -l /dev/video*")
    if output:
        print(f"{GREEN}✓ Video devices found:{RESET}")
        print(output)

        # Extract device numbers
        devices = []
        for line in output.split('\n'):
            if 'video' in line:
                parts = line.split('video')
                if len(parts) > 1:
                    try:
                        num = int(parts[1].split()[0])
                        devices.append(num)
                    except:
                        pass
        return sorted(set(devices))
    else:
        print(f"{RED}✗ No video devices found{RESET}")
        return []

def test_device_with_formats(device_id):
    """Test different pixel formats for a device"""
    print(f"\n  Testing /dev/video{device_id}...")

    # Try different backends and formats
    backends = [
        (cv2.CAP_V4L2, "V4L2"),
        (cv2.CAP_ANY, "ANY")
    ]

    # FOURCC codes to try
    formats = [
        (cv2.VideoWriter_fourcc(*'MJPG'), "MJPEG"),
        (cv2.VideoWriter_fourcc(*'YUYV'), "YUYV"),
        (None, "Default")
    ]

    for backend, backend_name in backends:
        for fmt_code, fmt_name in formats:
            try:
                camera = cv2.VideoCapture(device_id, backend)
                if not camera.isOpened():
                    continue

                # Set format if specified
                if fmt_code is not None:
                    camera.set(cv2.CAP_PROP_FOURCC, fmt_code)

                # Set resolution (Logitech C270 supports 720p)
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                camera.set(cv2.CAP_PROP_FPS, 30)

                # Try to set camera parameters
                try:
                    camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # Auto mode
                    camera.set(cv2.CAP_PROP_AUTO_WB, 1)  # Auto white balance
                except:
                    pass

                # Extended warm-up (USB cameras need time to stabilize!)
                # Discard first 30 frames
                for i in range(30):
                    ret, frame = camera.read()
                    if not ret:
                        break
                    time.sleep(0.1)  # Give camera time

                # Now test with multiple frames
                valid_frames = 0
                last_frame = None

                for i in range(5):
                    ret, frame = camera.read()
                    time.sleep(0.1)

                    if ret and frame is not None and frame.size > 0:
                        last_frame = frame
                        # Check if valid (not uniform)
                        if frame.max() > 0 and frame.min() != frame.max():
                            valid_frames += 1

                camera.release()

                # Need at least 3/5 valid frames
                if valid_frames >= 3 and last_frame is not None:
                    min_val = last_frame.min()
                    max_val = last_frame.max()
                    result = f"{GREEN}✓ WORKING! ({valid_frames}/5 valid, pixels: {min_val}-{max_val}){RESET}"
                    print(f"    {backend_name}/{fmt_name}: {result}")
                    return True, backend, backend_name, fmt_code, fmt_name
                elif last_frame is not None:
                    min_val = last_frame.min()
                    max_val = last_frame.max()
                    if max_val == 0:
                        result = f"{RED}BLACK{RESET}"
                    elif min_val == max_val:
                        b, g, r = last_frame[0, 0]
                        result = f"{RED}UNIFORM (R:{r} G:{g} B:{b}) - only {valid_frames}/5 valid{RESET}"
                    else:
                        result = f"{YELLOW}UNSTABLE (only {valid_frames}/5 valid){RESET}"
                    print(f"    {backend_name}/{fmt_name}: {result}")

            except Exception as e:
                pass

    return False, None, None, None, None

def find_working_camera():
    """Find a working camera configuration"""
    print(f"\n{BLUE}[2/6] Testing camera configurations...{RESET}")

    devices = check_video_devices()

    if not devices:
        return None

    for device_id in devices:
        success, backend, backend_name, fmt_code, fmt_name = test_device_with_formats(device_id)
        if success:
            print(f"\n{GREEN}✓ Found working configuration!{RESET}")
            print(f"  Device: /dev/video{device_id}")
            print(f"  Backend: {backend_name}")
            print(f"  Format: {fmt_name}")
            return {
                'device_id': device_id,
                'backend': backend,
                'backend_name': backend_name,
                'format': fmt_code,
                'format_name': fmt_name
            }

    return None

def apply_v4l2_settings(device_id):
    """Apply optimal V4L2 settings"""
    print(f"\n{BLUE}[3/6] Applying V4L2 settings...{RESET}")

    device = f"/dev/video{device_id}"

    # Check if v4l2-ctl is available
    if not run_command("which v4l2-ctl"):
        print(f"{YELLOW}! v4l2-ctl not found, installing...{RESET}")
        run_command("sudo apt install -y v4l-utils")

    settings = {
        'brightness': 128,
        'contrast': 128,
        'saturation': 128,
        'white_balance_temperature_auto': 1,
        'gain': 0,
        'power_line_frequency': 1,
        'sharpness': 128,
        'backlight_compensation': 0,
        'exposure_auto': 3,
        'exposure_absolute': 166,
    }

    for key, value in settings.items():
        cmd = f"v4l2-ctl -d {device} --set-ctrl={key}={value} 2>/dev/null"
        run_command(cmd)

    print(f"{GREEN}✓ V4L2 settings applied{RESET}")

def check_permissions():
    """Check and fix video group permissions"""
    print(f"\n{BLUE}[4/6] Checking permissions...{RESET}")

    output = run_command("groups")
    if 'video' in output:
        print(f"{GREEN}✓ User is in 'video' group{RESET}")
        return True
    else:
        print(f"{YELLOW}! User not in 'video' group{RESET}")
        print(f"{YELLOW}  Run: sudo usermod -a -G video $USER{RESET}")
        print(f"{YELLOW}  Then log out and log back in{RESET}")
        return False

def update_config(camera_config):
    """Update application config with working settings"""
    print(f"\n{BLUE}[5/6] Updating application config...{RESET}")

    config_file = "config/settings.yaml"

    try:
        with open(config_file, 'r') as f:
            lines = f.readlines()

        # Update device_id
        new_lines = []
        in_camera_section = False
        updated_device_id = False

        for line in lines:
            if 'camera:' in line and not line.strip().startswith('#'):
                in_camera_section = True
                new_lines.append(line)
            elif in_camera_section and 'device_id:' in line:
                indent = len(line) - len(line.lstrip())
                new_lines.append(' ' * indent + f"device_id: {camera_config['device_id']}  # Auto-detected working device\n")
                updated_device_id = True
            elif in_camera_section and line.strip() and not line.strip().startswith('#') and ':' in line:
                # Still in camera section
                new_lines.append(line)
            elif in_camera_section and (not line.strip() or (line.strip() and not line.strip().startswith('#') and ':' not in line)):
                # End of camera section
                in_camera_section = False
                new_lines.append(line)
            else:
                new_lines.append(line)

        if updated_device_id:
            with open(config_file, 'w') as f:
                f.writelines(new_lines)
            print(f"{GREEN}✓ Config updated: device_id set to {camera_config['device_id']}{RESET}")
        else:
            print(f"{YELLOW}! Could not update config automatically{RESET}")
            print(f"  Please manually set: camera.device_id: {camera_config['device_id']}")

    except Exception as e:
        print(f"{YELLOW}! Could not update config: {e}{RESET}")
        print(f"  Please manually set in {config_file}:")
        print(f"    camera:")
        print(f"      device_id: {camera_config['device_id']}")

def test_final():
    """Test the application camera handler"""
    print(f"\n{BLUE}[6/6] Testing with application...{RESET}")

    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent / 'src'))

        from utils import Config
        from camera_handler import CameraHandler

        config = Config()
        camera = CameraHandler(config)

        if camera.initialize():
            camera.start_capture()
            time.sleep(1)

            frame = camera.get_current_frame()
            if frame is not None:
                if frame.max() == 0:
                    print(f"{RED}✗ Still getting black frames{RESET}")
                    result = False
                elif frame.min() == frame.max():
                    print(f"{RED}✗ Still getting uniform frames{RESET}")
                    result = False
                else:
                    print(f"{GREEN}✓ Camera working in application! (pixels: {frame.min()}-{frame.max()}){RESET}")
                    result = True
            else:
                print(f"{RED}✗ No frame captured{RESET}")
                result = False

            camera.release()
            return result
        else:
            print(f"{RED}✗ Camera failed to initialize{RESET}")
            return False

    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        return False

def main():
    print("=" * 70)
    print(f"{BLUE}Logitech USB Webcam Fix for Raspberry Pi{RESET}")
    print("=" * 70)
    print("This tool will diagnose and fix the uniform gray pixels issue.")
    print()

    # Find working camera
    camera_config = find_working_camera()

    if not camera_config:
        print(f"\n{RED}✗ Could not find working camera configuration{RESET}")
        print(f"\n{YELLOW}Troubleshooting steps:{RESET}")
        print("1. Check USB connection - try different USB port")
        print("2. Check if camera works outside Python:")
        print(f"   {BLUE}cheese{RESET}  (install with: sudo apt install cheese)")
        print("3. Check USB power - Raspberry Pi may not provide enough power")
        print("   - Try powered USB hub")
        print("4. Check dmesg for USB errors:")
        print(f"   {BLUE}dmesg | grep -i usb{RESET}")
        print("5. Try rebooting:")
        print(f"   {BLUE}sudo reboot{RESET}")
        return

    # Apply V4L2 settings
    apply_v4l2_settings(camera_config['device_id'])

    # Check permissions
    perms_ok = check_permissions()

    # Update config
    update_config(camera_config)

    # Test with application
    if perms_ok:
        success = test_final()
    else:
        success = False
        print(f"\n{YELLOW}⚠ Skipping application test (fix permissions first){RESET}")

    # Summary
    print("\n" + "=" * 70)
    print(f"{BLUE}SUMMARY{RESET}")
    print("=" * 70)

    if success:
        print(f"{GREEN}✓ SUCCESS! Camera is working!{RESET}")
        print(f"\nYou can now run:")
        print(f"  {BLUE}python3 src/main.py{RESET}")
        print(f"  {BLUE}python3 test_vision.py{RESET}")
    else:
        print(f"{YELLOW}⚠ Camera configuration found but needs manual steps{RESET}")
        print(f"\nNext steps:")
        print(f"1. If permissions were wrong, log out and log back in")
        print(f"2. Unplug and replug the USB camera")
        print(f"3. Run this script again: {BLUE}python3 fix_logitech_camera.py{RESET}")
        print(f"4. If still not working, try: {BLUE}sudo reboot{RESET}")

    print("=" * 70)

if __name__ == "__main__":
    main()
