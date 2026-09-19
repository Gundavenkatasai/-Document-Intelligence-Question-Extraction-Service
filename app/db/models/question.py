import uuid
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.document import Document
    from app.db.models.review import ReviewItem


class ExtractedQuestion(Base, TimestampMixin):
    __tablename__ = "extracted_questions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    
    question_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    # MULTIPLE_CHOICE, TRUE_FALSE, SHORT_ANSWER, DESCRIPTIVE, UNKNOWN
    question_type: Mapped[str] = mapped_column(String(50), default="UNKNOWN", nullable=False)
    
    source_pages: Mapped[List[int]] = mapped_column(JSON, default=list, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    # ACCEPTED, PENDING_REVIEW, REJECTED
    review_status: Mapped[str] = mapped_column(String(50), default="ACCEPTED", nullable=False)
    
    has_visual_content: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    visual_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    raw_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    warnings: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="questions")
    options: Mapped[List["QuestionOption"]] = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan", order_by="QuestionOption.option_key")
    answer: Mapped[Optional["QuestionAnswer"]] = relationship("QuestionAnswer", back_populates="question", uselist=False, cascade="all, delete-orphan")
    reviews: Mapped[List["ReviewItem"]] = relationship("ReviewItem", back_populates="question", cascade="all, delete-orphan")


class QuestionOption(Base, TimestampMixin):
    __tablename__ = "question_options"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("extracted_questions.id", ondelete="CASCADE"), index=True, nullable=False)
    
    option_key: Mapped[str] = mapped_column(String(50), nullable=False)  # "A", "B", "1", "(a)"
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Relationships
    question: Mapped["ExtractedQuestion"] = relationship("ExtractedQuestion", back_populates="options")


class QuestionAnswer(Base, TimestampMixin):
    __tablename__ = "question_answers"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("extracted_questions.id", ondelete="CASCADE"), index=True, nullable=False)
    source_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    
    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer_key_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # matched, unmatched, uncertain, not_available
    match_type: Mapped[str] = mapped_column(String(50), default="not_available", nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    question: Mapped["ExtractedQuestion"] = relationship("ExtractedQuestion", back_populates="answer")
