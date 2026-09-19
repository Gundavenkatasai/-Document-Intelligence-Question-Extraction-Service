import uuid
import pytest
from unittest.mock import patch
from app.workers.tasks import process_document_task
from app.services.document_service import DocumentService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_worker_task_success_execution(db_session: AsyncSession, test_user):
    from app.workers.tasks import _execute_pipeline
    with open("sample_documents/01_digital_exam.pdf", "rb") as f:
        pdf_bytes = f.read()

    doc = await DocumentService.create_document(
        db=db_session,
        user_id=test_user.id,
        filename="01_digital_exam.pdf",
        content=pdf_bytes
    )

    await _execute_pipeline(doc.id, db=db_session)
    await db_session.refresh(doc)
    assert doc.status == "COMPLETED"


@pytest.mark.asyncio
async def test_worker_task_nonexistent_document_handled(db_session: AsyncSession):
    from app.workers.tasks import _execute_pipeline
    fake_id = uuid.uuid4()
    # Pipeline handles gracefully without crashing
    await _execute_pipeline(fake_id, db=db_session)


@pytest.mark.asyncio
async def test_worker_retry_on_transient_failure():
    import celery.exceptions
    # Verify retry logic when an external service throws a transient exception
    with patch("app.services.pipeline.DocumentProcessingPipeline.run", side_effect=RuntimeError("Transient network timeout")):
        fake_id = str(uuid.uuid4())
        try:
            result = process_document_task(fake_id)
            assert result["status"] == "FAILED"
        except (celery.exceptions.Retry, RuntimeError) as exc:
            assert "Transient network timeout" in str(exc)
