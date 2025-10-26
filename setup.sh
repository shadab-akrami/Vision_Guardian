#!/bin/bash
################################################################################
# VisionGuardian Setup Script for Raspberry Pi 5 (64-bit Raspberry Pi OS)
# This script installs all dependencies and configures the system
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on 64-bit ARM
check_architecture() {
    log_info "Checking system architecture..."
    ARCH=$(uname -m)

    if [ "$ARCH" != "aarch64" ]; then
        log_error "This script requires 64-bit ARM architecture (aarch64)"
        log_error "Detected: $ARCH"
        exit 1
    fi

    log_info "Architecture check passed: $ARCH"
}

# Check if running on Raspberry Pi 5
check_raspberry_pi() {
    log_info "Checking Raspberry Pi model..."

    if [ -f /proc/device-tree/model ]; then
        MODEL=$(cat /proc/device-tree/model)
        log_info "Detected: $MODEL"

        if [[ ! $MODEL =~ "Raspberry Pi 5" ]]; then
            log_warn "This script is optimized for Raspberry Pi 5"
            log_warn "Detected: $MODEL"
            log_warn "Continue anyway? (y/n)"
            read -r response
            if [[ ! $response =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    else
        log_warn "Could not detect Raspberry Pi model"
    fi
}

# Check available storage
check_storage() {
    log_info "Checking available storage..."

    FREE_SPACE=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')

    if [ "$FREE_SPACE" -lt 10 ]; then
        log_error "Insufficient storage space"
        log_error "At least 10GB free space required, found ${FREE_SPACE}GB"
        exit 1
    fi

    log_info "Storage check passed: ${FREE_SPACE}GB free"
}

# Update system
update_system() {
    log_info "Updating system packages..."
    sudo apt-get update
    sudo apt-get upgrade -y
    log_info "System updated"
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."

    sudo apt-get install -y \
        python3-dev \
        python3-pip \
        python3-venv \
        cmake \
        build-essential \
        pkg-config \
        libjpeg-dev \
        libtiff5-dev \
        libpng-dev \
        libavcodec-dev \
        libavformat-dev \
        libswscale-dev \
        libv4l-dev \
        libxvidcore-dev \
        libx264-dev \
        libatlas-base-dev \
        gfortran \
        libhdf5-dev \
        libhdf5-serial-dev \
        libhdf5-103 \
        libqt5gui5 \
        libqt5webkit5 \
        libqt5test5 \
        python3-pyqt5 \
        libopenblas-dev \
        liblapack-dev

    log_info "System dependencies installed"
}

# Install Tesseract OCR
install_tesseract() {
    log_info "Installing Tesseract OCR..."

    sudo apt-get install -y \
        tesseract-ocr \
        libtesseract-dev \
        tesseract-ocr-eng

    log_info "Tesseract OCR installed"
}

# Install audio dependencies
install_audio_deps() {
    log_info "Installing audio dependencies..."

    sudo apt-get install -y \
        portaudio19-dev \
        python3-pyaudio \
        alsa-utils \
        espeak \
        espeak-ng \
        libespeak1 \
        libespeak-dev \
        mpg123

    log_info "Audio dependencies installed"
}

# Install camera dependencies
install_camera_deps() {
    log_info "Installing camera dependencies..."

    sudo apt-get install -y \
        v4l-utils \
        libv4l-dev

    log_info "Camera dependencies installed"
}

# Create virtual environment
setup_virtualenv() {
    log_info "Setting up Python virtual environment..."

    if [ -d "venv" ]; then
        log_warn "Virtual environment already exists. Recreate? (y/n)"
        read -r response
        if [[ $response =~ ^[Yy]$ ]]; then
            rm -rf venv
        else
            return
        fi
    fi

    python3 -m venv venv
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip setuptools wheel

    log_info "Virtual environment created"
}

# Install Python dependencies
install_python_deps() {
    log_info "Installing Python dependencies..."

    source venv/bin/activate

    # Install core dependencies first
    pip install numpy
    pip install Pillow

    # Install OpenCV
    log_info "Installing OpenCV (this may take a while)..."
    pip install opencv-python opencv-contrib-python

    # Install requirements
    log_info "Installing requirements from requirements.txt..."
    pip install -r requirements.txt

    log_info "Python dependencies installed"
}

# Download models
download_models() {
    log_info "Downloading pre-trained models..."

    mkdir -p models
    cd models

    # Download COCO SSD MobileNet for object detection
    if [ ! -f "ssd_mobilenet_v2_coco_quant.tflite" ]; then
        log_info "Downloading object detection model..."
        wget -q --show-progress \
            https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
        unzip -q coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
        mv detect.tflite ssd_mobilenet_v2_coco_quant.tflite
        mv labelmap.txt coco_labels.txt
        rm coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
        log_info "Object detection model downloaded"
    else
        log_info "Object detection model already exists"
    fi

    cd ..
    log_info "Models downloaded"
}

# Configure audio output
configure_audio() {
    log_info "Configuring audio output..."

    # Set default audio output to headphone jack
    sudo amixer cset numid=3 1

    # Test audio
    log_info "Testing audio output..."
    espeak "Audio test successful" 2>/dev/null || log_warn "Audio test failed"

    log_info "Audio configured"
}

# Configure camera
configure_camera() {
    log_info "Configuring camera..."

    # Enable camera
    sudo raspi-config nonint do_camera 0

    # Add user to video group
    sudo usermod -a -G video $USER

    log_info "Camera configured (reboot may be required)"
}

# Create systemd service
create_service() {
    log_info "Creating systemd service..."

    SERVICE_FILE="/etc/systemd/system/visionguardian.service"
    WORKING_DIR=$(pwd)

    sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=VisionGuardian - Smart Assistant for Visually Impaired
After=network.target sound.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORKING_DIR
Environment="PATH=$WORKING_DIR/venv/bin"
ExecStart=$WORKING_DIR/venv/bin/python3 $WORKING_DIR/src/main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload

    log_info "Systemd service created"
    log_info "To enable on boot: sudo systemctl enable visionguardian"
    log_info "To start now: sudo systemctl start visionguardian"
}

# Create sample face directory
setup_face_recognition() {
    log_info "Setting up facial recognition..."

    mkdir -p data/known_faces

    log_info "To add known faces:"
    log_info "  1. Create directory: data/known_faces/[person_name]"
    log_info "  2. Add face photos: data/known_faces/[person_name]/photo1.jpg"
    log_info "  3. Run: python3 scripts/train_faces.py"
}

# Set permissions
set_permissions() {
    log_info "Setting permissions..."

    chmod +x src/main.py
    chmod +x scripts/*.py 2>/dev/null || true

    log_info "Permissions set"
}

# Create startup script
create_startup_script() {
    log_info "Creating startup script..."

    cat > start.sh <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 src/main.py
EOF

    chmod +x start.sh
    log_info "Startup script created: ./start.sh"
}

# Main installation process
main() {
    log_info "Starting VisionGuardian installation..."
    log_info "This will take approximately 20-30 minutes"
    echo ""

    # System checks
    check_architecture
    check_raspberry_pi
    check_storage

    echo ""
    log_info "System checks passed. Continue with installation? (y/n)"
    read -r response
    if [[ ! $response =~ ^[Yy]$ ]]; then
        log_info "Installation cancelled"
        exit 0
    fi

    # Installation steps
    update_system
    install_system_deps
    install_tesseract
    install_audio_deps
    install_camera_deps
    setup_virtualenv
    install_python_deps
    download_models
    configure_audio
    configure_camera
    create_service
    setup_face_recognition
    set_permissions
    create_startup_script

    echo ""
    log_info "================================"
    log_info "Installation completed successfully!"
    log_info "================================"
    echo ""
    log_info "Next steps:"
    log_info "  1. Reboot the system: sudo reboot"
    log_info "  2. Add known faces to: data/known_faces/[name]/"
    log_info "  3. Run training: python3 scripts/train_faces.py"
    log_info "  4. Start application: ./start.sh"
    log_info "  or"
    log_info "  5. Enable auto-start: sudo systemctl enable visionguardian"
    echo ""
    log_info "Configuration file: config/settings.yaml"
    log_info "Documentation: README.md"
    echo ""
}

# Run main installation
main
