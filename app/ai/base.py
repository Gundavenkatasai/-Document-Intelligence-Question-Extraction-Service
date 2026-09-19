import abc
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ExtractedOptionSchema(BaseModel):
    key: str
    text: str


class ExtractedQuestionSchema(BaseModel):
    question_number: Optional[str] = None
    question_text: str
    question_type: str  # MULTIPLE_CHOICE, TRUE_FALSE, SHORT_ANSWER, DESCRIPTIVE, UNKNOWN
    options: List[ExtractedOptionSchema] = []
    detected_answer: Optional[str] = None
    answer_reference: Optional[str] = None
    confidence: float = 1.0
    warnings: List[str] = []
    has_visual: bool = False
    source_pages: List[int] = Field(default_factory=list)


class AnswerKeyEntrySchema(BaseModel):
    question_number: str
    answer_text: str
    confidence: float = 1.0
    reference: Optional[str] = None


class DocumentUnderstandingProvider(abc.ABC):
    """Abstract interface for multimodal/document-understanding AI providers."""

    @abc.abstractmethod
    async def extract_questions_from_page(
        self,
        page_text: str,
        page_number: int,
        image_bytes: Optional[bytes] = None
    ) -> List[ExtractedQuestionSchema]:
        """Extracts individual questions and options from page content."""
        pass

    @abc.abstractmethod
    async def parse_answer_key(self, text: str) -> List[AnswerKeyEntrySchema]:
        """Parses answer key tables or lists into structured mappings."""
        pass
