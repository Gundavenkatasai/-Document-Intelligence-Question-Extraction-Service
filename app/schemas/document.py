import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    status: str = "PENDING"
    message: str = "Document accepted for asynchronous processing"


class DocumentStatusResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    total_pages: int
    processed_pages: int
    questions_extracted: int
    warnings: int
    error_message: Optional[str] = None


class DocumentPageResponse(BaseModel):
    id: uuid.UUID
    page_number: int
    extraction_method: str
    character_count: int
    has_visual_content: bool
    page_metadata: Dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    id: uuid.UUID
    group_id: Optional[uuid.UUID]
    filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    status: str
    total_pages: int
    processed_pages: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
