#!/bin/bash
# USB Webcam Fix for Raspberry Pi
# Fixes the uniform gray pixels issue with USB webcams

echo "=========================================="
echo "USB Webcam Fix for Raspberry Pi"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Note: Some commands may require sudo${NC}"
fi

echo "Step 1: Detecting USB cameras..."
echo ""

# List video devices
if ls /dev/video* 1> /dev/null 2>&1; then
    echo -e "${GREEN}✓ Video devices found:${NC}"
    ls -l /dev/video*
    echo ""
else
    echo -e "${RED}✗ No video devices found${NC}"
    echo "Please check if your USB camera is connected"
    exit 1
fi

# Check v4l-utils
echo "Step 2: Checking v4l-utils..."
if ! command -v v4l2-ctl &> /dev/null; then
    echo -e "${YELLOW}! v4l-utils not installed${NC}"
    echo "Installing v4l-utils..."
    sudo apt update
    sudo apt install -y v4l-utils
else
    echo -e "${GREEN}✓ v4l-utils installed${NC}"
fi
echo ""

# List all cameras
echo "Step 3: Listing all cameras..."
v4l2-ctl --list-devices
echo ""

# For each video device, show capabilities
echo "Step 4: Checking camera capabilities..."
for device in /dev/video*; do
    if [ -c "$device" ]; then
        echo "----------------------------------------"
        echo "Device: $device"
        echo "----------------------------------------"

        # Check if it's a capture device (not metadata)
        if v4l2-ctl -d "$device" --all 2>/dev/null | grep -q "Video Capture"; then
            echo -e "${GREEN}✓ This is a video capture device${NC}"

            # Show supported formats
            echo ""
            echo "Supported formats:"
            v4l2-ctl -d "$device" --list-formats-ext 2>/dev/null | grep -A 2 "MJPEG\|YUYV"

            # Show current settings
            echo ""
            echo "Current settings:"
            v4l2-ctl -d "$device" -V 2>/dev/null

        else
            echo -e "${YELLOW}! Not a video capture device (might be metadata)${NC}"
        fi
        echo ""
    fi
done

# Fix: Reset USB camera settings
echo "Step 5: Resetting USB camera controls..."
echo ""

# Find the actual capture device (usually video0)
CAMERA_DEVICE="/dev/video0"

# Try video0, video1, video2
for device in /dev/video0 /dev/video1 /dev/video2; do
    if [ -c "$device" ] && v4l2-ctl -d "$device" --all 2>/dev/null | grep -q "Video Capture"; then
        CAMERA_DEVICE="$device"
        echo -e "${GREEN}Using camera: $CAMERA_DEVICE${NC}"
        break
    fi
done

echo ""
echo "Applying optimal settings for $CAMERA_DEVICE..."

# Reset controls to defaults
v4l2-ctl -d "$CAMERA_DEVICE" --set-ctrl=brightness=128 2>/dev/null
v4l2-ctl -d "$CAMERA_DEVICE" --set-ctrl=contrast=128 2>/dev/null
v4l2-ctl -d "$CAMERA_DEVICE" --set-ctrl=saturation=128 2>/dev/null
v4l2-ctl -d "$CAMERA_DEVICE" --set-ctrl=white_balance_temperature_auto=1 2>/dev/null
v4l2-ctl -d "$CAMERA_DEVICE" --set-ctrl=gain=0 2>/dev/null
v4l2-ctl -d "$CAMERA_DEVICE" --set-ctrl=power_line_frequency=1 2>/dev/null
v4l2-ctl -d "$CAMERA_DEVICE" --set-ctrl=white_balance_temperature=4000 2>/dev/null
v4l2-ctl -d "$CAMERA_DEVICE" --set-ctrl=sharpness=128 2>/dev/null
v4l2-ctl -d "$CAMERA_DEVICE" --set-ctrl=backlight_compensation=0 2>/dev/null
v4l2-ctl -d "$CAMERA_DEVICE" --set-ctrl=exposure_auto=3 2>/dev/null
v4l2-ctl -d "$CAMERA_DEVICE" --set-ctrl=exposure_absolute=166 2>/dev/null
v4l2-ctl -d "$CAMERA_DEVICE" --set-ctrl=exposure_auto_priority=0 2>/dev/null

echo -e "${GREEN}✓ Camera settings applied${NC}"
echo ""

# Check permissions
echo "Step 6: Checking permissions..."
if groups $USER | grep -q video; then
    echo -e "${GREEN}✓ User is in 'video' group${NC}"
else
    echo -e "${YELLOW}! User not in 'video' group${NC}"
    echo "Adding user to video group..."
    sudo usermod -a -G video $USER
    echo -e "${YELLOW}⚠ Please log out and log back in (or reboot) for changes to take effect${NC}"
fi
echo ""

# Create udev rule for persistent settings
echo "Step 7: Creating udev rule for persistent settings..."
UDEV_RULE="/etc/udev/rules.d/99-logitech-webcam.rules"

sudo tee "$UDEV_RULE" > /dev/null << 'EOF'
# Logitech USB Webcam - Set defaults on plug
ACTION=="add", SUBSYSTEM=="video4linux", ATTRS{idVendor}=="046d", RUN+="/usr/bin/v4l2-ctl -d $devnode --set-ctrl=brightness=128,contrast=128,saturation=128"
EOF

echo -e "${GREEN}✓ Udev rule created at $UDEV_RULE${NC}"
echo ""

# Reload udev rules
sudo udevadm control --reload-rules

echo "=========================================="
echo "Configuration complete!"
echo "=========================================="
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Test camera with: python3 test_camera_backends.py"
echo "2. If it still doesn't work, try:"
echo "   - Unplug and replug the USB camera"
echo "   - Try different USB port"
echo "   - Reboot: sudo reboot"
echo ""
echo "If you changed groups, you MUST log out/reboot first!"
echo ""
