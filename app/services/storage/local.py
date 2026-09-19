import os
import re
import uuid
import aiofiles
from pathlib import Path

from app.core.config import settings
from app.services.storage.base import BaseStorageService


class LocalStorageService(BaseStorageService):
    """Local filesystem-backed storage implementation."""

    def __init__(self, base_path: str = settings.STORAGE_PATH):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        # Strip path components and keep only safe alphanumeric/dashes/dots
        clean_name = os.path.basename(filename)
        clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", clean_name)
        return clean_name or "file.bin"

    def _resolve_key(self, storage_key: str) -> Path:
        # Prevent directory traversal attacks
        clean_key = Path(storage_key).as_posix().lstrip("/")
        full_path = (self.base_path / clean_key).resolve()
        if not str(full_path).startswith(str(self.base_path)):
            raise ValueError(f"Directory traversal attack detected in storage_key: {storage_key}")
        return full_path

    async def save_file(self, content: bytes, original_filename: str, user_id: uuid.UUID) -> str:
        sanitized = self._sanitize_filename(original_filename)
        unique_id = uuid.uuid4().hex
        relative_key = f"{user_id}/{unique_id}_{sanitized}"
        target_path = self.base_path / relative_key

        target_path.parent.mkdir(parents=True, exist_ok=True)
        # Write bytes asynchronously
        with open(target_path, "wb") as f:
            f.write(content)

        return relative_key

    async def get_file(self, storage_key: str) -> bytes:
        file_path = self._resolve_key(storage_key)
        if not file_path.exists():
            raise FileNotFoundError(f"Storage object not found: {storage_key}")
        with open(file_path, "rb") as f:
            return f.read()

    async def delete_file(self, storage_key: str) -> bool:
        file_path = self._resolve_key(storage_key)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def get_local_path(self, storage_key: str) -> str:
        file_path = self._resolve_key(storage_key)
        return str(file_path)
