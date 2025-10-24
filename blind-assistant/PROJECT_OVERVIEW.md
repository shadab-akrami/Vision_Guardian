# VisionGuardian - Project Overview

## Project Summary

VisionGuardian is a production-ready smart wearable assistant system designed specifically for visually impaired users, optimized for Raspberry Pi 5 with 64-bit ARM architecture. The system provides real-time environmental awareness through computer vision, voice interaction, and intelligent audio feedback.

## Technical Architecture

### Hardware Platform
- **Target Device**: Raspberry Pi 5 (64-bit ARM64 architecture)
- **Storage**: 32GB SD card with intelligent storage management
- **Input**: USB Webcam, Voice commands via microphone
- **Output**: Audio feedback through earphones

### Software Stack
- **Language**: Python 3.11+
- **Computer Vision**: OpenCV (ARM64 optimized)
- **ML Framework**: TensorFlow Lite Runtime
- **OCR**: Tesseract / EasyOCR
- **TTS**: pyttsx3 / gTTS
- **Voice Recognition**: SpeechRecognition library

## Core Features Implemented

### 1. Facial Recognition (`facial_recognition.py`)
- Real-time face detection and recognition
- HOG and CNN models support
- Training system for known faces
- Unknown face logging
- Configurable recognition intervals

### 2. Object Detection (`object_detection.py`)
- TFLite-based object detection (SSD MobileNet)
- COCO dataset (80 object classes)
- Real-time detection with NMS
- Configurable confidence thresholds
- Top-N object announcement

### 3. OCR Module (`ocr_module.py`)
- Text reading from images
- Tesseract and EasyOCR support
- Image preprocessing pipeline
- Orientation detection
- Sentence/word/full announcement modes

### 4. Scene Description (`scene_description.py`)
- Lighting analysis
- Location type inference
- Scene composition analysis
- Comprehensive scene summaries
- Detail level configuration

### 5. Obstacle Detection (`obstacle_detection.py`)
- Real-time obstacle detection
- Distance estimation (calibrated)
- Multi-zone detection (left/center/right)
- Severity-based alerts
- Configurable warning distances

### 6. Currency Detection (`currency_detection.py`)
- Bill recognition system
- Multi-currency support framework
- Confidence-based detection
- Simple/detailed announcement modes

### 7. Color Detection (`color_detection.py`)
- Dominant color extraction
- K-means clustering
- Named color recognition
- Shade detection
- Center-point color detection

### 8. Voice Assistant (`voice_assistant.py`)
- Wake word activation
- Command recognition
- Callback system for actions
- Customizable commands
- Timeout management

### 9. Audio Output (`audio_output.py`)
- Priority-based announcement queue
- Emergency interruption support
- Multiple TTS engines
- Queue management
- Audio cue system

### 10. Camera Handler (`camera_handler.py`)
- Threaded frame capture
- Configurable resolution/FPS
- Frame preprocessing
- Performance monitoring
- V4L2 backend support

### 11. Storage Manager (`storage_manager.py`)
- Automatic cleanup system
- Log rotation
- Cache management
- Storage health monitoring
- Emergency cleanup procedures

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      VisionGuardian                          │
│                      Main Application                        │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────┼────────────┐
        │           │            │
        ▼           ▼            ▼
   ┌────────┐  ┌────────┐  ┌──────────┐
   │ Camera │  │ Audio  │  │  Voice   │
   │Handler │  │Output  │  │Assistant │
   └───┬────┘  └───┬────┘  └─────┬────┘
       │           │             │
       │           │             │
       ▼           ▼             ▼
┌──────────────────────────────────────┐
│        Processing Modules             │
├──────────────────────────────────────┤
│  • Facial Recognition                │
│  • Object Detection                  │
│  • OCR                               │
│  • Scene Description                 │
│  • Obstacle Detection                │
│  • Currency Detection                │
│  • Color Detection                   │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│       Support Systems                 │
├──────────────────────────────────────┤
│  • Storage Manager                   │
│  • Configuration System              │
│  • Performance Monitor               │
│  • Logging System                    │
└──────────────────────────────────────┘
```

## Threading Model

### Main Thread
- Application coordination
- Frame capture monitoring
- Command processing

### Background Threads
1. **Camera Capture Thread**: Continuous frame acquisition
2. **Obstacle Detection Thread**: High-priority safety monitoring (0.5s interval)
3. **Facial Recognition Thread**: Person identification (2s interval)
4. **Object Detection Thread**: Environment understanding (3s interval)
5. **Audio Speaker Thread**: Priority-based announcement delivery
6. **Voice Listening Thread**: Wake word and command detection
7. **Storage Monitor Thread**: Periodic health checks (5min interval)

## Priority System

Announcements are processed based on priority:

1. **EMERGENCY** (P1): Fire, medical emergencies
2. **CRITICAL** (P2): Obstacles in path
3. **HIGH** (P3): Recognized people, currency
4. **MEDIUM** (P4): Objects, colors, text
5. **LOW** (P5): Scene descriptions

Higher priority announcements can interrupt lower priority ones.

## Storage Optimization

### Space Management (32GB SD Card)
- **System**: ~8GB
- **Dependencies**: ~3GB
- **Models**: ~50MB (quantized INT8)
- **Application**: ~100MB
- **Logs**: Max 100MB (auto-rotated)
- **Cache**: Max 500MB (24h lifetime)
- **User Data**: ~1GB (face encodings)
- **Available**: ~19GB free space

### Optimization Techniques
- INT8 quantized models
- Automatic log rotation
- Cache expiration (24h)
- Selective face storage
- Model compression
- Emergency cleanup at 2GB threshold

## Performance Characteristics

### Expected Performance on Raspberry Pi 5

| Module | Metric | Target | Typical |
|--------|--------|--------|---------|
| Camera Capture | FPS | 15 | 15-20 |
| Object Detection | FPS | 10 | 10-15 |
| Facial Recognition | Time | <1s | 500-800ms |
| OCR Processing | Time | <2s | 1-2s |
| Obstacle Detection | FPS | 15 | 15-20 |
| Audio Latency | Time | <500ms | 200-400ms |

### Resource Usage
- **CPU**: 40-60% average (multi-threaded)
- **Memory**: 1.5-2GB
- **Storage I/O**: Minimal (optimized)
- **Network**: Only for voice recognition

## Configuration System

### Settings Hierarchy
- System-wide: `config/settings.yaml`
- Module-specific: Nested configurations
- Runtime: Command-line overrides
- Per-user: Face training data

### Key Configurable Parameters
- Detection thresholds
- Processing intervals
- Audio preferences
- Camera settings
- Feature enable/disable
- Priority levels
- Storage limits

## Installation & Deployment

### Automated Setup
- `setup.sh`: Complete installation script
- Dependency management
- Model downloads
- System configuration
- Service installation

### Manual Configuration
- Camera permissions
- Audio routing
- GPIO access (optional)
- Systemd service

### Deployment Modes
1. **Development**: Manual start with debug output
2. **Production**: Systemd service with auto-restart
3. **Testing**: Individual module testing

## Tools & Utilities

### Training Tools
- `train_faces.py`: Facial recognition training
- Face enrollment system
- Encoding management

### Calibration Tools
- `calibrate.py`: Camera distance calibration
- Audio speed optimization
- Threshold tuning

### Performance Tools
- `benchmark.py`: Comprehensive performance testing
- Module-specific benchmarks
- System health checks

### Model Management
- `download_models.sh`: Automated model downloads
- Version management
- Format conversion utilities

## Testing Strategy

### Unit Tests (`tests/`)
- Utils module testing
- Configuration validation
- Performance monitor tests
- Path verification

### Integration Tests
- Module interaction testing
- End-to-end workflows
- Error handling validation

### Performance Tests
- Benchmark suite
- Stress testing
- Memory leak detection

## Documentation

### User Documentation
- `README.md`: Comprehensive guide
- `QUICKSTART.md`: 15-minute setup
- `LICENSE`: MIT + Safety disclaimer

### Technical Documentation
- Inline code comments
- Module docstrings
- Configuration examples
- API documentation

### Operational Documentation
- Installation guides
- Troubleshooting tips
- Optimization guides
- Safety guidelines

## Security & Safety

### Safety Measures
- Not a replacement for traditional aids
- User warnings and disclaimers
- Fallback mechanisms
- Conservative distance estimates

### Security Features
- No data transmission (except voice API)
- Local processing only
- No remote access
- User data privacy

## Future Enhancements

### Planned Features
- GPS navigation integration
- Depth camera support
- Offline voice recognition
- Mobile app integration
- Advanced currency models
- Multi-language support

### Optimization Opportunities
- Custom trained models
- GPU acceleration (if available)
- Better depth estimation
- Enhanced scene understanding
- Improved battery optimization

## Project Statistics

### Code Metrics
- **Lines of Code**: ~5,000+ Python
- **Modules**: 14 core modules
- **Configuration**: 100+ parameters
- **Voice Commands**: 10+ built-in
- **Supported Objects**: 80 (COCO dataset)

### Development Effort
- **Architecture**: Modular, extensible
- **Testing**: Unit tests included
- **Documentation**: Comprehensive
- **Deployment**: Automated
- **Optimization**: Production-ready

## License & Attribution

- **License**: MIT License
- **Target Users**: Visually impaired community
- **Purpose**: Assistive technology
- **Status**: Production-ready

## Contact & Support

For issues and contributions:
- Review documentation
- Check troubleshooting guide
- Run diagnostic tools
- Submit detailed reports

---

**VisionGuardian - Empowering Independence Through Technology**

*Version 1.0.0 - Optimized for Raspberry Pi 5 (64-bit ARM64)*
