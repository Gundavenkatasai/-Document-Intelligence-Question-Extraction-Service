from typing import Tuple
from app.services.preprocessing.pdf_processor import PDFProcessor


class NativeExtractor:
    """Extracts digitally embedded text from PDF pages."""

    @staticmethod
    def extract_text(pdf_bytes: bytes, page_number: int) -> Tuple[str, int]:
        """
        Extracts native text and character count.
        """
        return PDFProcessor.extract_page_native_text(pdf_bytes, page_number)
