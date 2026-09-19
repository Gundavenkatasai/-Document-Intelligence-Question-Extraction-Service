import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Document, ExtractedQuestion
from app.services.document_service import DocumentService
from app.services.pipeline import DocumentProcessingPipeline


@pytest.mark.asyncio
async def test_multipage_question_merging(db_session: AsyncSession, test_user):
    with open("sample_documents/04_multipage_exam.pdf", "rb") as f:
        pdf_bytes = f.read()

    doc = await DocumentService.create_document(
        db=db_session,
        user_id=test_user.id,
        filename="04_multipage_exam.pdf",
        content=pdf_bytes
    )

    pipeline = DocumentProcessingPipeline(db=db_session)
    await pipeline.run(doc.id)

    stmt = (
        select(Document)
        .where(Document.id == doc.id)
        .options(
            selectinload(Document.questions).selectinload(ExtractedQuestion.options),
            selectinload(Document.questions).selectinload(ExtractedQuestion.answer),
        )
    )
    res = await db_session.execute(stmt)
    completed_doc = res.scalar_one()

    assert completed_doc.status == "COMPLETED"
    assert completed_doc.total_pages == 2

    # Find Question 17
    q17 = next((q for q in completed_doc.questions if q.question_number in ("17", "Q17")), None)
    assert q17 is not None, f"Question 17 should be extracted. Found: {[q.question_number for q in completed_doc.questions]}"

    # Crucial assertion: Question 17 spanned page 1 and page 2
    assert q17.source_pages == [1, 2], f"Expected source_pages [1, 2], got {q17.source_pages}"
    
    # Crucial assertion: Options A, B (from page 1) and C, D (from page 2) are merged
    opt_keys = [opt.option_key.upper() for opt in q17.options]
    assert "A" in opt_keys
    assert "B" in opt_keys
    assert "C" in opt_keys
    assert "D" in opt_keys
    assert len(q17.options) == 4

    # Crucial assertion: Answer C from page 2 is associated
    assert q17.answer is not None
    assert q17.answer.answer_text == "C"

    # Find Question 18 (started and finished on page 2)
    q18 = next((q for q in completed_doc.questions if q.question_number in ("18", "Q18")), None)
    assert q18 is not None
    assert q18.source_pages == [2]
    assert len(q18.options) == 4
    assert q18.answer.answer_text == "B"
