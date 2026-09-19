import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.document import Document
    from app.db.models.question import ExtractedQuestion


class ReviewItem(Base, TimestampMixin):
    __tablename__ = "review_items"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    question_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("extracted_questions.id", ondelete="CASCADE"), index=True, nullable=True)
    
    # PENDING, RESOLVED, DISMISSED
    status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    warnings: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="reviews")
    question: Mapped[Optional["ExtractedQuestion"]] = relationship("ExtractedQuestion", back_populates="reviews")
