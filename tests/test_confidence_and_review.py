import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Document, ReviewItem
from app.services.document_service import DocumentService
from app.services.pipeline import DocumentProcessingPipeline


@pytest.mark.asyncio
async def test_low_confidence_flagged_for_review(db_session: AsyncSession, client: AsyncClient, auth_headers: dict, test_user):
    with open("sample_documents/06_ambiguous_exam.pdf", "rb") as f:
        pdf_bytes = f.read()

    doc = await DocumentService.create_document(
        db=db_session,
        user_id=test_user.id,
        filename="06_ambiguous_exam.pdf",
        content=pdf_bytes
    )

    pipeline = DocumentProcessingPipeline(db=db_session)
    await pipeline.run(doc.id)

    # Check that reviews were created
    stmt = select(ReviewItem).where(ReviewItem.document_id == doc.id)
    reviews = (await db_session.execute(stmt)).scalars().all()
    assert len(reviews) >= 1

    first_rev = reviews[0]
    assert first_rev.status == "PENDING"
    assert first_rev.confidence_score < 0.75

    # Test flagged review queue endpoint via API
    res = await client.get("/api/v1/reviews/flagged", headers=auth_headers)
    assert res.status_code == 200
    queue_data = res.json()
    assert queue_data["total"] >= 1
    assert any(item["id"] == str(first_rev.id) for item in queue_data["items"])

    # Test resolving review item
    resolve_res = await client.post(
        f"/api/v1/reviews/{first_rev.id}/resolve",
        headers=auth_headers,
        json={"status": "RESOLVED", "notes": "Verified by examiner manually."}
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED"
    assert resolve_res.json()["notes"] == "Verified by examiner manually."
