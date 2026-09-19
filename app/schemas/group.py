import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the document group")
    description: Optional[str] = Field(None, max_length=1000)


class GroupDocumentSummary(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupDetailResponse(GroupResponse):
    documents: List[GroupDocumentSummary] = []
