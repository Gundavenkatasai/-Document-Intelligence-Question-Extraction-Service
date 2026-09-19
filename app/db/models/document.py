import uuid
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, BigInteger, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.group import DocumentGroup
    from app.db.models.question import ExtractedQuestion, QuestionAnswer
    from app.db.models.review import ReviewItem


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("document_groups.id", ondelete="SET NULL"), index=True, nullable=True)
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # PDF, IMAGE
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    # Status: PENDING, PROCESSING, COMPLETED, FAILED
    status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    total_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    doc_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="documents")
    group: Mapped[Optional["DocumentGroup"]] = relationship("DocumentGroup", back_populates="documents")
    pages: Mapped[List["DocumentPage"]] = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan", order_by="DocumentPage.page_number")
    jobs: Mapped[List["ProcessingJob"]] = relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan", order_by="ProcessingJob.created_at.desc()")
    questions: Mapped[List["ExtractedQuestion"]] = relationship("ExtractedQuestion", back_populates="document", cascade="all, delete-orphan")
    reviews: Mapped[List["ReviewItem"]] = relationship("ReviewItem", back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base, TimestampMixin):
    __tablename__ = "document_pages"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-indexed
    
    # Extraction method: native_text, ocr, hybrid
    extraction_method: Mapped[str] = mapped_column(String(50), default="native_text", nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    character_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    page_image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    has_visual_content: Mapped[bool] = mapped_column(default=False, nullable=False)
    page_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="pages")


class ProcessingJob(Base, TimestampMixin):
    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    
    # PENDING, RUNNING, SUCCESS, FAILED, RETRYING
    status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True, nullable=False)
    stage: Mapped[str] = mapped_column(String(100), default="INITIALIZING", nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="jobs")
