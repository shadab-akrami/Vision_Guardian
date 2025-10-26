#!/bin/bash
################################################################################
# Download Pre-trained Models for VisionGuardian
# Run this script to download all required AI models
################################################################################

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Create models directory
mkdir -p models
cd models

log_info "Downloading pre-trained models for VisionGuardian..."
echo ""

# 1. Object Detection Model (COCO SSD MobileNet)
if [ ! -f "ssd_mobilenet_v2_coco_quant.tflite" ]; then
    log_info "Downloading object detection model (SSD MobileNet v2)..."
    wget -q --show-progress \
        https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip

    unzip -q coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
    mv detect.tflite ssd_mobilenet_v2_coco_quant.tflite
    mv labelmap.txt coco_labels.txt
    rm coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip

    log_info "Object detection model downloaded ✓"
else
    log_warn "Object detection model already exists"
fi

echo ""

# 2. Alternative: EfficientDet Lite (more accurate but slower)
# Uncomment to download
# if [ ! -f "efficientdet_lite0.tflite" ]; then
#     log_info "Downloading EfficientDet Lite model..."
#     wget -q --show-progress \
#         https://tfhub.dev/tensorflow/lite-model/efficientdet/lite0/detection/metadata/1?lite-format=tflite \
#         -O efficientdet_lite0.tflite
#     log_info "EfficientDet model downloaded ✓"
# fi

# 3. Depth Estimation Model (MiDaS) - Optional
# Uncomment to download
# if [ ! -f "midas_v21_small_256_quantized.tflite" ]; then
#     log_info "Downloading depth estimation model (MiDaS)..."
#     wget -q --show-progress \
#         https://github.com/isl-org/MiDaS/releases/download/v2_1/midas_v21_small_256.pt
#     # Note: Convert to TFLite format using conversion script
#     log_info "MiDaS model downloaded ✓"
# fi

cd ..

echo ""
log_info "============================================"
log_info "Model download complete!"
log_info "============================================"
echo ""
log_info "Downloaded models:"
ls -lh models/

echo ""
log_info "Total size:"
du -sh models/

echo ""
