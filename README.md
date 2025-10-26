# VisionGuardian

**Smart Wearable Assistant System for Visually Impaired Users**

Optimized for Raspberry Pi 5 (64-bit ARM64 Architecture)

---

## Overview

VisionGuardian is a comprehensive assistive technology system designed to help visually impaired users navigate their environment safely and independently. Using computer vision, voice commands, and audio feedback, it provides real-time information about surroundings, obstacles, people, text, and more.

### Key Features

- **Facial Recognition**: Recognizes and announces familiar people
- **Object Detection**: Identifies and announces objects in real-time
- **OCR (Text Recognition)**: Reads text from signs, documents, and labels
- **Scene Description**: Provides contextual environmental descriptions
- **Obstacle Detection**: Alerts about obstacles with distance estimation
- **Currency Detection**: Identifies bills and coins
- **Color Detection**: Announces colors of objects
- **Voice Commands**: Hands-free operation via voice activation
- **Priority-Based Audio**: Intelligent announcement system with priority levels

---

## Hardware Requirements

### Required Hardware

- **Raspberry Pi 5** (4GB or 8GB RAM recommended)
- **32GB microSD card** (Class 10 or better)
- **USB Webcam** (720p or higher)
- **Earphones/Headphones** (3.5mm or USB)
- **Power Supply** (Official Raspberry Pi 5 power supply)

### Optional Hardware

- USB Microphone (for better voice recognition)
- Portable power bank (for mobile use)
- Mounting hardware for wearable configuration

---

## Software Requirements

- **Raspberry Pi OS** (64-bit) Bookworm or later
- **Python 3.11+**
- **OpenCV 4.8+** (ARM64 optimized)
- **TensorFlow Lite Runtime**
- See `requirements.txt` for complete list

---

## Installation

### Quick Install

Run the automated setup script:

```bash
cd blind-assistant
chmod +x setup.sh
./setup.sh
```

The installation process takes approximately 20-30 minutes and includes:
- System updates
- Dependency installation
- Python environment setup
- Model downloads
- Audio/camera configuration
- Service creation

### Manual Installation

If you prefer manual installation, follow these steps:

#### 1. Update System

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

#### 2. Install System Dependencies

```bash
sudo apt-get install -y python3-dev python3-pip python3-venv \
    cmake build-essential pkg-config \
    libjpeg-dev libtiff5-dev libpng-dev \
    libavcodec-dev libavformat-dev libswscale-dev \
    libv4l-dev libxvidcore-dev libx264-dev \
    libatlas-base-dev gfortran \
    tesseract-ocr libtesseract-dev tesseract-ocr-eng \
    portaudio19-dev python3-pyaudio alsa-utils \
    espeak espeak-ng mpg123 \
    v4l-utils
```

#### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

#### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### 5. Download Models

```bash
mkdir -p models
cd models

# Download object detection model
wget https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
unzip coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
mv detect.tflite ssd_mobilenet_v2_coco_quant.tflite
mv labelmap.txt coco_labels.txt

cd ..
```

#### 6. Configure Audio

```bash
# Set audio output to headphone jack
sudo amixer cset numid=3 1

# Test audio
espeak "Audio test"
```

#### 7. Configure Camera

```bash
# Enable camera
sudo raspi-config nonint do_camera 0

# Add user to video group
sudo usermod -a -G video $USER
```

---

## Configuration

### Settings File

All settings are configured in `config/settings.yaml`. Key sections include:

```yaml
system:
  debug_mode: false
  log_level: "INFO"
  storage_warning_threshold_gb: 5

camera:
  resolution_width: 640
  resolution_height: 480
  fps: 15

audio:
  engine: "pyttsx3"
  voice_speed: 160
  volume: 0.9

facial_recognition:
  enabled: true
  tolerance: 0.6

object_detection:
  enabled: true
  confidence_threshold: 0.5

ocr:
  enabled: true
  engine: "tesseract"

obstacle_detection:
  enabled: true
  min_distance_cm: 150
  warning_distance_cm: 100
```

### Customize Settings

Edit `config/settings.yaml` to customize:
- Feature enable/disable
- Detection thresholds
- Voice speed and volume
- Camera resolution and FPS
- Priority levels
- Storage management

---

## Facial Recognition Setup

### Adding Known Faces

1. Create a directory for each person:

```bash
mkdir -p data/known_faces/John
mkdir -p data/known_faces/Jane
```

2. Add face photos (2-5 photos per person):

```bash
# Add clear, front-facing photos
data/known_faces/John/photo1.jpg
data/known_faces/John/photo2.jpg
data/known_faces/Jane/photo1.jpg
data/known_faces/Jane/photo2.jpg
```

3. Train the face recognition model:

```bash
python3 scripts/train_faces.py
```

### Photo Guidelines

- Use clear, well-lit photos
- Face should be front-facing
- Include different expressions
- Avoid sunglasses or masks
- 2-5 photos per person recommended

---

## Usage

### Starting the Application

#### Option 1: Manual Start

```bash
cd blind-assistant
source venv/bin/activate
python3 src/main.py
```

Or use the startup script:

```bash
./start.sh
```

#### Option 2: Auto-Start on Boot

Enable the systemd service:

```bash
sudo systemctl enable visionguardian
sudo systemctl start visionguardian
```

Check status:

```bash
sudo systemctl status visionguardian
```

View logs:

```bash
sudo journalctl -u visionguardian -f
```

### Voice Commands

Wake the system with: **"Hey Guardian"**

Then use commands:

- **"Read text"** - Read visible text using OCR
- **"What do you see"** - Describe the scene
- **"Who is here"** - Identify people
- **"What color"** - Detect colors
- **"Identify money"** - Detect currency
- **"Any obstacles"** - Check for obstacles
- **"Help"** - List available commands
- **"Repeat"** - Repeat last announcement
- **"Stop"** - Stop all announcements

### Automatic Features

When running, VisionGuardian automatically:

- Monitors for obstacles (continuous)
- Recognizes familiar faces (every 2 seconds)
- Detects objects (every 3 seconds)
- Manages storage and logs
- Provides priority-based announcements

---

## Calibration

### Camera Calibration

For accurate distance estimation:

```bash
python3 scripts/calibrate.py
```

Select option 1 (Camera calibration) and follow instructions:

1. Place an object at a known distance (e.g., 100cm)
2. Press 'c' to capture
3. Enter the actual distance
4. System calculates focal length
5. Update `config/settings.yaml` with the focal length

### Audio Calibration

To find the optimal voice speed:

```bash
python3 scripts/calibrate.py
```

Select option 2 (Audio calibration) and test different speeds.

---

## Performance Benchmarking

Test system performance:

```bash
python3 scripts/benchmark.py
```

This will benchmark:
- Camera capture FPS
- Object detection throughput
- Facial recognition speed
- OCR processing time
- Obstacle detection performance

### Expected Performance on Raspberry Pi 5

- **Camera**: 15+ FPS
- **Object Detection**: 10-15 FPS
- **Facial Recognition**: < 1 second per detection
- **OCR**: < 2 seconds per frame
- **Obstacle Detection**: 15+ FPS

---

## Storage Management

### Automatic Cleanup

VisionGuardian automatically manages storage:

- Rotates logs (keeps last 7 days)
- Cleans cache (keeps last 24 hours)
- Limits unknown face storage
- Monitors free space

### Manual Storage Check

```bash
python3 -c "from src.storage_manager import StorageManager; from src.utils import Config; sm = StorageManager(Config()); print(sm.get_storage_report())"
```

### Storage Optimization Tips

- Use quantized models (INT8)
- Enable automatic cleanup
- Periodically review logs
- Remove unnecessary face encodings
- Keep models directory clean

---

## Troubleshooting

### Camera Not Working

```bash
# Check camera detection
v4l2-ctl --list-devices

# Test camera
vcgencmd get_camera

# Enable camera
sudo raspi-config
```

### Audio Not Working

```bash
# Test speakers
speaker-test -t wav

# Check audio devices
aplay -l

# Set output device
sudo raspi-config
```

### Low Performance

1. Check CPU temperature:
   ```bash
   vcgencmd measure_temp
   ```

2. Reduce resolution in `config/settings.yaml`:
   ```yaml
   camera:
     resolution_width: 480
     resolution_height: 360
   ```

3. Disable non-essential features:
   ```yaml
   scene_description:
     enabled: false
   ```

### Import Errors

```bash
# Reinstall dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Facial Recognition Not Working

```bash
# Check if dlib is installed correctly
python3 -c "import dlib; print(dlib.__version__)"

# Reinstall face_recognition
pip install --no-cache-dir face_recognition
```

---

## Development

### Project Structure

```
blind-assistant/
├── src/
│   ├── main.py                    # Main application
│   ├── camera_handler.py          # Camera capture
│   ├── audio_output.py            # Audio/TTS
│   ├── facial_recognition.py      # Face recognition
│   ├── object_detection.py        # Object detection
│   ├── ocr_module.py              # Text recognition
│   ├── scene_description.py       # Scene analysis
│   ├── obstacle_detection.py      # Obstacle detection
│   ├── currency_detection.py      # Currency recognition
│   ├── color_detection.py         # Color detection
│   ├── voice_assistant.py         # Voice commands
│   ├── storage_manager.py         # Storage management
│   └── utils.py                   # Utilities
├── models/                        # ML models
├── data/
│   └── known_faces/              # Face training data
├── config/
│   └── settings.yaml             # Configuration
├── logs/                         # Application logs
├── cache/                        # Temporary cache
├── scripts/
│   ├── train_faces.py           # Face training
│   ├── calibrate.py             # Calibration tool
│   └── benchmark.py             # Performance testing
├── requirements.txt              # Python dependencies
├── setup.sh                      # Installation script
└── README.md                     # This file
```

### Adding Custom Features

1. Create a new module in `src/`
2. Follow the existing module pattern
3. Register in `main.py`
4. Update `config/settings.yaml`
5. Test thoroughly

### Testing

Run module tests:

```bash
# Test camera
python3 src/camera_handler.py

# Test audio
python3 src/audio_output.py

# Test face recognition
python3 src/facial_recognition.py

# Test object detection
python3 src/object_detection.py
```

---

## Performance Optimization

### For Better Battery Life

- Reduce camera FPS
- Increase detection intervals
- Disable non-critical features
- Use power-efficient wake word detection

### For Better Accuracy

- Increase confidence thresholds
- Use higher resolution
- Add more training photos for faces
- Fine-tune model parameters

### For Lower Latency

- Reduce image resolution
- Use quantized models
- Enable frame skipping
- Optimize detection intervals

---

## Limitations

- Currency detection uses basic heuristics (custom model recommended)
- Scene description is rule-based (ML model recommended)
- Distance estimation requires calibration
- Voice recognition requires internet connection (Google Speech API)
- Performance varies with ambient conditions

---

## Future Enhancements

- GPS navigation integration
- Emergency contact alerts
- Offline voice recognition
- Advanced depth sensing (with depth camera)
- Mobile app integration
- Cloud backup for face encodings
- Multi-language support
- Improved currency detection models

---

## Contributing

Contributions are welcome! Areas for improvement:

- Better currency detection models
- Enhanced scene understanding
- Offline voice recognition
- Performance optimizations
- Documentation improvements
- Bug fixes

---

## Safety Notice

VisionGuardian is an assistive tool and should not be the sole means of navigation. Users should:

- Use traditional mobility aids (cane, guide dog) when available
- Be cautious in unfamiliar environments
- Verify important information when possible
- Keep the system charged and maintained
- Have backup navigation methods

---

## License

This project is intended for educational and assistive technology purposes.

---

## Support

For issues, questions, or suggestions:

1. Check the troubleshooting section
2. Review logs in `logs/`
3. Run benchmarks to check performance
4. Test individual modules for issues

---

## Acknowledgments

Built using:
- OpenCV for computer vision
- TensorFlow Lite for object detection
- face_recognition for facial recognition
- Tesseract OCR for text recognition
- pyttsx3 for text-to-speech
- Python Speech Recognition

Optimized for Raspberry Pi 5 (64-bit ARM64 architecture)

---

## Version

**Version 1.0.0**

Tested on:
- Raspberry Pi 5 (4GB/8GB)
- Raspberry Pi OS (64-bit) Bookworm
- Python 3.11+

---

**VisionGuardian - Empowering Independence Through Technology**
