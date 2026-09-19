import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.document_service import DocumentService
from app.services.pipeline import DocumentProcessingPipeline


@pytest.mark.asyncio
async def test_api_system_health_and_ready(client: AsyncClient):
    # Health check
    h_res = await client.get("/health")
    assert h_res.status_code == 200
    assert h_res.json()["status"] == "healthy"

    # Readiness check
    r_res = await client.get("/ready")
    assert r_res.status_code == 200
    assert r_res.json()["database"] is True


@pytest.mark.asyncio
async def test_api_question_and_answer_key_queries(db_session: AsyncSession, client: AsyncClient, auth_headers: dict, test_user):
    # Upload and process a document
    with open("sample_documents/01_digital_exam.pdf", "rb") as f:
        pdf_bytes = f.read()

    doc = await DocumentService.create_document(
        db=db_session,
        user_id=test_user.id,
        filename="01_digital_exam.pdf",
        content=pdf_bytes
    )
    pipeline = DocumentProcessingPipeline(db=db_session)
    await pipeline.run(doc.id)

    # 1. Query questions list
    q_list_res = await client.get(f"/api/v1/documents/{doc.id}/questions", headers=auth_headers)
    assert q_list_res.status_code == 200
    data = q_list_res.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3
    first_q_id = data["items"][0]["id"]

    # 2. Query questions filtered by type
    mcq_res = await client.get(f"/api/v1/documents/{doc.id}/questions?question_type=MULTIPLE_CHOICE", headers=auth_headers)
    assert mcq_res.status_code == 200
    assert all(q["question_type"] == "MULTIPLE_CHOICE" for q in mcq_res.json()["items"])

    # 3. Query individual question by ID
    single_res = await client.get(f"/api/v1/questions/{first_q_id}", headers=auth_headers)
    assert single_res.status_code == 200
    single_data = single_res.json()
    assert single_data["id"] == first_q_id
    assert "options" in single_data
    assert "confidence_score" in single_data
    assert "source_pages" in single_data

    # 4. Query answer key endpoint
    ak_res = await client.get(f"/api/v1/documents/{doc.id}/answer-key", headers=auth_headers)
    assert ak_res.status_code == 200
    ak_data = ak_res.json()
    assert ak_data["document_id"] == str(doc.id)
    assert ak_data["total_questions"] >= 3
    assert "matched_count" in ak_data
    assert len(ak_data["answers"]) >= 3


@pytest.mark.asyncio
async def test_api_isolation_between_different_users(db_session: AsyncSession, client: AsyncClient, test_user):
    from app.db.models.user import User
    from app.core.security import get_password_hash, create_access_token

    # Create a second user
    user2 = User(
        email="second_user@example.com",
        hashed_password=get_password_hash("Secret456!"),
        full_name="Second User",
        is_active=True
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)
    user2_token = create_access_token(user2.id)
    user2_headers = {"Authorization": f"Bearer {user2_token}"}

    # Upload document as user 1
    with open("sample_documents/01_digital_exam.pdf", "rb") as f:
        pdf_bytes = f.read()

    doc = await DocumentService.create_document(
        db=db_session,
        user_id=test_user.id,
        filename="01_digital_exam.pdf",
        content=pdf_bytes
    )

    # User 2 attempts to get status of User 1's document -> 404
    status_res = await client.get(f"/api/v1/documents/{doc.id}/status", headers=user2_headers)
    assert status_res.status_code == 404

    # User 2 attempts to get questions of User 1's document -> empty list or 404
    q_res = await client.get(f"/api/v1/documents/{doc.id}/questions", headers=user2_headers)
    assert q_res.status_code == 200
    assert q_res.json()["total"] == 0
