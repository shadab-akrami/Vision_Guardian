"""
Currency Detection Module for VisionGuardian
Identifies bills and coins for visually impaired users
Optimized for Raspberry Pi 5
"""

import cv2
import numpy as np
import logging
from typing import Optional, Dict

from utils import Config, MODELS_DIR


class CurrencyDetection:
    """Detects and identifies currency (bills and coins)"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.CurrencyDetection')

        # Settings
        self.enabled = config.get('currency_detection.enabled', True)
        self.supported_currencies = config.get('currency_detection.supported_currencies', ['USD'])
        self.confidence_threshold = config.get('currency_detection.confidence_threshold', 0.7)
        self.announcement_format = config.get('currency_detection.announcement_format', 'detailed')

        # Currency model (would be loaded here)
        self.model = None

        # US Dollar denominations (color-based heuristics as fallback)
        self.usd_denominations = {
            1: 'one dollar',
            5: 'five dollars',
            10: 'ten dollars',
            20: 'twenty dollars',
            50: 'fifty dollars',
            100: 'one hundred dollars'
        }

    def initialize(self) -> bool:
        """
        Initialize currency detection

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            self.logger.info("Initializing currency detection...")

            # Load currency detection model (if available)
            # In production, this would load a trained TFLite model
            self.logger.info("Using heuristic-based currency detection")

            self.logger.info("Currency detection initialized")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing currency detection: {e}")
            return False

    def detect_currency(self, frame: np.ndarray) -> Optional[Dict]:
        """
        Detect and identify currency in frame

        Args:
            frame: Input frame

        Returns:
            Currency information or None
        """
        if not self.enabled:
            return None

        try:
            # Simple heuristic-based detection for US bills
            # In production, use trained model
            result = self._detect_usd_bill_heuristic(frame)

            return result

        except Exception as e:
            self.logger.error(f"Error detecting currency: {e}")
            return None

    def _detect_usd_bill_heuristic(self, frame: np.ndarray) -> Optional[Dict]:
        """
        Heuristic-based USD bill detection (basic implementation)

        Args:
            frame: Input frame

        Returns:
            Detection result
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Look for rectangular shapes with appropriate aspect ratio
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by area
            if area < 10000:
                continue

            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / float(h) if h > 0 else 0

            # US bills have aspect ratio ~2.35:1
            if 2.0 < aspect_ratio < 2.7:
                # Extract region
                bill_region = frame[y:y+h, x:x+w]

                # Analyze color to estimate denomination (very basic)
                denomination = self._estimate_denomination_by_color(bill_region)

                if denomination:
                    return {
                        'amount': denomination,
                        'currency': 'USD',
                        'confidence': 0.6,  # Low confidence for heuristic
                        'bbox': (x, y, x+w, y+h)
                    }

        return None

    def _estimate_denomination_by_color(self, region: np.ndarray) -> Optional[int]:
        """
        Estimate bill denomination by color analysis (very basic)

        Args:
            region: Bill region

        Returns:
            Estimated denomination or None
        """
        # This is a placeholder - real implementation would use ML model
        # US bills are primarily green with subtle color differences

        avg_color = np.mean(region, axis=(0, 1))

        # Very basic heuristic (not accurate, just for demonstration)
        # In production, use trained classifier
        return 20  # Default guess

    def format_announcement(self, detection: Dict) -> str:
        """
        Format currency detection for announcement

        Args:
            detection: Detection result

        Returns:
            Announcement text
        """
        if not detection:
            return "No currency detected"

        amount = detection['amount']
        currency = detection['currency']

        if self.announcement_format == 'simple':
            if currency == 'USD':
                return f"{amount} dollars"
            else:
                return f"{amount} {currency}"

        elif self.announcement_format == 'detailed':
            if currency == 'USD':
                denomination_name = self.usd_denominations.get(amount, f"{amount} dollars")
                confidence = detection['confidence'] * 100
                return f"Detected {denomination_name}, confidence {confidence:.0f}%"
            else:
                return f"{amount} {currency}"

        return str(amount)

    def draw_detection(self, frame: np.ndarray, detection: Dict) -> np.ndarray:
        """
        Draw currency detection on frame

        Args:
            frame: Input frame
            detection: Detection result

        Returns:
            Frame with detection drawn
        """
        if not detection:
            return frame

        x1, y1, x2, y2 = detection['bbox']

        # Draw box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Draw label
        label = f"${detection['amount']}"
        cv2.putText(frame, label, (x1, y1 - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        return frame


if __name__ == "__main__":
    from utils import setup_logging
    setup_logging("INFO")

    config = Config()
    detector = CurrencyDetection(config)

    if detector.initialize():
        print("Currency detection initialized")
        print("Note: Currently using basic heuristics")
        print("For production, train a custom model for currency recognition")
    else:
        print("Failed to initialize currency detection")
