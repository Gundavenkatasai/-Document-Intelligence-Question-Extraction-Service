from __future__ import annotations
import io
from typing import Tuple, Optional
from PIL import Image

try:
    import numpy as np
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from app.core.logging import logger


class ImageProcessor:
    """Provides OpenCV & Pillow-based preprocessing for scanned/imperfect documents."""

    @staticmethod
    def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
        """Converts raw image bytes to OpenCV BGR numpy array."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image from bytes.")
        return img

    @staticmethod
    def to_bytes(cv_image: np.ndarray, format: str = "PNG") -> bytes:
        """Encodes an OpenCV image back to bytes."""
        success, encoded = cv2.imencode(f".{format.lower()}", cv_image)
        if not success:
            raise ValueError(f"Failed to encode image to {format}")
        return encoded.tobytes()

    @classmethod
    def deskew(cls, gray: np.ndarray) -> np.ndarray:
        """Detects skew angle and rotates image to upright position."""
        try:
            # Invert colors so text is white
            thresh = cv2.bitwise_not(gray)
            thresh = cv2.threshold(thresh, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 50:
                return gray

            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            # Ignore tiny skews (< 0.5 degrees) or large 90 degree flips here
            if abs(angle) < 0.5 or abs(angle) > 45:
                return gray

            (h, w) = gray.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                gray, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            return rotated
        except Exception as e:
            logger.warning(f"Deskew failed: {e}. Falling back to unskewed image.")
            return gray

    @classmethod
    def enhance_contrast(cls, gray: np.ndarray) -> np.ndarray:
        """Applies Contrast Limited Adaptive Histogram Equalization (CLAHE)."""
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(gray)
        except Exception:
            return gray

    @classmethod
    def denoise(cls, gray: np.ndarray) -> np.ndarray:
        """Removes salt-and-pepper noise using median blur or bilateral filter."""
        try:
            return cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
        except Exception:
            return gray

    @classmethod
    def adaptive_threshold(cls, gray: np.ndarray) -> np.ndarray:
        """Creates binarized black-and-white image for optimal OCR."""
        try:
            return cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
        except Exception:
            return gray

    @classmethod
    def preprocess_for_ocr(cls, image_bytes: bytes) -> bytes:
        """
        Executes full preprocessing pipeline:
        1. Decode
        2. Grayscale
        3. Deskew
        4. Denoise
        5. Contrast enhancement
        6. Return preprocessed image bytes
        """
        if not HAS_CV2:
            return image_bytes

        try:
            bgr = cls.load_image_from_bytes(image_bytes)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            deskewed = cls.deskew(gray)
            denoised = cls.denoise(deskewed)
            enhanced = cls.enhance_contrast(denoised)
            return cls.to_bytes(enhanced, format="PNG")
        except Exception as e:
            logger.warning(f"Image preprocessing encountered an error: {e}. Using raw original image.")
            return image_bytes
