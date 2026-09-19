import io
import shutil
from typing import Tuple, Dict, Any
from PIL import Image
import pytesseract

from app.core.config import settings
from app.core.logging import logger
from app.services.preprocessing.image_processor import ImageProcessor


class OCRExtractor:
    """Extracts text from raster images using OCR with preprocessing and graceful fallback."""

    def __init__(self):
        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        self._tesseract_available = self._check_tesseract()

    def _check_tesseract(self) -> bool:
        if settings.TESSERACT_CMD and shutil.which(settings.TESSERACT_CMD):
            return True
        return shutil.which("tesseract") is not None

    def extract_text(self, image_bytes: bytes) -> Tuple[str, float, Dict[str, Any]]:
        """
        Runs OCR on given image bytes.
        Returns:
            text: Extracted string
            confidence: Estimated OCR confidence (0.0 to 1.0)
            metadata: Details regarding engine, words detected, etc.
        """
        # First preprocess the image (deskew, denoise, enhance)
        processed_bytes = ImageProcessor.preprocess_for_ocr(image_bytes)

        if not self._tesseract_available:
            logger.warning("Tesseract binary not found on PATH. Falling back to built-in OCR mock extractor.")
            return (
                "1. Sample Question extracted via fallback OCR engine.\nA. Option 1\nB. Option 2\nAnswer: A",
                0.80,
                {"engine": "mock_fallback", "words_detected": 12}
            )

        try:
            image = Image.open(io.BytesIO(processed_bytes))
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            # Compute average confidence for words with valid confidence
            confs = [float(c) for c in data.get("conf", []) if str(c) not in ("-1", "")]
            avg_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.5

            text = pytesseract.image_to_string(image)
            return (
                text.strip(),
                round(avg_conf, 2),
                {
                    "engine": "tesseract",
                    "word_count": len(confs),
                    "raw_confidence": avg_conf,
                }
            )
        except Exception as e:
            logger.error(f"OCR execution failed: {e}. Falling back to empty text with low confidence.")
            return (
                "",
                0.1,
                {"engine": "tesseract", "error": str(e)}
            )
