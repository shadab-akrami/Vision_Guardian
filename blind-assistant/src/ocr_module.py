"""
OCR Module for VisionGuardian
Text recognition and reading for visually impaired users
Optimized for Raspberry Pi 5 (64-bit ARM64)
"""

import cv2
import numpy as np
import logging
import time
from typing import List, Dict, Optional, Tuple

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("pytesseract not available")

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logging.warning("easyocr not available")

from utils import Config, PerformanceMonitor


class OCRModule:
    """Handles optical character recognition (text reading)"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.OCRModule')

        # Settings
        self.enabled = config.get('ocr.enabled', True)
        self.engine = config.get('ocr.engine', 'tesseract')
        self.languages = config.get('ocr.languages', ['eng'])
        self.confidence_threshold = config.get('ocr.confidence_threshold', 60)
        self.preprocessing = config.get('ocr.preprocessing', True)
        self.detect_orientation = config.get('ocr.detect_orientation', True)
        self.announcement_mode = config.get('ocr.announcement_mode', 'sentences')

        # OCR engine
        self.reader = None

        # Performance
        self.performance = PerformanceMonitor()

    def initialize(self) -> bool:
        """
        Initialize OCR engine

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            self.logger.info(f"Initializing OCR engine: {self.engine}")

            if self.engine == 'tesseract':
                if not TESSERACT_AVAILABLE:
                    self.logger.error("Tesseract not available")
                    return False

                # Test tesseract
                try:
                    version = pytesseract.get_tesseract_version()
                    self.logger.info(f"Tesseract version: {version}")
                except Exception as e:
                    self.logger.error(f"Tesseract not properly installed: {e}")
                    return False

            elif self.engine == 'easyocr':
                if not EASYOCR_AVAILABLE:
                    self.logger.error("EasyOCR not available")
                    return False

                # Initialize EasyOCR reader
                self.logger.info("Loading EasyOCR model (this may take a moment)...")
                self.reader = easyocr.Reader(self.languages, gpu=False)
                self.logger.info("EasyOCR initialized")

            else:
                self.logger.error(f"Unknown OCR engine: {self.engine}")
                return False

            self.logger.info("OCR module initialized")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing OCR: {e}")
            return False

    def read_text(self, frame: np.ndarray) -> Dict:
        """
        Read text from frame

        Args:
            frame: Input frame (BGR format)

        Returns:
            Dictionary with OCR results
        """
        if not self.enabled:
            return {'text': '', 'confidence': 0, 'lines': []}

        self.performance.start('ocr')

        try:
            # Preprocess image
            if self.preprocessing:
                processed = self._preprocess_image(frame)
            else:
                processed = frame

            # Run OCR based on engine
            if self.engine == 'tesseract':
                result = self._ocr_tesseract(processed)
            elif self.engine == 'easyocr':
                result = self._ocr_easyocr(processed)
            else:
                result = {'text': '', 'confidence': 0, 'lines': []}

            self.performance.end('ocr')
            return result

        except Exception as e:
            self.logger.error(f"Error reading text: {e}")
            self.performance.end('ocr')
            return {'text': '', 'confidence': 0, 'lines': []}

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results

        Args:
            image: Input image

        Returns:
            Preprocessed image
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply bilateral filter to reduce noise while keeping edges sharp
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)

        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        # Optional: Detect and correct orientation
        if self.detect_orientation:
            try:
                # Detect orientation using Tesseract
                osd = pytesseract.image_to_osd(binary)
                angle = int([line for line in osd.split('\n') if 'Rotate:' in line][0].split(':')[1].strip())

                if angle != 0:
                    # Rotate image
                    if angle == 90:
                        binary = cv2.rotate(binary, cv2.ROTATE_90_CLOCKWISE)
                    elif angle == 180:
                        binary = cv2.rotate(binary, cv2.ROTATE_180)
                    elif angle == 270:
                        binary = cv2.rotate(binary, cv2.ROTATE_90_COUNTERCLOCKWISE)
            except:
                pass  # If orientation detection fails, continue with original

        return binary

    def _ocr_tesseract(self, image: np.ndarray) -> Dict:
        """
        Perform OCR using Tesseract

        Args:
            image: Preprocessed image

        Returns:
            OCR results
        """
        try:
            # Get detailed OCR data
            lang = '+'.join(self.languages)
            data = pytesseract.image_to_data(
                image,
                lang=lang,
                output_type=pytesseract.Output.DICT
            )

            # Filter by confidence
            lines = []
            text_parts = []

            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                confidence = data['conf'][i]

                if text and confidence != -1 and confidence >= self.confidence_threshold:
                    line_info = {
                        'text': text,
                        'confidence': confidence,
                        'bbox': (
                            data['left'][i],
                            data['top'][i],
                            data['left'][i] + data['width'][i],
                            data['top'][i] + data['height'][i]
                        )
                    }
                    lines.append(line_info)
                    text_parts.append(text)

            # Combine text
            full_text = ' '.join(text_parts)

            # Calculate average confidence
            if lines:
                avg_confidence = sum(line['confidence'] for line in lines) / len(lines)
            else:
                avg_confidence = 0

            return {
                'text': full_text,
                'confidence': avg_confidence,
                'lines': lines
            }

        except Exception as e:
            self.logger.error(f"Tesseract OCR error: {e}")
            return {'text': '', 'confidence': 0, 'lines': []}

    def _ocr_easyocr(self, image: np.ndarray) -> Dict:
        """
        Perform OCR using EasyOCR

        Args:
            image: Preprocessed image

        Returns:
            OCR results
        """
        try:
            if self.reader is None:
                return {'text': '', 'confidence': 0, 'lines': []}

            # Run EasyOCR
            results = self.reader.readtext(image)

            lines = []
            text_parts = []

            for bbox, text, confidence in results:
                confidence_percent = confidence * 100

                if confidence_percent >= self.confidence_threshold:
                    # Convert bbox to simple format
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    bbox_simple = (
                        int(min(x_coords)),
                        int(min(y_coords)),
                        int(max(x_coords)),
                        int(max(y_coords))
                    )

                    line_info = {
                        'text': text,
                        'confidence': confidence_percent,
                        'bbox': bbox_simple
                    }
                    lines.append(line_info)
                    text_parts.append(text)

            # Combine text
            full_text = ' '.join(text_parts)

            # Calculate average confidence
            if lines:
                avg_confidence = sum(line['confidence'] for line in lines) / len(lines)
            else:
                avg_confidence = 0

            return {
                'text': full_text,
                'confidence': avg_confidence,
                'lines': lines
            }

        except Exception as e:
            self.logger.error(f"EasyOCR error: {e}")
            return {'text': '', 'confidence': 0, 'lines': []}

    def format_for_announcement(self, ocr_result: Dict) -> str:
        """
        Format OCR text for audio announcement

        Args:
            ocr_result: OCR result dictionary

        Returns:
            Formatted text for announcement
        """
        text = ocr_result.get('text', '').strip()

        if not text:
            return ""

        # Format based on announcement mode
        if self.announcement_mode == 'full':
            return text

        elif self.announcement_mode == 'sentences':
            # Break into sentences and announce first few
            sentences = text.replace('!', '.').replace('?', '.').split('.')
            sentences = [s.strip() for s in sentences if s.strip()]
            return '. '.join(sentences[:3])  # First 3 sentences

        elif self.announcement_mode == 'words':
            # Announce word by word (up to 10 words)
            words = text.split()[:10]
            return ' '.join(words)

        return text

    def draw_text_boxes(self, frame: np.ndarray, ocr_result: Dict) -> np.ndarray:
        """
        Draw text bounding boxes on frame

        Args:
            frame: Input frame
            ocr_result: OCR results

        Returns:
            Frame with text boxes drawn
        """
        for line in ocr_result.get('lines', []):
            left, top, right, bottom = line['bbox']
            text = line['text']
            confidence = line['confidence']

            # Draw box
            cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)

            # Draw text label
            label = f"{confidence:.0f}%"
            cv2.putText(
                frame,
                label,
                (left, max(top - 5, 0)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 0),
                2
            )

        return frame

    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        return self.performance.get_stats('ocr')


if __name__ == "__main__":
    # Test OCR module
    from utils import setup_logging
    setup_logging("INFO", "ocr_test.log")

    config = Config()
    ocr = OCRModule(config)

    if ocr.initialize():
        print("OCR module initialized")
        print("Engine:", ocr.engine)
        print("Languages:", ocr.languages)
    else:
        print("Failed to initialize OCR module")
