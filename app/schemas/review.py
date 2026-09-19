import uuid
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


class ReviewItemResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    question_id: Optional[uuid.UUID]
    status: str
    reason: str
    confidence_score: float
    warnings: List[str] = []
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewListResponse(BaseModel):
    items: List[ReviewItemResponse]
    total: int
    page: int
    page_size: int


class ReviewResolveRequest(BaseModel):
    status: Literal["RESOLVED", "DISMISSED"]
    notes: Optional[str] = Field(None, max_length=1000)
