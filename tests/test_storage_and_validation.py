import os
import uuid
import pytest
from app.services.preprocessing.validator import FileValidator, ValidationError
from app.services.storage.local import LocalStorageService


def test_file_validator_valid_inputs():
    # PDF magic signature and structural integrity
    with open("sample_documents/01_digital_exam.pdf", "rb") as f:
        valid_pdf = f.read()
    ft, mime = FileValidator.validate_file("test.pdf", valid_pdf)
    assert ft == "PDF"
    assert mime == "application/pdf"

    # PNG magic signature and structural integrity
    with open("sample_documents/02_scanned_exam.png", "rb") as f:
        valid_png = f.read()
    ft, mime = FileValidator.validate_file("test.png", valid_png)
    assert ft == "IMAGE"
    assert mime == "image/png"


def test_file_validator_invalid_inputs():
    # Empty file
    with pytest.raises(ValidationError) as exc:
        FileValidator.validate_file("empty.pdf", b"")
    assert exc.value.error_code == "EMPTY_FILE"

    # Unsupported extension
    with pytest.raises(ValidationError) as exc:
        FileValidator.validate_file("script.py", b"print('hello')")
    assert exc.value.error_code == "UNSUPPORTED_EXTENSION"

    # Fake extension with mismatched content
    with pytest.raises(ValidationError) as exc:
        FileValidator.validate_file("fake.pdf", b"THIS_IS_NOT_A_PDF_STREAM")
    assert exc.value.error_code in ("INVALID_FILE_SIGNATURE", "MALFORMED_PDF")


@pytest.mark.asyncio
async def test_storage_path_traversal_prevention(tmp_path):
    storage = LocalStorageService(base_path=str(tmp_path))
    user_id = uuid.uuid4()

    # Save normal file
    key = await storage.save_file(b"test content", "../../../evil.pdf", user_id)
    assert not key.startswith("..")
    assert "evil.pdf" in key

    # Direct traversal attempt in key resolution
    with pytest.raises(ValueError):
        storage.get_local_path("../../../outside.txt")
