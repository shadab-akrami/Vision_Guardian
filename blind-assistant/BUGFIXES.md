# Bug Fixes

## Version 1.0.2 - Path Configuration Fix

### Bug 3: Model Path Doubling

#### Issue
```
WARNING: Labels file not found: /path/models/models/coco_labels.txt
ERROR: Model file not found: /path/models/models/ssd_mobilenet_v2_coco_quant.tflite
```

Models directory appearing twice in paths.

#### Cause
Config file had paths like `"models/ssd_mobilenet_v2_coco_quant.tflite"` but code already prepends `MODELS_DIR` (which is the models directory), resulting in `models/models/file.tflite`.

#### Fix
Removed `"models/"` prefix from all model paths in `config/settings.yaml`:
- `model_path: "ssd_mobilenet_v2_coco_quant.tflite"` (was `"models/..."`)
- `labels_path: "coco_labels.txt"` (was `"models/..."`)
- Fixed for all modules: object_detection, scene_description, obstacle_detection, currency_detection

#### Files Changed
- `config/settings.yaml` (lines 60-61, 81, 95, 101)

#### Status
✅ Fixed

---

## Version 1.0.1 - Critical Bug Fixes

### Bug 1: Initialization Order Issue

#### Issue
`AttributeError: 'VisionGuardian' object has no attribute 'storage_manager'`

#### Cause
The `_check_system()` method was called before `storage_manager` was initialized in the `__init__` method.

#### Fix
Moved `self.storage_manager = StorageManager(self.config)` initialization to before the `_check_system()` call.

#### Files Changed
- `src/main.py` (lines 47-53)

#### Status
✅ Fixed

---

### Bug 2: Voice Assistant Microphone Error Loop

#### Issue
```
ERROR:VisionGuardian.VoiceAssistant:Error listening: 'NoneType' object does not support the context manager protocol
```
Repeating continuously when no microphone is connected.

#### Cause
The voice assistant tried to use a microphone that failed to initialize:
1. `sr.Microphone()` failed (no mic connected)
2. Exception was caught but `self.microphone` was left in an undefined state
3. `_listen_for_command()` tried to use `with self.microphone` even though it was `None`
4. This caused continuous error loop

#### Fix
1. Added explicit check for `self.microphone is None` in `_listen_for_command()`
2. Added check in `start_listening()` to prevent starting if microphone unavailable
3. Improved error handling in `initialize()` to:
   - Explicitly set `self.microphone = None` on failure
   - Set `self.enabled = False` to prevent further attempts
   - Log clear message that voice commands won't be available
4. System now gracefully continues without voice commands if no microphone

#### Files Changed
- `src/voice_assistant.py` (lines 66-107, 109-111, 143-175)

#### Status
✅ Fixed

---

## Known Warnings (Not Errors)

### 1. pkg_resources deprecation warning
```
UserWarning: pkg_resources is deprecated as an API
```
**Source**: face_recognition_models library (third-party)
**Impact**: None - just a warning, functionality works fine
**Action**: No action needed, will be fixed when upstream library updates

### 2. easyocr not available
```
WARNING:root:easyocr not available
```
**Source**: OCR module trying to import easyocr
**Impact**: System falls back to Tesseract OCR (works fine)
**Action**: Optional - install easyocr if you want better OCR:
```bash
pip install easyocr
```
Note: easyocr requires ~500MB storage and takes time to download models.

### 3. PyAudio / No microphone found
```
ERROR: No microphone found: Could not find PyAudio; check installation
```
**Source**: Voice assistant trying to initialize microphone
**Impact**: Voice commands won't work, but all other features work fine
**Action**: Optional - to enable voice commands:
```bash
# Install PyAudio system package
sudo apt-get install python3-pyaudio

# Or install via pip (may require compilation)
pip install pyaudio
```
**Note**: PyAudio requires PortAudio development libraries. If you don't need voice commands, you can ignore this warning.

---

## How to Apply These Fixes

If you're on Raspberry Pi and seeing the error:

```bash
cd ~/Vision_Guardian/blind-assistant

# Update main.py with the fix (file already updated if you're using latest version)
python3 src/main.py
```

The fix is already in the GitHub/provided files. If you downloaded earlier, just copy the updated `src/main.py` file.

---

## Verification

After applying the fix, you should see:

```
============================================================
VisionGuardian - Smart Assistant for Visually Impaired
Optimized for Raspberry Pi 5
============================================================
```

Followed by system information and initialization messages, NOT an error.
