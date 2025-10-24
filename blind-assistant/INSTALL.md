# VisionGuardian Installation Guide

## For Raspberry Pi 5 (Recommended)

### Automated Installation (Easiest)

```bash
cd blind-assistant
chmod +x setup.sh
./setup.sh
```

This script will:
- Install all system dependencies
- Set up Python virtual environment
- Install Python packages
- Download models
- Configure audio and camera
- Create systemd service

**Installation time**: 20-30 minutes

### Manual Installation

If the automated script fails or you prefer manual installation:

#### 1. Update System

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

#### 2. Install System Dependencies

```bash
sudo apt-get install -y \
    python3-dev python3-pip python3-venv \
    cmake build-essential pkg-config \
    libjpeg-dev libtiff5-dev libpng-dev \
    libavcodec-dev libavformat-dev libswscale-dev \
    libv4l-dev libxvidcore-dev libx264-dev \
    libatlas-base-dev gfortran \
    tesseract-ocr libtesseract-dev tesseract-ocr-eng \
    portaudio19-dev python3-pyaudio alsa-utils \
    espeak espeak-ng mpg123 v4l-utils
```

#### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```

#### 4. Install Python Packages

**Option A: All packages (may take 30-60 minutes)**

```bash
pip install -r requirements.txt
```

**Option B: Install step-by-step (recommended if errors occur)**

```bash
# Core packages
pip install numpy Pillow opencv-python imutils

# Configuration
pip install PyYAML python-dotenv

# Utilities
pip install requests psutil coloredlogs python-json-logger distro webcolors filterpy

# OCR
pip install pytesseract

# Audio (some via apt)
sudo apt-get install python3-pyaudio
pip install pyttsx3 gTTS SpeechRecognition

# Facial recognition (takes longest, may need to build from source)
pip install face-recognition

# Computer vision extras
pip install opencv-contrib-python scikit-learn scipy
```

**If face-recognition fails to install:**

```bash
# Install dlib dependencies
sudo apt-get install cmake libopenblas-dev liblapack-dev

# Build dlib from source
pip install dlib --no-cache-dir

# Then install face-recognition
pip install face-recognition
```

**If TFLite fails to install:**

```bash
# For ARM64, use the Coral repository
pip3 install --index-url https://google-coral.github.io/py-repo/ tflite_runtime
```

#### 5. Download Models

```bash
chmod +x scripts/download_models.sh
./scripts/download_models.sh
```

Or manually:

```bash
mkdir -p models
cd models
wget https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
unzip coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
mv detect.tflite ssd_mobilenet_v2_coco_quant.tflite
mv labelmap.txt coco_labels.txt
rm *.zip
cd ..
```

#### 6. Configure Hardware

**Camera:**

```bash
sudo raspi-config
# Navigate to: Interface Options -> Camera -> Enable
sudo usermod -a -G video $USER
```

**Audio:**

```bash
# Set audio to headphone jack (not HDMI)
sudo amixer cset numid=3 1

# Test audio
espeak "Audio test"
```

#### 7. Test Installation

```bash
# Test camera
python3 src/camera_handler.py

# Test audio
python3 src/audio_output.py
```

#### 8. First Run

```bash
python3 src/main.py
```

## Troubleshooting

### NumPy Version Conflicts

If you see NumPy version errors:

```bash
pip install "numpy>=1.24.0,<2.0.0" --force-reinstall
```

### Face Recognition Build Fails

```bash
# Increase swap space
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Try again
pip install face-recognition --no-cache-dir
```

### TFLite Runtime Not Found

```bash
# Use Coral's repository for ARM64
pip3 install --index-url https://google-coral.github.io/py-repo/ tflite_runtime
```

### Camera Not Detected

```bash
# Check camera
vcgencmd get_camera

# List video devices
v4l2-ctl --list-devices

# If using USB camera, check permissions
sudo usermod -a -G video $USER
# Log out and back in
```

### Audio Not Working

```bash
# List audio devices
aplay -l

# Test speaker
speaker-test -t wav -c 2

# Check volume
alsamixer

# Set default output
sudo raspi-config
# Navigate to: System Options -> Audio
```

### Out of Memory During Install

```bash
# Reduce parallel builds
export MAKEFLAGS="-j1"

# Install packages one at a time
pip install --no-cache-dir <package-name>
```

### Low Storage Space

```bash
# Check space
df -h

# Clean package cache
sudo apt-get clean
sudo apt-get autoclean

# Remove unused packages
sudo apt-get autoremove
```

## For Development/Testing (Non-Raspberry Pi)

If you want to test the code on a regular PC:

```bash
# Install minimal requirements
pip install -r requirements-dev.txt

# Some features won't work without:
# - face-recognition (requires dlib)
# - TFLite models (ARM-specific)
# - GPIO libraries (Raspberry Pi only)
```

## Verification

After installation, verify everything works:

```bash
# Run benchmark
python3 scripts/benchmark.py

# Check system info
python3 -c "from src.utils import get_system_info; import json; print(json.dumps(get_system_info(), indent=2))"

# Test storage
python3 -c "from src.storage_manager import StorageManager; from src.utils import Config; sm = StorageManager(Config()); print(sm.get_storage_report())"
```

## Post-Installation

1. **Add known faces**: Create directories in `data/known_faces/` and run `python3 scripts/train_faces.py`
2. **Calibrate camera**: Run `python3 scripts/calibrate.py`
3. **Adjust settings**: Edit `config/settings.yaml`
4. **Enable auto-start**: `sudo systemctl enable visionguardian`

## Getting Help

If installation fails:

1. Check the error message carefully
2. Review the troubleshooting section above
3. Check available disk space (`df -h`)
4. Check available memory (`free -h`)
5. Review logs in `logs/` directory
6. Try installing problematic packages individually

## Minimum Requirements

- Raspberry Pi 5 (4GB RAM minimum, 8GB recommended)
- 32GB microSD card (Class 10 or better)
- 10GB+ free space for installation
- Internet connection during setup
- USB webcam
- Audio output device (earphones/speakers)

## Optional Enhancements

```bash
# Better OCR (requires 500MB+ storage)
pip install easyocr

# Wake word detection
pip install pvporcupine

# GPIO support
pip install RPi.GPIO gpiozero
```

---

For quick start, see `QUICKSTART.md`

For full documentation, see `README.md`
