from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Document Intelligence & Question Extraction Service"
    API_V1_STR: str = "api/v1"
    SECRET_KEY: str = "super-secret-production-key-change-in-env-minimum-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/doc_intelligence"
    DB_ECHO: bool = False

    # Task Queue / Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_PATH: str = "./data/storage"
    S3_BUCKET: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None

    # Processing Limits & Policies
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_MIME_TYPES: list[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/jpg",
    ]
    CONFIDENCE_REVIEW_THRESHOLD: float = 0.75
    MIN_CHARS_FOR_NATIVE_TEXT: int = 40  # If page has fewer chars, trigger OCR fallback

    # Document Understanding AI Provider
    AI_PROVIDER: Literal["rule_based", "gemini", "openai", "mock"] = "rule_based"
    AI_API_KEY: Optional[str] = None
    AI_MODEL: str = "gemini-1.5-flash"

    # OCR Config
    TESSERACT_CMD: Optional[str] = None

    # Background execution mode for local tests
    CELERY_TASK_ALWAYS_EAGER: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
