# Grey Screen Issue - Fix Guide

## 🔧 Changes Made

To fix the grey screen issue, I've made the following changes:

### 1. **Created Minimal Camera Test** (`test_camera_minimal.py`)
   - Tests ALL camera devices (0, 1, 2, 3)
   - NO processing - pure raw camera feed
   - Identifies which camera device actually works
   - Diagnostic information for each device

### 2. **Added RAW MODE to Camera Handler**
   - New config option: `camera.raw_mode: true`
   - Bypasses ALL processing (rotation, flipping, color correction)
   - Returns pure camera output - exactly as captured
   - **Currently ENABLED by default**

### 3. **Enhanced Frame Validation**
   - Detects black frames (all zeros)
   - Detects uniform grey frames (all same value)
   - Warns about dark frames
   - Logs diagnostics every 100 frames

---

## 🚀 Quick Fix Steps

### **Step 1: Test Camera with Minimal Script**

This is the MOST IMPORTANT step - it will tell us if the issue is hardware or software.

```bash
cd ~/Vision_Guardian
source venv/bin/activate
python3 test_camera_minimal.py
```

**What this does:**
- Tests all camera devices (0, 1, 2, 3)
- Opens each working camera with ZERO processing
- Shows you the raw camera feed

**Expected Results:**

✅ **If you see COLORS:**
- Camera hardware is WORKING
- Issue is in VisionGuardian processing
- Proceed to Step 2

❌ **If you see GREY:**
- Camera hardware/driver issue
- Try different USB port
- Check camera permissions
- Try: `v4l2-ctl --list-devices`

---

### **Step 2: Identify Working Camera Device**

The minimal test will show which device_id works. Example output:

```
Working cameras: [0, 1]
Recommended device_id: 1
```

If device 1 works but device 0 doesn't, update config:

```bash
nano config/settings.yaml
```

Change:
```yaml
camera:
  device_id: 1  # Change from 0 to 1
```

---

### **Step 3: Run VisionGuardian with RAW MODE**

Raw mode is already enabled in the config (`raw_mode: true`). This bypasses ALL processing.

```bash
python3 src/main.py
```

**Check the logs:**
```bash
tail -f logs/vision_guardian.log
```

Look for:
- `RAW MODE ENABLED - All processing bypassed`
- Frame validation messages
- Any warnings about black/grey frames

---

### **Step 4: Test with Visual Monitor**

```bash
python3 test_vision.py
```

This shows what the camera sees with object detection overlay.

---

## 🔍 Diagnostic Commands

### Check Camera Devices
```bash
ls -l /dev/video*
```

### List Available Cameras
```bash
v4l2-ctl --list-devices
```

### Check Camera Properties
```bash
v4l2-ctl -d /dev/video0 --all
```

### Test Camera Directly
```bash
ffplay /dev/video0
```

### Check Who's Using Camera
```bash
fuser /dev/video0
```

---

## 🛠️ Common Issues and Solutions

### Issue 1: Wrong Camera Device

**Symptom:** Grey screen, but camera works on Windows

**Solution:**
```yaml
# In config/settings.yaml
camera:
  device_id: 1  # Try 1 instead of 0
```

**Why:** Some systems have multiple video devices (internal webcam, dummy drivers, actual camera)

---

### Issue 2: Camera Permissions

**Symptom:** Cannot open camera, permission denied

**Solution:**
```bash
# Add user to video group
sudo usermod -a -G video $USER

# Check permissions
ls -l /dev/video0

# If needed, set permissions
sudo chmod 666 /dev/video0
```

---

### Issue 3: Camera Not Warming Up

**Symptom:** First few frames are grey, then works

**Solution:** Already fixed! Camera now warms up for 30 frames instead of 10.

---

### Issue 4: Processing Pipeline Issue

**Symptom:** Minimal test works, but VisionGuardian shows grey

**Solution:** Raw mode is now enabled by default. If still grey, check logs:

```bash
tail -f logs/vision_guardian.log
```

Look for frame validation warnings.

---

### Issue 5: Display Server Not Running

**Symptom:** "Cannot create window" error

**Solution:**
```bash
# If using SSH, enable X11 forwarding
export DISPLAY=:0

# Or test headless
# The scripts will still validate frame data
```

---

## 📊 Configuration Summary

**Current Settings** (optimized for debugging):

```yaml
camera:
  device_id: 0        # Try 1, 2 if grey persists
  brightness: 50      # Camera default
  contrast: 50        # Camera default
  saturation: 50      # Camera default
  raw_mode: true      # BYPASS ALL PROCESSING
  color_correction:
    enabled: false    # NO color correction
```

---

## 🎯 What Each Test Does

### `test_camera_minimal.py`
- **Purpose:** Test camera hardware
- **Processing:** ZERO (pure raw feed)
- **Use When:** First troubleshooting step

### `test_camera_simple.py`
- **Purpose:** Diagnostics and device detection
- **Processing:** Minimal
- **Use When:** Need detailed device info

### `test_vision.py`
- **Purpose:** Full system test with object detection
- **Processing:** All features enabled
- **Use When:** Testing complete pipeline

### `src/main.py`
- **Purpose:** Run VisionGuardian system
- **Processing:** Depends on config (raw_mode = bypass all)
- **Use When:** Normal operation

---

## 🔬 Advanced Debugging

### Check Frame Data in Python

```python
import cv2
cap = cv2.VideoCapture(0)  # Try 0, 1, 2

# Warm up
for _ in range(30):
    cap.read()

ret, frame = cap.read()
print(f"Success: {ret}")
print(f"Shape: {frame.shape if frame is not None else 'None'}")
print(f"Range: {frame.min()}-{frame.max() if frame is not None else 'None'}")

cap.release()
```

If `frame.max()` is 0, camera is producing black frames.
If `frame.max()` > 0, camera is working!

---

## ✅ Success Criteria

**Camera is working when:**
1. ✅ `test_camera_minimal.py` shows colors
2. ✅ Frame pixel range is 0-255 (not all 0)
3. ✅ Log shows: `RAW MODE ENABLED`
4. ✅ No "BLACK frames" warnings in log
5. ✅ Object detection recognizes objects

---

## 📝 Next Steps

1. **Run `test_camera_minimal.py`** - This is CRITICAL
2. **Identify working device_id** - Update config if needed
3. **Run VisionGuardian** - With raw mode enabled
4. **Check logs** - For frame validation messages
5. **Disable raw mode** - Once confirmed working:
   ```yaml
   camera:
     raw_mode: false  # Enable processing after debug
   ```

---

## 🆘 Still Not Working?

If grey screen persists after all steps:

### Provide Debug Info

```bash
# System info
uname -a

# Camera devices
ls -l /dev/video*
v4l2-ctl --list-devices

# Test each device
for i in 0 1 2 3; do
  echo "Testing device $i:"
  v4l2-ctl -d /dev/video$i --all
done

# Run minimal test
python3 test_camera_minimal.py

# Check logs
cat logs/vision_guardian.log | grep -i "camera\|frame\|error"
```

### Hardware Checks

1. **Try different USB port**
2. **Check camera LED** - Is it on?
3. **Test on Windows** - Does it still work?
4. **Try another camera** - Different hardware
5. **Check power** - USB hub might not provide enough power

---

## 💡 Technical Details

### Why Raw Mode?

Processing steps that might cause issues:
- ❌ Rotation (cv2.rotate)
- ❌ Flipping (cv2.flip)
- ❌ Color correction (HSV conversion)
- ❌ Gamma correction (LUT tables)

Raw mode bypasses ALL of these, ensuring you get exactly what the camera captures.

### Frame Validation

New validation checks every 100 frames:
- Black frames (max = 0)
- Uniform frames (min = max)
- Dark frames (max < 10)

This helps identify camera issues immediately.

---

## 🎉 Once Working

After confirming camera works:

1. **Keep raw_mode: true** if no rotation/flipping needed
2. **Disable raw_mode** if you need rotation or flipping:
   ```yaml
   camera:
     raw_mode: false
     rotation: 90  # If needed
   ```
3. **Never enable color_correction** - Camera defaults are perfect!

---

## 📚 Summary

**Issue:** Grey screen in VisionGuardian
**Root Cause:** Likely wrong device_id OR processing issue
**Solution:**
1. Use minimal test to find working device_id
2. Enable raw_mode to bypass all processing
3. Update config with correct device_id

**Files Modified:**
- `src/camera_handler.py` - Added raw mode + frame validation
- `config/settings.yaml` - Enabled raw mode by default
- `test_camera_minimal.py` - NEW - Minimal camera test

**Run This First:**
```bash
python3 test_camera_minimal.py
```

**Good luck! 🚀**
