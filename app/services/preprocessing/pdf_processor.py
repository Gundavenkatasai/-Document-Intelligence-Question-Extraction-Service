import io
from typing import List, Dict, Any, Tuple
import fitz  # PyMuPDF

from app.core.logging import logger


class PDFProcessor:
    """Handles PDF rendering, native text inspection, and visual element detection."""

    @staticmethod
    def get_page_count(pdf_bytes: bytes) -> int:
        """Returns the number of pages in the PDF document."""
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            return doc.page_count

    @staticmethod
    def extract_page_native_text(pdf_bytes: bytes, page_number: int) -> Tuple[str, int]:
        """
        Extracts native text from a specific page (1-indexed).
        Returns (text, character_count).
        """
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            idx = page_number - 1
            if idx < 0 or idx >= doc.page_count:
                raise IndexError(f"Page number {page_number} out of range (1..{doc.page_count})")
            page = doc.load_page(idx)
            text = page.get_text("text") or ""
            return text.strip(), len(text.strip())

    @staticmethod
    def render_page_to_image(pdf_bytes: bytes, page_number: int, dpi: int = 150) -> bytes:
        """
        Renders a PDF page to PNG image bytes.
        """
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            idx = page_number - 1
            page = doc.load_page(idx)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            return pix.tobytes("png")

    @staticmethod
    def detect_page_visual_elements(pdf_bytes: bytes, page_number: int) -> Dict[str, Any]:
        """
        Detects embedded images, drawings, and potential tables on the page.
        """
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            idx = page_number - 1
            page = doc.load_page(idx)
            images = page.get_images(full=True)
            drawings = page.get_drawings()
            
            # Check for table-like patterns (lines/rectangles grid)
            rects = [d for d in drawings if d.get("type") in ("s", "f", "fs") and len(d.get("items", [])) > 2]
            potential_tables = len(rects) > 4

            has_visuals = len(images) > 0 or len(drawings) > 5 or potential_tables

            return {
                "has_visual_content": has_visuals,
                "embedded_image_count": len(images),
                "drawing_count": len(drawings),
                "potential_table_detected": potential_tables,
            }
