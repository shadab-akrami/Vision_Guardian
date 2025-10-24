# VisionGuardian - Quick Start Guide

Get up and running in 15 minutes!

## Prerequisites

- Raspberry Pi 5 with 64-bit Raspberry Pi OS
- 32GB microSD card
- USB Webcam
- Earphones/Headphones
- Internet connection

## Installation (5 minutes)

1. **Clone or extract the project:**
   ```bash
   cd ~
   # If you have the files, or:
   # git clone [repository-url] blind-assistant
   cd blind-assistant
   ```

2. **Run the setup script:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Wait for installation** (20-30 minutes)
   - The script will install all dependencies
   - Download required models
   - Configure audio and camera

4. **Reboot:**
   ```bash
   sudo reboot
   ```

## Basic Configuration (2 minutes)

1. **Test the camera:**
   ```bash
   cd ~/blind-assistant
   source venv/bin/activate
   python3 src/camera_handler.py
   ```
   Press 'q' to quit if the camera works.

2. **Test audio:**
   ```bash
   python3 src/audio_output.py
   ```
   You should hear test announcements.

## Add Known Faces (5 minutes)

1. **Create a directory for yourself:**
   ```bash
   mkdir -p data/known_faces/YourName
   ```

2. **Add 2-3 photos of your face:**
   ```bash
   # Copy photos to the directory
   cp /path/to/your/photo1.jpg data/known_faces/YourName/
   cp /path/to/your/photo2.jpg data/known_faces/YourName/
   ```

3. **Train the system:**
   ```bash
   python3 scripts/train_faces.py
   ```

## First Run (3 minutes)

1. **Start VisionGuardian:**
   ```bash
   ./start.sh
   ```

2. **Wait for initialization:**
   - You'll hear "VisionGuardian initializing"
   - Then "VisionGuardian ready"

3. **Try voice commands:**
   - Say: **"Hey Guardian"**
   - Then: **"What do you see"**

## Essential Voice Commands

Wake word: **"Hey Guardian"**

Commands:
- **"Read text"** - Read visible text
- **"What do you see"** - Describe scene
- **"Who is here"** - Identify people
- **"What color"** - Detect color
- **"Any obstacles"** - Check for obstacles
- **"Help"** - List all commands

## Auto-Start on Boot

To start VisionGuardian automatically:

```bash
sudo systemctl enable visionguardian
sudo systemctl start visionguardian
```

Check if running:
```bash
sudo systemctl status visionguardian
```

## Adjust Settings

Edit `config/settings.yaml` to customize:

```yaml
# Make voice faster/slower
audio:
  voice_speed: 180  # Increase for faster speech

# Improve performance
camera:
  resolution_width: 480  # Lower for better FPS

# Adjust sensitivity
object_detection:
  confidence_threshold: 0.6  # Higher = fewer false positives
```

## Troubleshooting

### No camera?
```bash
vcgencmd get_camera
sudo raspi-config  # Enable camera
```

### No audio?
```bash
speaker-test -t wav
sudo raspi-config  # Check audio output
```

### Low performance?
```bash
python3 scripts/benchmark.py
# Check if CPU is throttling:
vcgencmd measure_temp
```

## Next Steps

1. **Add more faces:**
   - Create directories for family/friends
   - Add their photos
   - Run training script

2. **Calibrate camera:**
   ```bash
   python3 scripts/calibrate.py
   ```

3. **Test performance:**
   ```bash
   python3 scripts/benchmark.py
   ```

4. **Customize settings:**
   - Edit `config/settings.yaml`
   - Adjust voice speed, thresholds, etc.

## Getting Help

- **Check logs:** `tail -f logs/visionguardian.log`
- **Read README:** Full documentation in `README.md`
- **Test modules:** Run individual module tests

## Tips for Best Results

1. **Good lighting** - System works best in well-lit areas
2. **Clear audio** - Use quality earphones for best experience
3. **Regular updates** - Keep system and models updated
4. **Battery backup** - Use portable power for mobile use
5. **Test regularly** - Run benchmarks to ensure good performance

---

**You're ready to go! VisionGuardian is now helping you navigate the world.**

For detailed documentation, see `README.md`
