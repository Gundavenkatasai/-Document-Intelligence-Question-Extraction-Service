import uuid
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class AnswerKeyItem(BaseModel):
    question_id: uuid.UUID
    question_number: Optional[str]
    matched_answer: Optional[str]
    reference: Optional[str]
    match_type: Literal["matched", "unmatched", "uncertain", "not_available"]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    source_document_id: Optional[uuid.UUID]
    explanation: Optional[str] = None


class DocumentAnswerKeyResponse(BaseModel):
    document_id: uuid.UUID
    total_questions: int
    matched_count: int
    unmatched_count: int
    uncertain_count: int
    not_available_count: int
    answers: List[AnswerKeyItem] = []
