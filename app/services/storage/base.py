import abc
import uuid
from typing import Optional


class BaseStorageService(abc.ABC):
    """Abstract interface for document object storage."""

    @abc.abstractmethod
    async def save_file(self, content: bytes, original_filename: str, user_id: uuid.UUID) -> str:
        """Saves file securely and returns a safe storage identifier/key."""
        pass

    @abc.abstractmethod
    async def get_file(self, storage_key: str) -> bytes:
        """Retrieves file content given the storage key."""
        pass

    @abc.abstractmethod
    async def delete_file(self, storage_key: str) -> bool:
        """Deletes file given the storage key."""
        pass

    @abc.abstractmethod
    def get_local_path(self, storage_key: str) -> str:
        """Returns local filesystem path for internal processing libraries (fitz, opencv)."""
        pass
