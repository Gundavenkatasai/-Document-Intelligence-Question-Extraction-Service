import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Document, DocumentGroup, ExtractedQuestion
from app.services.document_service import DocumentService
from app.services.pipeline import DocumentProcessingPipeline


@pytest.mark.asyncio
async def test_cross_document_group_answer_matching(db_session: AsyncSession, test_user):
    # 1. Create a Document Group
    group = DocumentGroup(
        user_id=test_user.id,
        name="General Knowledge Exam Group",
        description="Question paper and separate answer key"
    )
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)

    # 2. Upload and process Answer Key document
    with open("sample_documents/05_answer_key.pdf", "rb") as f:
        key_bytes = f.read()

    key_doc = await DocumentService.create_document(
        db=db_session,
        user_id=test_user.id,
        filename="05_answer_key.pdf",
        content=key_bytes,
        group_id=group.id
    )
    pipeline = DocumentProcessingPipeline(db=db_session)
    await pipeline.run(key_doc.id)

    # 3. Upload and process Question Paper document
    with open("sample_documents/05_question_paper.pdf", "rb") as f:
        paper_bytes = f.read()

    paper_doc = await DocumentService.create_document(
        db=db_session,
        user_id=test_user.id,
        filename="05_question_paper.pdf",
        content=paper_bytes,
        group_id=group.id
    )
    await pipeline.run(paper_doc.id)

    # 4. Inspect Questions in Question Paper
    stmt = (
        select(Document)
        .where(Document.id == paper_doc.id)
        .options(
            selectinload(Document.questions).selectinload(ExtractedQuestion.answer)
        )
    )
    res = await db_session.execute(stmt)
    completed_paper = res.scalar_one()

    assert completed_paper.status == "COMPLETED"
    assert len(completed_paper.questions) == 3

    q1 = next((q for q in completed_paper.questions if q.question_number in ("1", "Q1")), None)
    assert q1 is not None
    assert q1.answer is not None
    assert q1.answer.answer_text == "C"
    assert q1.answer.match_type == "matched"
    assert q1.answer.source_document_id == key_doc.id  # Preserved cross-doc provenance!

    q2 = next((q for q in completed_paper.questions if q.question_number in ("2", "Q2")), None)
    assert q2 is not None
    assert q2.answer is not None
    assert q2.answer.answer_text == "B"
    assert q2.answer.match_type == "matched"

    q3 = next((q for q in completed_paper.questions if q.question_number in ("3", "Q3")), None)
    assert q3 is not None
    assert q3.answer is not None
    assert q3.answer.answer_text == "B"
    assert q3.answer.match_type == "matched"


@pytest.mark.asyncio
async def test_uncertain_answer_option_mismatch():
    from app.services.answer_keys.matcher import AnswerKeyMatcher
    from app.ai.base import ExtractedQuestionSchema, ExtractedOptionSchema, AnswerKeyEntrySchema

    # Question has options A, B, C, D
    q = ExtractedQuestionSchema(
        question_number="1",
        question_text="Sample question",
        question_type="MULTIPLE_CHOICE",
        options=[
            ExtractedOptionSchema(key="A", text="Option A"),
            ExtractedOptionSchema(key="B", text="Option B")
        ]
    )
    # Answer key specifies "Z" which doesn't exist
    key_entry = AnswerKeyEntrySchema(question_number="1", answer_text="Z")

    results = AnswerKeyMatcher.match_answers([q], [key_entry])
    assert len(results) == 1
    match = results[0]
    assert match.match_type == "uncertain"
    assert match.answer_text is None  # Never hallucinate invalid answer
    assert match.confidence_score < 0.50
