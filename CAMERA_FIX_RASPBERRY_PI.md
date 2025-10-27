# Camera Fix for Raspberry Pi - Multi-Backend Support

## Problem
Getting uniform gray pixels (r:130 g:130 b:130) or "camera producing uniform pixels" error on Raspberry Pi.

## Solution
The camera handler has been updated with **multi-backend support** to automatically detect and use the best camera method for your Raspberry Pi.

---

## What Changed

### ✅ New Features

1. **Multiple Backend Support**
   - `picamera2` (best for Pi Camera Modules v1/v2/v3/HQ)
   - `OpenCV with V4L2` (USB cameras, some Pi cameras)
   - `OpenCV generic` (fallback for other cameras)

2. **Automatic Detection**
   - Tries all backends automatically
   - Tests multiple device IDs (0, 1, 2, 3)
   - Validates frames before accepting backend

3. **Better Diagnostics**
   - Shows which backend is working
   - Detects uniform/black frames
   - Provides troubleshooting tips

---

## Quick Start

### Step 1: Test Your Camera

Run the diagnostic tool to see which backend works:

```bash
python3 test_camera_backends.py
```

This will test **all** available camera methods and tell you which one works.

### Step 2: Install picamera2 (Recommended for Pi Camera)

If you're using a **Raspberry Pi Camera Module**, install picamera2:

```bash
# Install picamera2
pip install picamera2

# Or use system package (Raspberry Pi OS Bullseye or newer)
sudo apt install python3-picamera2
```

### Step 3: Enable Camera (Raspberry Pi Camera Module only)

```bash
# Enable camera interface
sudo raspi-config
# Navigate to: Interface Options → Camera → Enable

# Reboot
sudo reboot
```

### Step 4: Test the Application

```bash
# Run the application
python3 src/main.py

# Or run the visual test
python3 test_vision.py
```

---

## Troubleshooting

### Issue: "picamera2 library not installed"

**For Raspberry Pi Camera Module:**

```bash
# Method 1: pip install (recommended)
pip install picamera2

# Method 2: System package (Raspberry Pi OS)
sudo apt update
sudo apt install python3-picamera2

# Verify installation
python3 -c "from picamera2 import Picamera2; print('picamera2 installed!')"
```

### Issue: "All backends failed"

**Check camera connection:**

```bash
# For Raspberry Pi Camera Module
libcamera-hello

# For USB cameras
ls -l /dev/video*
```

**Check permissions:**

```bash
# Add user to video group
sudo usermod -a -G video $USER

# Log out and log back in (or reboot)
sudo reboot
```

**Enable camera (Pi Camera Module):**

```bash
sudo raspi-config
# Interface Options → Camera → Enable
```

### Issue: "Camera producing uniform frames"

This means the camera is opening but not capturing actual video. Try:

1. **Different device ID:**
   ```yaml
   # Edit config/settings.yaml
   camera:
     device_id: 1  # Try 0, 1, 2, or 3
   ```

2. **Use picamera2:**
   ```bash
   pip install picamera2
   ```

3. **Restart camera:**
   ```bash
   sudo modprobe -r bcm2835-v4l2
   sudo modprobe bcm2835-v4l2
   ```

### Issue: USB Camera Not Detected

```bash
# List video devices
ls -l /dev/video*

# Check if camera is detected
v4l2-ctl --list-devices

# Install v4l-utils if not available
sudo apt install v4l-utils
```

---

## Testing Individual Backends

### Test picamera2

```python
python3 -c "
from picamera2 import Picamera2
import time

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={'size': (640, 480)})
picam2.configure(config)
picam2.start()
time.sleep(1)
frame = picam2.capture_array()
print(f'Frame captured: {frame.shape}, pixel range: {frame.min()}-{frame.max()}')
picam2.stop()
"
```

### Test OpenCV

```python
python3 -c "
import cv2
camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
ret, frame = camera.read()
if ret:
    print(f'Frame captured: {frame.shape}, pixel range: {frame.min()}-{frame.max()}')
else:
    print('Failed to capture frame')
camera.release()
"
```

---

## Configuration

The camera handler will automatically use the best backend, but you can force specific settings:

### Use Specific Device

```yaml
# config/settings.yaml
camera:
  device_id: 0  # Try 0, 1, 2, or 3
```

### Disable Processing (Raw Mode)

```yaml
# config/settings.yaml
camera:
  raw_mode: true  # No rotation, flipping, or color correction
```

---

## Supported Hardware

### ✅ Raspberry Pi Camera Modules

- **Pi Camera Module v1** (5MP)
- **Pi Camera Module v2** (8MP)
- **Pi Camera Module v3** (12MP)
- **Pi HQ Camera** (12.3MP)

**Best Backend:** `picamera2`

### ✅ USB Webcams

- Most USB webcams
- Logitech C270, C920, etc.
- Generic UVC cameras

**Best Backend:** `OpenCV V4L2` or `OpenCV Generic`

---

## How It Works

The camera handler tries backends in this order:

1. **picamera2** (if installed)
   - Best for Raspberry Pi camera modules
   - Native support, best performance

2. **OpenCV V4L2** (device 0, 1, 2, 3)
   - Good for USB cameras
   - Direct V4L2 access

3. **OpenCV Generic** (device 0, 1, 2, 3)
   - Fallback for other cameras
   - Works with most cameras

For each backend:
- Captures test frames
- Validates pixel data (no black/uniform frames)
- Selects first working backend

---

## Performance Tips

### Raspberry Pi Camera Module

```yaml
# config/settings.yaml
camera:
  resolution_width: 640   # Lower = faster
  resolution_height: 480
  fps: 15                 # Lower = less CPU usage
  raw_mode: true          # Disable processing for speed
```

### USB Camera

```yaml
# config/settings.yaml
camera:
  device_id: 0
  resolution_width: 640
  resolution_height: 480
  fps: 15
```

---

## Logs

Check the logs for detailed camera initialization info:

```bash
# View camera initialization
cat logs/vision_guardian.log | grep -A 20 "CAMERA INITIALIZATION"

# Check for errors
cat logs/vision_guardian.log | grep -i "error\|fail\|uniform"
```

---

## Summary

| Problem | Solution |
|---------|----------|
| Uniform gray pixels | Install picamera2 or try different device_id |
| Black frames | Check camera connection and enable in raspi-config |
| Camera not detected | Check /dev/video*, permissions, and enable camera |
| Wrong device | Use test_camera_backends.py to find correct device_id |

---

## Commands Cheatsheet

```bash
# Test all backends
python3 test_camera_backends.py

# Install picamera2 (Pi Camera Module)
pip install picamera2

# Enable camera (Pi Camera Module)
sudo raspi-config  # → Interface → Camera → Enable

# Check video devices
ls -l /dev/video*

# Fix permissions
sudo usermod -a -G video $USER
sudo reboot

# Test Pi Camera
libcamera-hello

# View logs
cat logs/vision_guardian.log | tail -50
```

---

## Still Not Working?

If camera still doesn't work after all troubleshooting:

1. **Verify camera works outside the application:**
   ```bash
   # Pi Camera
   libcamera-hello

   # USB Camera
   cheese  # or any camera viewer
   ```

2. **Check Raspberry Pi OS version:**
   ```bash
   cat /etc/os-release
   ```
   - picamera2 requires Raspberry Pi OS Bullseye or newer

3. **Check camera hardware:**
   - Reconnect camera ribbon cable (Pi Camera)
   - Try different USB port (USB camera)
   - Test camera on different computer

4. **Create issue with logs:**
   ```bash
   python3 test_camera_backends.py > camera_test.txt 2>&1
   cat logs/vision_guardian.log > app_log.txt
   ```
   Share these files when asking for help.

---

**Your camera should now work on Raspberry Pi! The multi-backend system will automatically detect and use the best method for your hardware.**
