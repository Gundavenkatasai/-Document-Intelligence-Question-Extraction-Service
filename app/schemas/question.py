import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class OptionResponse(BaseModel):
    id: uuid.UUID
    option_key: str
    option_text: str
    is_correct: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class AnswerResponse(BaseModel):
    id: uuid.UUID
    source_document_id: Optional[uuid.UUID] = None
    answer_text: Optional[str] = None
    answer_key_reference: Optional[str] = None
    match_type: Literal["matched", "unmatched", "uncertain", "not_available"] = "not_available"
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    explanation: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class QuestionResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    question_number: Optional[str] = None
    question_text: str
    question_type: str  # MULTIPLE_CHOICE, TRUE_FALSE, SHORT_ANSWER, DESCRIPTIVE, UNKNOWN
    options: List[OptionResponse] = []
    answer: Optional[AnswerResponse] = None
    source_pages: List[int] = []
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    review_status: str  # ACCEPTED, PENDING_REVIEW, REJECTED
    has_visual_content: bool = False
    visual_metadata: Dict[str, Any] = {}
    raw_metadata: Dict[str, Any] = {}
    warnings: List[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionListResponse(BaseModel):
    items: List[QuestionResponse]
    total: int
    page: int
    page_size: int
