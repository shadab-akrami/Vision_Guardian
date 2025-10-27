# Logitech USB Webcam Setup for Raspberry Pi

## Your Setup
- **Camera**: Logitech 720p USB Webcam (C270/C920 or similar)
- **Platform**: Raspberry Pi
- **Issue**: Uniform gray pixels (R:130 G:130 B:130)

---

## 🚀 Quick Fix (1 Command)

```bash
python3 fix_logitech_camera.py
```

This script will:
- ✅ Auto-detect your camera device (/dev/video0, /dev/video1, etc.)
- ✅ Test different backends (V4L2, generic)
- ✅ Test different pixel formats (MJPEG, YUYV)
- ✅ Apply optimal V4L2 settings
- ✅ Update your config automatically
- ✅ Verify the camera works

**That's it!** After running this, your camera should work.

---

## 📋 Step-by-Step Instructions

### Step 1: Run the Fix Script

```bash
cd /path/to/blind-assistant
python3 fix_logitech_camera.py
```

**Expected output:**
```
============================================================
Logitech USB Webcam Fix for Raspberry Pi
============================================================

[1/6] Checking video devices...
✓ Video devices found:
/dev/video0
/dev/video2

[2/6] Testing camera configurations...
  Testing /dev/video0...
    V4L2/MJPEG: ✓ WORKING! (pixels: 0-255)

✓ Found working configuration!
  Device: /dev/video0
  Backend: V4L2
  Format: MJPEG

[3/6] Applying V4L2 settings...
✓ V4L2 settings applied

[4/6] Checking permissions...
✓ User is in 'video' group

[5/6] Updating application config...
✓ Config updated: device_id set to 0

[6/6] Testing with application...
✓ Camera working in application! (pixels: 0-255)

✓ SUCCESS! Camera is working!
```

### Step 2: Test the Application

```bash
# Visual test
python3 test_vision.py

# Or run the full application
python3 src/main.py
```

---

## ❌ If Fix Script Says "Fix Permissions First"

```bash
# Add your user to video group
sudo usermod -a -G video $USER

# Log out and log back in (or reboot)
sudo reboot

# Run fix script again
python3 fix_logitech_camera.py
```

---

## 🔧 Manual Troubleshooting

### Check Camera Connection

```bash
# List video devices
ls -l /dev/video*

# Should show something like:
# /dev/video0
# /dev/video1
```

### Check Camera Details

```bash
# Install v4l-utils
sudo apt install -y v4l-utils

# List all cameras
v4l2-ctl --list-devices

# Check camera capabilities
v4l2-ctl -d /dev/video0 --all
```

### Test Camera Outside Python

```bash
# Install cheese (simple webcam viewer)
sudo apt install cheese

# Run cheese
cheese

# If cheese works, Python should work too
```

---

## 🐛 Common Issues

### Issue 1: "No video devices found"

**Camera not detected by system**

```bash
# Check if camera is connected
lsusb | grep -i logitech

# Should show something like:
# Bus 001 Device 004: ID 046d:0825 Logitech, Inc. Webcam C270

# Check dmesg for errors
dmesg | grep -i usb | tail -20

# Try different USB port
# Try powered USB hub (Pi may not provide enough power)
```

### Issue 2: "Permission denied"

**User not in video group**

```bash
# Check groups
groups

# If 'video' is missing, add it
sudo usermod -a -G video $USER

# MUST log out and log back in
sudo reboot
```

### Issue 3: "Camera works in cheese but not in Python"

**V4L2 driver issue**

```bash
# Reset V4L2 settings
python3 fix_logitech_camera.py

# Or manually
v4l2-ctl -d /dev/video0 --set-ctrl=brightness=128
v4l2-ctl -d /dev/video0 --set-ctrl=contrast=128
v4l2-ctl -d /dev/video0 --set-ctrl=saturation=128
```

### Issue 4: "Wrong device_id"

Some USB cameras show up as `/dev/video1` or `/dev/video2` instead of `/dev/video0`.

**The fix script auto-detects this**, but if you want to manually check:

```bash
# Test each device
python3 -c "
import cv2
for i in range(4):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f'Device {i}: Working ({frame.shape})')
        cap.release()
"
```

Then update config:

```yaml
# config/settings.yaml
camera:
  device_id: 1  # Use the working device number
```

### Issue 5: "Camera initializes but shows uniform gray"

**Format issue - camera needs specific pixel format**

The fix script tests MJPEG and YUYV formats automatically. If it still fails:

```bash
# Check supported formats
v4l2-ctl -d /dev/video0 --list-formats-ext

# Look for:
# [0]: 'MJPG' (Motion-JPEG)
# [1]: 'YUYV' (YUYV 4:2:2)
```

---

## 🔍 Advanced: Check Camera Backend in Application

Check which backend the application is using:

```bash
# Run application and check logs
python3 src/main.py

# In another terminal, check logs
tail -f logs/vision_guardian.log | grep -i camera
```

Look for:
```
✅ SUCCESS! Using backend: opencv_v4l2 with device 0
```

---

## ⚙️ Logitech Camera Specifications

### Logitech C270
- Resolution: 720p (1280x720) @ 30fps, 480p @ 30fps
- Format: MJPEG, YUYV
- Works with: OpenCV V4L2

### Logitech C920
- Resolution: 1080p (1920x1080) @ 30fps
- Format: MJPEG, H.264
- Works with: OpenCV V4L2

**Both are supported!** The fix script will auto-configure optimal settings.

---

## 📝 Config File Settings

Your `config/settings.yaml` has been optimized for USB webcams:

```yaml
camera:
  device_id: 0           # Auto-detected by fix script
  resolution_width: 640  # Good balance for Pi
  resolution_height: 480
  fps: 30                # Logitech supports 30fps
  raw_mode: false        # Processing enabled for USB cameras
```

---

## 🚦 What Each Script Does

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `fix_logitech_camera.py` | **USE THIS FIRST** - Auto-fixes everything | Always run first |
| `test_camera_backends.py` | Tests all camera methods | If fix script doesn't work |
| `test_vision.py` | Visual test with object detection | After camera is working |
| `src/main.py` | Full application | Production use |

---

## 📦 Required Packages

```bash
# Install v4l-utils (for camera control)
sudo apt install -y v4l-utils

# Python packages (already in requirements.txt)
pip install opencv-python numpy
```

---

## ✅ Success Checklist

- [ ] Run `python3 fix_logitech_camera.py`
- [ ] See "✓ SUCCESS! Camera is working!"
- [ ] Run `python3 test_vision.py`
- [ ] See live camera feed with colors
- [ ] Objects are detected

**If all checked, you're done! 🎉**

---

## 💡 Pro Tips

1. **USB Power**: Raspberry Pi may not provide enough power for USB cameras
   - Use powered USB hub if camera keeps disconnecting
   - Don't use cheap USB cables

2. **USB Ports**: Some USB ports work better than others
   - Try blue USB 3.0 ports first
   - Avoid USB hubs if possible

3. **Resolution**: Lower resolution = better performance
   - 640x480 is perfect for object detection
   - 1280x720 if you need higher quality

4. **Lighting**: USB cameras need good lighting
   - Poor lighting = dark/grainy frames
   - Position camera facing light source

---

## 🆘 Still Not Working?

If nothing works:

1. **Collect diagnostics:**
   ```bash
   python3 fix_logitech_camera.py > camera_fix.log 2>&1
   python3 test_camera_backends.py > camera_test.log 2>&1
   lsusb > usb_devices.log
   v4l2-ctl --list-devices > v4l2_devices.log 2>&1
   dmesg | grep -i usb > usb_errors.log
   ```

2. **Check if it's hardware issue:**
   - Test camera on Windows/Mac
   - Test different USB cable
   - Test different camera

3. **Try different camera backend:**
   - Some cameras work better with generic OpenCV
   - The fix script tests all backends automatically

---

## 📚 Additional Resources

- [Logitech C270 Datasheet](https://www.logitech.com/en-us/products/webcams/c270-hd-webcam.960-000694.html)
- [V4L2 Documentation](https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.html)
- [OpenCV VideoCapture Documentation](https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html)

---

**Your Logitech USB webcam should now work perfectly on Raspberry Pi! 🎥**
