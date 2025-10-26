#!/bin/bash
# Quick fix for test_vision.py variable scope bug

echo "Fixing test_vision.py..."

cd "$(dirname "$0")"

# Create backup
cp test_vision.py test_vision.py.backup

# Apply fix using sed
sed -i '97a\        enhanced_success = False\n' test_vision.py
sed -i 's/ENHANCED_AVAILABLE = False/# Enhanced failed, using basic/g' test_vision.py
sed -i 's/if not ENHANCED_AVAILABLE or self.object_detector is None:/if not enhanced_success:/g' test_vision.py
sed -i '/if self.object_detector.initialize():/a\                enhanced_success = True' test_vision.py

echo "Fix applied! Backup saved as test_vision.py.backup"
echo "You can now run: python3 test_vision.py"
