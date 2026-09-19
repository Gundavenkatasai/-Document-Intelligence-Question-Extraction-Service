import io
from typing import Tuple
import filetype
from PIL import Image
import fitz  # PyMuPDF

from app.core.config import settings


class ValidationError(Exception):
    """Custom exception raised when file validation fails."""
    def __init__(self, message: str, error_code: str = "INVALID_FILE"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class FileValidator:
    """Validates uploaded files for size, extension, MIME type, magic bytes, and structural integrity."""

    MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

    MAGIC_SIGNATURES = {
        "pdf": b"%PDF-",
        "jpeg": b"\xff\xd8\xff",
        "png": b"\x89PNG\r\n\x1a\n",
    }

    @classmethod
    def validate_file(cls, filename: str, content: bytes) -> Tuple[str, str]:
        """
        Validates content and filename.
        Returns (file_type, detected_mime_type) e.g. ("PDF", "application/pdf")
        Raises ValidationError on failure.
        """
        if not content or len(content) == 0:
            raise ValidationError("Uploaded file is empty (0 bytes).", error_code="EMPTY_FILE")

        if len(content) > cls.MAX_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_MB
            raise ValidationError(
                f"File size exceeds maximum allowed limit of {max_mb}MB.",
                error_code="FILE_TOO_LARGE"
            )

        # 1. Extension check
        ext = ""
        if "." in filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(cls.ALLOWED_EXTENSIONS))}",
                error_code="UNSUPPORTED_EXTENSION"
            )

        # 2. Magic byte / Signature check
        detected_kind = None
        if content.startswith(cls.MAGIC_SIGNATURES["pdf"]):
            detected_kind = "pdf"
        elif content.startswith(cls.MAGIC_SIGNATURES["jpeg"]):
            detected_kind = "jpeg"
        elif content.startswith(cls.MAGIC_SIGNATURES["png"]):
            detected_kind = "png"
        else:
            # Fallback to filetype library inspection
            kind = filetype.guess(content[:4096])
            if kind is not None and kind.extension in ("pdf", "jpg", "jpeg", "png"):
                detected_kind = "jpeg" if kind.extension == "jpg" else kind.extension

        if not detected_kind:
            raise ValidationError(
                "File content does not match allowed magic signatures for PDF, JPG, or PNG.",
                error_code="INVALID_FILE_SIGNATURE"
            )

        # 3. Structural validation (Ensure not corrupted or malformed)
        if detected_kind == "pdf":
            try:
                # Open PDF with PyMuPDF
                doc = fitz.open(stream=content, filetype="pdf")
                if doc.page_count <= 0:
                    raise ValidationError("PDF has 0 pages or is malformed.", error_code="MALFORMED_PDF")
                doc.close()
            except Exception as e:
                raise ValidationError(f"Malformed or unreadable PDF document: {str(e)}", error_code="MALFORMED_PDF")
            return "PDF", "application/pdf"

        elif detected_kind in ("jpeg", "png"):
            try:
                # Open Image with Pillow to verify integrity
                img = Image.open(io.BytesIO(content))
                img.verify()
            except Exception as e:
                raise ValidationError(f"Corrupted or malformed image: {str(e)}", error_code="CORRUPTED_IMAGE")
            
            mime = "image/png" if detected_kind == "png" else "image/jpeg"
            return "IMAGE", mime

        raise ValidationError("Unsupported file format.", error_code="UNSUPPORTED_FORMAT")
