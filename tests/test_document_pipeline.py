import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Document, ExtractedQuestion, DocumentPage
from app.services.document_service import DocumentService
from app.services.pipeline import DocumentProcessingPipeline


@pytest.mark.asyncio
async def test_digital_pdf_pipeline_execution(db_session: AsyncSession, test_user):
    with open("sample_documents/01_digital_exam.pdf", "rb") as f:
        pdf_bytes = f.read()

    # 1. Create document
    doc = await DocumentService.create_document(
        db=db_session,
        user_id=test_user.id,
        filename="01_digital_exam.pdf",
        content=pdf_bytes
    )
    assert doc.status == "PENDING"

    # 2. Run Pipeline
    pipeline = DocumentProcessingPipeline(db=db_session)
    await pipeline.run(doc.id)

    # 3. Reload document with questions and pages
    stmt = (
        select(Document)
        .where(Document.id == doc.id)
        .options(
            selectinload(Document.pages),
            selectinload(Document.questions).selectinload(ExtractedQuestion.options),
            selectinload(Document.questions).selectinload(ExtractedQuestion.answer),
        )
    )
    res = await db_session.execute(stmt)
    completed_doc = res.scalar_one()

    assert completed_doc.status == "COMPLETED"
    assert completed_doc.total_pages == 1
    assert completed_doc.processed_pages == 1

    # Check pages
    assert len(completed_doc.pages) == 1
    assert completed_doc.pages[0].extraction_method == "native_text"
    assert completed_doc.pages[0].character_count > 50

    # Check extracted questions
    assert len(completed_doc.questions) >= 3

    # Check Question 1
    q1 = next((q for q in completed_doc.questions if q.question_number in ("1", "Q1")), None)
    assert q1 is not None
    assert "mitochondria" in q1.question_text.lower()
    assert q1.question_type == "MULTIPLE_CHOICE"
    assert len(q1.options) == 4
    assert q1.source_pages == [1]
    assert q1.answer is not None
    assert q1.answer.answer_text == "B"
    assert q1.confidence_score >= 0.85

    # Check Question 3 (True/False)
    q3 = next((q for q in completed_doc.questions if q.question_number in ("3", "Q3")), None)
    assert q3 is not None
    assert q3.question_type == "TRUE_FALSE"


@pytest.mark.asyncio
async def test_scanned_image_pipeline_execution(db_session: AsyncSession, test_user):
    with open("sample_documents/02_scanned_exam.png", "rb") as f:
        img_bytes = f.read()

    doc = await DocumentService.create_document(
        db=db_session,
        user_id=test_user.id,
        filename="02_scanned_exam.png",
        content=img_bytes
    )

    pipeline = DocumentProcessingPipeline(db=db_session)
    await pipeline.run(doc.id)

    stmt = (
        select(Document)
        .where(Document.id == doc.id)
        .options(
            selectinload(Document.pages),
            selectinload(Document.questions),
        )
    )
    res = await db_session.execute(stmt)
    completed_doc = res.scalar_one()

    assert completed_doc.status == "COMPLETED"
    assert completed_doc.pages[0].extraction_method == "ocr"
    assert len(completed_doc.questions) >= 1
