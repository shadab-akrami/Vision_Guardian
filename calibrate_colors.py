#!/usr/bin/env python3
"""
Quick Color Calibration Tool
Helps you find optimal color settings for your camera
"""

import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import cv2
import yaml
from utils import Config
from camera_handler import CameraHandler

def print_header():
    print("=" * 60)
    print("VisionGuardian - Color Calibration Tool")
    print("=" * 60)
    print()

def get_current_settings():
    """Load current settings from config"""
    config_path = Path(__file__).parent / 'config' / 'settings.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    camera = config.get('camera', {})
    correction = camera.get('color_correction', {})

    return {
        'brightness': camera.get('brightness', 55),
        'contrast': camera.get('contrast', 60),
        'saturation': camera.get('saturation', 55),
        'brightness_adjust': correction.get('brightness_adjust', 0),
        'contrast_adjust': correction.get('contrast_adjust', 5),
        'saturation_adjust': correction.get('saturation_adjust', 0),
        'gamma': correction.get('gamma', 1.0)
    }

def save_settings(settings):
    """Save settings to config file"""
    config_path = Path(__file__).parent / 'config' / 'settings.yaml'

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Update camera settings
    config['camera']['brightness'] = settings['brightness']
    config['camera']['contrast'] = settings['contrast']
    config['camera']['saturation'] = settings['saturation']

    # Update color correction
    if 'color_correction' not in config['camera']:
        config['camera']['color_correction'] = {}

    config['camera']['color_correction']['brightness_adjust'] = settings['brightness_adjust']
    config['camera']['color_correction']['contrast_adjust'] = settings['contrast_adjust']
    config['camera']['color_correction']['saturation_adjust'] = settings['saturation_adjust']
    config['camera']['color_correction']['gamma'] = settings['gamma']

    # Save back
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    print(f"\n✅ Settings saved to {config_path}")

def print_current_settings(settings):
    """Display current settings"""
    print("\nCurrent Settings:")
    print("-" * 40)
    print(f"  Brightness:        {settings['brightness']}")
    print(f"  Contrast:          {settings['contrast']}")
    print(f"  Saturation:        {settings['saturation']}")
    print()
    print("  Software Adjustments:")
    print(f"    Brightness:      {settings['brightness_adjust']:+d}")
    print(f"    Contrast:        {settings['contrast_adjust']:+d}")
    print(f"    Saturation:      {settings['saturation_adjust']:+d}")
    print(f"    Gamma:           {settings['gamma']:.2f}")
    print("-" * 40)

def print_menu():
    """Display adjustment menu"""
    print("\nAdjustments:")
    print("  1. Increase Brightness (+5)")
    print("  2. Decrease Brightness (-5)")
    print("  3. Increase Contrast (+5)")
    print("  4. Decrease Contrast (-5)")
    print("  5. Increase Saturation (+5)")
    print("  6. Decrease Saturation (-5)")
    print("\nAdvanced:")
    print("  7. Increase Software Brightness (+5)")
    print("  8. Decrease Software Brightness (-5)")
    print("  9. Increase Gamma (+0.1)")
    print("  0. Decrease Gamma (-0.1)")
    print("\nActions:")
    print("  r. Reset to defaults")
    print("  s. Save and exit")
    print("  q. Quit without saving")

def reset_to_defaults():
    """Get default settings"""
    return {
        'brightness': 55,
        'contrast': 60,
        'saturation': 55,
        'brightness_adjust': 0,
        'contrast_adjust': 5,
        'saturation_adjust': 0,
        'gamma': 1.0
    }

def main():
    print_header()

    # Load current settings
    settings = get_current_settings()
    print_current_settings(settings)

    print("\n" + "=" * 60)
    print("CALIBRATION GUIDE")
    print("=" * 60)
    print("""
Common Issues:

1. Colors look INVERTED/NEGATIVE
   → Press '2' to decrease brightness
   → Press '6' to decrease saturation

2. Image too BRIGHT/WASHED OUT
   → Press '4' to decrease contrast
   → Press '2' to decrease brightness

3. Colors too VIBRANT/NEON
   → Press '6' to decrease saturation

4. Image too DARK
   → Press '1' to increase brightness
   → Press '9' to increase gamma

5. Colors look FLAT/GRAY
   → Press '5' to increase saturation
   → Press '3' to increase contrast

Make small adjustments (5 points at a time) and test!
""")

    # Recommendation based on common Raspberry Pi camera issues
    print("💡 RECOMMENDED STARTING ADJUSTMENTS:")
    print("   For most Raspberry Pi cameras, try:")
    print("   - Brightness: 50-60")
    print("   - Contrast: 60-70")
    print("   - Saturation: 50-60")
    print()

    input("Press Enter to start adjustment...")

    while True:
        print("\n" + "=" * 60)
        print_current_settings(settings)
        print_menu()

        choice = input("\nEnter choice: ").strip().lower()

        if choice == '1':
            settings['brightness'] = min(100, settings['brightness'] + 5)
            print(f"✓ Brightness → {settings['brightness']}")
        elif choice == '2':
            settings['brightness'] = max(0, settings['brightness'] - 5)
            print(f"✓ Brightness → {settings['brightness']}")
        elif choice == '3':
            settings['contrast'] = min(100, settings['contrast'] + 5)
            print(f"✓ Contrast → {settings['contrast']}")
        elif choice == '4':
            settings['contrast'] = max(0, settings['contrast'] - 5)
            print(f"✓ Contrast → {settings['contrast']}")
        elif choice == '5':
            settings['saturation'] = min(100, settings['saturation'] + 5)
            print(f"✓ Saturation → {settings['saturation']}")
        elif choice == '6':
            settings['saturation'] = max(0, settings['saturation'] - 5)
            print(f"✓ Saturation → {settings['saturation']}")
        elif choice == '7':
            settings['brightness_adjust'] = min(50, settings['brightness_adjust'] + 5)
            print(f"✓ Software Brightness → {settings['brightness_adjust']:+d}")
        elif choice == '8':
            settings['brightness_adjust'] = max(-50, settings['brightness_adjust'] - 5)
            print(f"✓ Software Brightness → {settings['brightness_adjust']:+d}")
        elif choice == '9':
            settings['gamma'] = min(2.0, settings['gamma'] + 0.1)
            print(f"✓ Gamma → {settings['gamma']:.2f}")
        elif choice == '0':
            settings['gamma'] = max(0.5, settings['gamma'] - 0.1)
            print(f"✓ Gamma → {settings['gamma']:.2f}")
        elif choice == 'r':
            settings = reset_to_defaults()
            print("✓ Reset to defaults")
        elif choice == 's':
            save_settings(settings)
            print("\n✅ Settings saved successfully!")
            print("\nNow run:")
            print("  python3 test_vision.py  (to verify)")
            print("  python3 src/main.py     (to use the system)")
            break
        elif choice == 'q':
            print("\n❌ Exiting without saving")
            break
        else:
            print("❌ Invalid choice")

        # Show recommendation
        if settings['brightness'] < 40:
            print("\n⚠️  WARNING: Brightness is very low. Image may be too dark.")
        elif settings['brightness'] > 80:
            print("\n⚠️  WARNING: Brightness is very high. Image may be washed out.")

        if settings['saturation'] < 30:
            print("\n⚠️  WARNING: Saturation is very low. Colors may look gray.")
        elif settings['saturation'] > 80:
            print("\n⚠️  WARNING: Saturation is very high. Colors may look artificial.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Exiting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
