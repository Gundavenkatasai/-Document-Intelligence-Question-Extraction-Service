from app.core.config import settings
from app.services.storage.base import BaseStorageService
from app.services.storage.local import LocalStorageService


def get_storage_service() -> BaseStorageService:
    """Storage service provider factory."""
    if settings.STORAGE_BACKEND == "local":
        return LocalStorageService(settings.STORAGE_PATH)
    elif settings.STORAGE_BACKEND == "s3":
        # S3 storage service fallback to local if not configured, or S3 implementation
        return LocalStorageService(settings.STORAGE_PATH)
    return LocalStorageService(settings.STORAGE_PATH)


__all__ = ["BaseStorageService", "LocalStorageService", "get_storage_service"]
