"""
AI Vision Module for VisionGuardian
Uses cloud-based AI (OpenAI Vision, Google Cloud Vision) for comprehensive scene understanding
Provides accurate object detection, text reading, and scene descriptions
"""

import cv2
import numpy as np
import logging
import time
import base64
from typing import Dict, List, Optional
import requests

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("openai not available")

try:
    from google.cloud import vision as google_vision
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False
    logging.warning("google-cloud-vision not available")

from utils import Config


class AIVision:
    """
    AI-powered comprehensive vision analysis using cloud services
    Provides superior recognition compared to local models
    """

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.AIVision')

        # Settings
        self.enabled = config.get('ai_vision.enabled', False)
        self.primary_service = config.get('ai_vision.primary_service', 'openai')  # 'openai' or 'google'
        self.fallback_to_local = config.get('ai_vision.fallback_to_local', True)
        self.detail_level = config.get('ai_vision.detail_level', 'high')
        self.max_retries = config.get('ai_vision.max_retries', 2)
        self.timeout = config.get('ai_vision.timeout_seconds', 10)

        # API keys
        self.openai_api_key = config.get('ai_vision.openai_api_key', '')
        self.google_credentials_path = config.get('ai_vision.google_credentials_path', '')

        # Rate limiting
        self.min_interval = config.get('ai_vision.min_interval_seconds', 2)
        self.last_request_time = 0

        # Clients
        self.openai_client = None
        self.google_client = None

        # Cache
        self.last_result = None

    def initialize(self) -> bool:
        """
        Initialize AI vision services

        Returns:
            True if at least one service is available
        """
        if not self.enabled:
            self.logger.info("AI Vision is disabled")
            return False

        try:
            self.logger.info("Initializing AI Vision services...")
            initialized = False

            # Initialize OpenAI
            if self.openai_api_key and OPENAI_AVAILABLE:
                try:
                    openai.api_key = self.openai_api_key
                    self.openai_client = openai
                    self.logger.info("OpenAI Vision API initialized")
                    initialized = True
                except Exception as e:
                    self.logger.error(f"Failed to initialize OpenAI: {e}")

            # Initialize Google Cloud Vision
            if self.google_credentials_path and GOOGLE_VISION_AVAILABLE:
                try:
                    import os
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.google_credentials_path
                    self.google_client = google_vision.ImageAnnotatorClient()
                    self.logger.info("Google Cloud Vision initialized")
                    initialized = True
                except Exception as e:
                    self.logger.error(f"Failed to initialize Google Vision: {e}")

            if not initialized:
                self.logger.warning("No AI vision services available - check API keys")
                self.logger.info("To enable AI Vision:")
                self.logger.info("  1. Get OpenAI API key from https://platform.openai.com/api-keys")
                self.logger.info("  2. Or get Google Cloud Vision credentials")
                self.logger.info("  3. Update config/settings.yaml with your API key")
                return False

            self.logger.info("AI Vision initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing AI Vision: {e}")
            return False

    def analyze_scene(self, frame: np.ndarray, query: str = None) -> Dict:
        """
        Comprehensive scene analysis using AI

        Args:
            frame: Input frame (BGR format)
            query: Optional specific question about the scene

        Returns:
            Dictionary with analysis results
        """
        if not self.enabled:
            return {'success': False, 'error': 'AI Vision disabled'}

        # Rate limiting
        current_time = time.time()
        if current_time - self.last_request_time < self.min_interval:
            if self.last_result:
                return self.last_result
            time.sleep(self.min_interval - (current_time - self.last_request_time))

        try:
            # Encode image
            image_base64 = self._encode_image(frame)

            # Try primary service
            result = None
            if self.primary_service == 'openai' and self.openai_client:
                result = self._analyze_openai(image_base64, query)
            elif self.primary_service == 'google' and self.google_client:
                result = self._analyze_google(frame, query)

            # Try fallback service if primary fails
            if not result or not result.get('success'):
                if self.primary_service == 'openai' and self.google_client:
                    self.logger.info("Falling back to Google Vision")
                    result = self._analyze_google(frame, query)
                elif self.primary_service == 'google' and self.openai_client:
                    self.logger.info("Falling back to OpenAI Vision")
                    result = self._analyze_openai(image_base64, query)

            self.last_request_time = time.time()
            self.last_result = result
            return result

        except Exception as e:
            self.logger.error(f"Error analyzing scene: {e}")
            return {'success': False, 'error': str(e)}

    def _analyze_openai(self, image_base64: str, query: str = None) -> Dict:
        """
        Analyze scene using OpenAI Vision API

        Args:
            image_base64: Base64 encoded image
            query: Optional specific query

        Returns:
            Analysis results
        """
        try:
            # Build prompt based on query and detail level
            if query:
                prompt = query
            else:
                if self.detail_level == 'low':
                    prompt = "Briefly describe what you see in one sentence for a visually impaired person."
                elif self.detail_level == 'high':
                    prompt = """Describe this scene in detail for a visually impaired person. Include:
1. Overall environment (indoor/outdoor, type of location)
2. All visible objects and their positions
3. Any people present
4. Any visible text
5. Colors and lighting
6. Potential obstacles or hazards
Be specific and helpful."""
                else:  # medium
                    prompt = "Describe what you see in this image for a visually impaired person. Include objects, people, text, and any important details."

            # Call OpenAI API
            response = self.openai_client.ChatCompletion.create(
                model="gpt-4o",  # GPT-4 Vision model
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    "detail": "high" if self.detail_level == 'high' else "auto"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                timeout=self.timeout
            )

            description = response.choices[0].message.content.strip()

            return {
                'success': True,
                'description': description,
                'service': 'openai',
                'model': 'gpt-4-vision'
            }

        except Exception as e:
            self.logger.error(f"OpenAI Vision error: {e}")
            return {'success': False, 'error': str(e)}

    def _analyze_google(self, frame: np.ndarray, query: str = None) -> Dict:
        """
        Analyze scene using Google Cloud Vision API

        Args:
            frame: Input frame
            query: Optional specific query

        Returns:
            Analysis results
        """
        try:
            # Encode image for Google Vision
            _, buffer = cv2.imencode('.jpg', frame)
            content = buffer.tobytes()
            image = google_vision.Image(content=content)

            # Perform multiple detections
            features = [
                {'type_': google_vision.Feature.Type.LABEL_DETECTION, 'max_results': 20},
                {'type_': google_vision.Feature.Type.OBJECT_LOCALIZATION, 'max_results': 20},
                {'type_': google_vision.Feature.Type.TEXT_DETECTION},
                {'type_': google_vision.Feature.Type.FACE_DETECTION},
                {'type_': google_vision.Feature.Type.LANDMARK_DETECTION},
            ]

            request = google_vision.AnnotateImageRequest(
                image=image,
                features=features
            )

            response = self.google_client.annotate_image(request=request, timeout=self.timeout)

            # Build comprehensive description
            description_parts = []

            # Labels (scene understanding)
            if response.label_annotations:
                labels = [label.description for label in response.label_annotations[:5]]
                description_parts.append(f"Scene type: {', '.join(labels)}")

            # Objects
            if response.localized_object_annotations:
                objects = []
                for obj in response.localized_object_annotations[:10]:
                    objects.append(f"{obj.name} ({obj.score:.0%} confidence)")
                description_parts.append(f"Objects detected: {', '.join(objects)}")

            # Text
            if response.text_annotations and len(response.text_annotations) > 0:
                text = response.text_annotations[0].description.strip()
                if text:
                    # Limit text length
                    if len(text) > 200:
                        text = text[:200] + "..."
                    description_parts.append(f"Text visible: {text}")

            # Faces
            if response.face_annotations:
                num_faces = len(response.face_annotations)
                description_parts.append(f"{num_faces} person{'s' if num_faces > 1 else ''} detected")

            # Landmarks
            if response.landmark_annotations:
                landmarks = [landmark.description for landmark in response.landmark_annotations[:3]]
                description_parts.append(f"Landmarks: {', '.join(landmarks)}")

            # Combine description
            if description_parts:
                description = ". ".join(description_parts)
            else:
                description = "Unable to analyze scene clearly"

            return {
                'success': True,
                'description': description,
                'service': 'google',
                'labels': [l.description for l in response.label_annotations[:10]],
                'objects': [obj.name for obj in response.localized_object_annotations[:10]],
                'text': response.text_annotations[0].description if response.text_annotations else '',
                'num_faces': len(response.face_annotations)
            }

        except Exception as e:
            self.logger.error(f"Google Vision error: {e}")
            return {'success': False, 'error': str(e)}

    def read_text(self, frame: np.ndarray) -> Dict:
        """
        Read text from image using AI OCR

        Args:
            frame: Input frame

        Returns:
            OCR results
        """
        if not self.enabled:
            return {'success': False, 'text': ''}

        try:
            if self.google_client:
                # Google Vision has excellent OCR
                _, buffer = cv2.imencode('.jpg', frame)
                content = buffer.tobytes()
                image = google_vision.Image(content=content)

                response = self.google_client.text_detection(
                    image=image,
                    timeout=self.timeout
                )

                if response.text_annotations:
                    text = response.text_annotations[0].description
                    return {
                        'success': True,
                        'text': text,
                        'service': 'google'
                    }

            elif self.openai_client:
                # Use OpenAI for text reading
                image_base64 = self._encode_image(frame)
                result = self._analyze_openai(
                    image_base64,
                    "Extract and read all visible text in this image. Provide only the text content."
                )
                if result['success']:
                    return {
                        'success': True,
                        'text': result['description'],
                        'service': 'openai'
                    }

            return {'success': False, 'text': ''}

        except Exception as e:
            self.logger.error(f"Error reading text: {e}")
            return {'success': False, 'text': '', 'error': str(e)}

    def detect_objects(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect objects using AI vision

        Args:
            frame: Input frame

        Returns:
            List of detected objects
        """
        if not self.enabled or not self.google_client:
            return []

        try:
            _, buffer = cv2.imencode('.jpg', frame)
            content = buffer.tobytes()
            image = google_vision.Image(content=content)

            response = self.google_client.object_localization(
                image=image,
                timeout=self.timeout
            )

            objects = []
            for obj in response.localized_object_annotations:
                # Convert normalized coordinates to pixel coordinates
                h, w = frame.shape[:2]
                vertices = obj.bounding_poly.normalized_vertices

                x1 = int(vertices[0].x * w)
                y1 = int(vertices[0].y * h)
                x2 = int(vertices[2].x * w)
                y2 = int(vertices[2].y * h)

                objects.append({
                    'label': obj.name,
                    'confidence': obj.score,
                    'bbox': (x1, y1, x2, y2),
                    'center': ((x1 + x2) // 2, (y1 + y2) // 2)
                })

            return objects

        except Exception as e:
            self.logger.error(f"Error detecting objects: {e}")
            return []

    def _encode_image(self, frame: np.ndarray, quality: int = 85) -> str:
        """
        Encode image to base64 for API transmission

        Args:
            frame: Input frame
            quality: JPEG quality (0-100)

        Returns:
            Base64 encoded image string
        """
        # Resize if image is too large (to save bandwidth)
        max_size = 1024
        h, w = frame.shape[:2]
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            frame = cv2.resize(frame, None, fx=scale, fy=scale)

        # Encode to JPEG
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        _, buffer = cv2.imencode('.jpg', frame, encode_params)

        # Convert to base64
        return base64.b64encode(buffer).decode('utf-8')

    def get_announcement_text(self, result: Dict) -> str:
        """
        Format AI vision result for audio announcement

        Args:
            result: Analysis result dictionary

        Returns:
            Text suitable for TTS announcement
        """
        if not result.get('success'):
            return "Unable to analyze scene"

        description = result.get('description', '')

        # Clean up for better TTS
        # Remove excessive technical details
        description = description.replace('(', '').replace(')', '')
        description = description.replace('%', ' percent')

        return description


def test_ai_vision():
    """Test AI vision module"""
    from utils import setup_logging
    import sys

    setup_logging("INFO")
    config = Config()

    # Check if API key is configured
    if not config.get('ai_vision.openai_api_key') and not config.get('ai_vision.google_credentials_path'):
        print("ERROR: No API keys configured!")
        print("\nTo use AI Vision, add to config/settings.yaml:")
        print("\nai_vision:")
        print("  enabled: true")
        print("  primary_service: 'openai'")
        print("  openai_api_key: 'your-api-key-here'")
        print("\nGet API key from: https://platform.openai.com/api-keys")
        sys.exit(1)

    ai_vision = AIVision(config)

    if not ai_vision.initialize():
        print("Failed to initialize AI Vision")
        sys.exit(1)

    print("AI Vision initialized successfully!")
    print(f"Primary service: {ai_vision.primary_service}")
    print("\nCapture an image to test...")

    # Test with camera
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from camera_handler import CameraHandler

    camera = CameraHandler(config)
    if not camera.initialize():
        print("Failed to initialize camera")
        sys.exit(1)

    camera.start_capture()
    time.sleep(1)

    frame = camera.get_current_frame()
    if frame is not None:
        print("\nAnalyzing scene...")
        result = ai_vision.analyze_scene(frame)

        if result['success']:
            print(f"\nService used: {result['service']}")
            print(f"\nDescription:\n{result['description']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")

    camera.release()


if __name__ == "__main__":
    from pathlib import Path
    test_ai_vision()
