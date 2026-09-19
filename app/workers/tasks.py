import asyncio
import concurrent.futures
import uuid
from typing import Optional
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy.ext.asyncio import AsyncSession

from app.workers.celery_app import celery_app
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.services.pipeline import DocumentProcessingPipeline


async def _execute_pipeline(document_id: uuid.UUID, db: Optional[AsyncSession] = None):
    if db:
        pipeline = DocumentProcessingPipeline(db=db)
        await pipeline.run(document_id)
    else:
        async with AsyncSessionLocal() as session:
            pipeline = DocumentProcessingPipeline(db=session)
            await pipeline.run(document_id)


def _run_coroutine_sync(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_document_task(self, document_id_str: str):
    """
    Celery background worker task for asynchronous document processing.
    """
    logger.info(f"[Worker] Received processing job for document: {document_id_str}", extra={"document_id": document_id_str, "stage": "WORKER_RECEIVED"})
    doc_uuid = uuid.UUID(document_id_str)

    try:
        _run_coroutine_sync(_execute_pipeline(doc_uuid))
        logger.info(f"[Worker] Job completed successfully for document: {document_id_str}")
        return {"status": "SUCCESS", "document_id": document_id_str}

    except Exception as exc:
        logger.error(f"[Worker] Transient failure processing document {document_id_str}: {exc}. Retrying...")
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error(f"[Worker] Max retries exceeded for document: {document_id_str}")
            return {"status": "FAILED", "document_id": document_id_str, "error": str(exc)}
