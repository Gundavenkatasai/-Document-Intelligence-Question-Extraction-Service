import uuid
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Document,
    DocumentGroup,
    ExtractedQuestion,
    QuestionOption,
    QuestionAnswer,
    ReviewItem,
    ProcessingJob,
)
from app.services.storage import get_storage_service
from app.services.preprocessing.validator import FileValidator, ValidationError


class DocumentService:
    """Business logic for document management and queries."""

    @staticmethod
    async def create_document(
        db: AsyncSession,
        user_id: uuid.UUID,
        filename: str,
        content: bytes,
        group_id: Optional[uuid.UUID] = None
    ) -> Document:
        # 1. File validation
        file_type, mime_type = FileValidator.validate_file(filename, content)

        # 2. Check group if specified
        if group_id:
            group_stmt = select(DocumentGroup).where(
                DocumentGroup.id == group_id,
                DocumentGroup.user_id == user_id
            )
            res = await db.execute(group_stmt)
            if not res.scalar_one_or_none():
                raise ValidationError("Specified document group does not exist or unauthorized.", error_code="INVALID_GROUP")

        # 3. Save to storage
        storage = get_storage_service()
        storage_path = await storage.save_file(content, filename, user_id)

        # 4. Create document record
        doc = Document(
            user_id=user_id,
            group_id=group_id,
            filename=filename,
            storage_path=storage_path,
            file_type=file_type,
            mime_type=mime_type,
            file_size_bytes=len(content),
            status="PENDING",
            total_pages=0,
            processed_pages=0,
            doc_metadata={"original_filename": filename}
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def get_document(db: AsyncSession, document_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Document]:
        stmt = select(Document).where(Document.id == document_id, Document.user_id == user_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_document_status(db: AsyncSession, document_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        stmt = (
            select(Document)
            .where(Document.id == document_id, Document.user_id == user_id)
            .options(selectinload(Document.jobs), selectinload(Document.questions))
        )
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            return None

        latest_job = doc.jobs[0] if doc.jobs else None
        progress = latest_job.progress_percent if latest_job else (100 if doc.status == "COMPLETED" else 0)
        
        # Calculate total warnings across questions
        warnings_count = sum(len(q.warnings) for q in doc.questions)

        return {
            "document_id": doc.id,
            "status": doc.status,
            "progress": progress,
            "total_pages": doc.total_pages,
            "processed_pages": doc.processed_pages,
            "questions_extracted": len(doc.questions),
            "warnings": warnings_count,
            "error_message": doc.error_message,
        }

    @staticmethod
    async def get_questions_for_document(
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        question_type: Optional[str] = None,
        review_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ExtractedQuestion], int]:
        # Check document ownership
        doc_stmt = select(Document.id).where(Document.id == document_id, Document.user_id == user_id)
        doc_res = await db.execute(doc_stmt)
        if not doc_res.scalar_one_or_none():
            return [], 0

        filters = [ExtractedQuestion.document_id == document_id]
        if question_type:
            filters.append(ExtractedQuestion.question_type == question_type.upper())
        if review_status:
            filters.append(ExtractedQuestion.review_status == review_status.upper())

        # Count total
        count_stmt = select(func.count()).select_from(ExtractedQuestion).where(and_(*filters))
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        # Query items
        offset = (page - 1) * page_size
        items_stmt = (
            select(ExtractedQuestion)
            .where(and_(*filters))
            .options(
                selectinload(ExtractedQuestion.options),
                selectinload(ExtractedQuestion.answer),
            )
            .order_by(ExtractedQuestion.created_at)
            .offset(offset)
            .limit(page_size)
        )
        items_res = await db.execute(items_stmt)
        return list(items_res.scalars().all()), total

    @staticmethod
    async def get_question_by_id(
        db: AsyncSession,
        question_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[ExtractedQuestion]:
        stmt = (
            select(ExtractedQuestion)
            .join(Document, ExtractedQuestion.document_id == Document.id)
            .where(ExtractedQuestion.id == question_id, Document.user_id == user_id)
            .options(
                selectinload(ExtractedQuestion.options),
                selectinload(ExtractedQuestion.answer),
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_document_answer_key(
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        # Verify document access
        doc_stmt = select(Document).where(Document.id == document_id, Document.user_id == user_id)
        doc_res = await db.execute(doc_stmt)
        doc = doc_res.scalar_one_or_none()
        if not doc:
            return None

        # Fetch questions and answers
        q_stmt = (
            select(ExtractedQuestion)
            .where(ExtractedQuestion.document_id == document_id)
            .options(selectinload(ExtractedQuestion.answer))
            .order_by(ExtractedQuestion.created_at)
        )
        q_res = await db.execute(q_stmt)
        questions = q_res.scalars().all()

        answers_list: List[Dict[str, Any]] = []
        counts = {"matched": 0, "unmatched": 0, "uncertain": 0, "not_available": 0}

        for q in questions:
            ans = q.answer
            m_type = ans.match_type if ans else "not_available"
            counts[m_type] = counts.get(m_type, 0) + 1

            answers_list.append({
                "question_id": q.id,
                "question_number": q.question_number,
                "matched_answer": ans.answer_text if ans else None,
                "reference": ans.answer_key_reference if ans else None,
                "match_type": m_type,
                "confidence_score": ans.confidence_score if ans else 0.0,
                "source_document_id": ans.source_document_id if ans else None,
                "explanation": ans.explanation if ans else "No answer association found."
            })

        return {
            "document_id": doc.id,
            "total_questions": len(questions),
            "matched_count": counts["matched"],
            "unmatched_count": counts["unmatched"],
            "uncertain_count": counts["uncertain"],
            "not_available_count": counts["not_available"],
            "answers": answers_list,
        }

    @staticmethod
    async def get_flagged_reviews(
        db: AsyncSession,
        user_id: uuid.UUID,
        document_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        confidence_max: Optional[float] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ReviewItem], int]:
        filters = [Document.user_id == user_id]
        if document_id:
            filters.append(ReviewItem.document_id == document_id)
        if status:
            filters.append(ReviewItem.status == status.upper())
        if confidence_max is not None:
            filters.append(ReviewItem.confidence_score <= confidence_max)

        # Count total
        count_stmt = (
            select(func.count())
            .select_from(ReviewItem)
            .join(Document, ReviewItem.document_id == Document.id)
            .where(and_(*filters))
        )
        total = (await db.execute(count_stmt)).scalar_one()

        # Query items
        offset = (page - 1) * page_size
        items_stmt = (
            select(ReviewItem)
            .join(Document, ReviewItem.document_id == Document.id)
            .where(and_(*filters))
            .order_by(ReviewItem.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = (await db.execute(items_stmt)).scalars().all()
        return list(items), total

    @staticmethod
    async def resolve_review_item(
        db: AsyncSession,
        review_id: uuid.UUID,
        user_id: uuid.UUID,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[ReviewItem]:
        stmt = (
            select(ReviewItem)
            .join(Document, ReviewItem.document_id == Document.id)
            .where(ReviewItem.id == review_id, Document.user_id == user_id)
            .options(selectinload(ReviewItem.question))
        )
        res = await db.execute(stmt)
        item = res.scalar_one_or_none()
        if not item:
            return None

        item.status = status
        if notes:
            item.notes = notes
        if item.question and status == "RESOLVED":
            item.question.review_status = "ACCEPTED"

        await db.commit()
        await db.refresh(item)
        return item
