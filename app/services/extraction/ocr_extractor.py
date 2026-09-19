import io
import shutil
from typing import Tuple, Dict, Any
from PIL import Image
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.services.preprocessing.image_processor import ImageProcessor


class OCRExtractor:
    """Extracts text from raster images using RapidOCR / Tesseract with image preprocessing."""

    def __init__(self):
        self._rapidocr = None
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._rapidocr = RapidOCR()
        except Exception as e:
            logger.info(f"RapidOCR engine initialization: {e}")

        if settings.TESSERACT_CMD:
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
            except ImportError:
                pass
        self._tesseract_available = self._check_tesseract()

    def _check_tesseract(self) -> bool:
        if settings.TESSERACT_CMD and shutil.which(settings.TESSERACT_CMD):
            return True
        return shutil.which("tesseract") is not None

    def extract_text(self, image_bytes: bytes) -> Tuple[str, float, Dict[str, Any]]:
        """
        Runs live real-time OCR on given image bytes.
        Returns:
            text: Extracted string
            confidence: Estimated OCR confidence (0.0 to 1.0)
            metadata: Details regarding engine, words detected, etc.
        """
        processed_bytes = ImageProcessor.preprocess_for_ocr(image_bytes)

        # 1. Primary engine: RapidOCR (high-accuracy deep learning OCR)
        if self._rapidocr is not None:
            try:
                image = Image.open(io.BytesIO(processed_bytes))
                img_np = np.array(image)
                result, _ = self._rapidocr(img_np)
                if result:
                    lines = [str(item[1]).strip() for item in result if item[1]]
                    confs = [float(item[2]) for item in result if len(item) > 2]
                    avg_conf = (sum(confs) / len(confs)) if confs else 0.85
                    extracted_text = "\n".join(lines).strip()
                    if extracted_text:
                        return (
                            extracted_text,
                            round(min(1.0, max(0.1, avg_conf)), 2),
                            {
                                "engine": "rapidocr",
                                "lines_detected": len(lines),
                                "raw_confidence": avg_conf,
                            }
                        )
            except Exception as e:
                logger.warning(f"RapidOCR extraction failed: {e}. Trying Tesseract fallback.")

        # 2. Secondary engine: Tesseract OCR (if installed)
        if self._tesseract_available:
            try:
                import pytesseract
                image = Image.open(io.BytesIO(processed_bytes))
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confs = [float(c) for c in data.get("conf", []) if str(c) not in ("-1", "")]
                avg_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.5
                text = pytesseract.image_to_string(image).strip()
                return (
                    text,
                    round(avg_conf, 2),
                    {
                        "engine": "tesseract",
                        "word_count": len(confs),
                        "raw_confidence": avg_conf,
                    }
                )
            except Exception as e:
                logger.error(f"Tesseract OCR failed: {e}")

        # 3. Clean empty fallback with genuine diagnostic error (zero mock data)
        return (
            "",
            0.0,
            {
                "engine": "ocr",
                "error": "No recognizable text detected in image",
                "words_detected": 0
            }
        )
