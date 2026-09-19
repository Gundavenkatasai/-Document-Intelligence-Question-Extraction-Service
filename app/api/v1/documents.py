import uuid
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    BackgroundTasks,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, AsyncSessionLocal
from app.db.models.user import User
from app.api.deps import get_current_user
from app.services.document_service import DocumentService
from app.services.preprocessing.validator import ValidationError
from app.services.pipeline import DocumentProcessingPipeline
from app.workers.tasks import process_document_task
from app.core.config import settings
from app.core.logging import logger
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentStatusResponse,
)
from app.schemas.question import (
    QuestionListResponse,
    QuestionResponse,
)
from app.schemas.answer import DocumentAnswerKeyResponse

router = APIRouter(prefix="/documents", tags=["Documents"])


def _is_redis_online() -> bool:
    """Fast non-blocking probe to verify Redis is listening before dispatching to Celery."""
    try:
        import socket
        from urllib.parse import urlparse
        parsed = urlparse(settings.REDIS_URL)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.05)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


async def _run_pipeline_inline(document_id: uuid.UUID):
    """Fallback inline background processor if Celery/Redis is not active."""
    async with AsyncSessionLocal() as session:
        pipeline = DocumentProcessingPipeline(db=session)
        await pipeline.run(document_id)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload examination document or image",
    description="Accepts PDF, PNG, JPG, or JPEG file for asynchronous document intelligence processing. Returns 202 Accepted immediately."
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF or image file (max 50MB)"),
    group_id: Optional[uuid.UUID] = Form(None, description="Optional document group UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Read file content into memory
    content = await file.read()

    try:
        doc = await DocumentService.create_document(
            db=db,
            user_id=current_user.id,
            filename=file.filename or "upload.bin",
            content=content,
            group_id=group_id
        )
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ve.message)

    # Dispatch to Celery or background task
    if settings.CELERY_TASK_ALWAYS_EAGER:
        try:
            process_document_task.delay(str(doc.id))
        except Exception:
            pass
    elif _is_redis_online():
        try:
            process_document_task.apply_async(args=[str(doc.id)], retry=False)
            logger.info(f"Dispatched document {doc.id} to Celery worker.")
        except Exception as e:
            logger.info(f"Celery dispatch failed ({e}). Running via asynchronous background task.")
            background_tasks.add_task(_run_pipeline_inline, doc.id)
    else:
        logger.info(f"Redis offline. Running document {doc.id} via asynchronous background task.")
        background_tasks.add_task(_run_pipeline_inline, doc.id)

    return DocumentUploadResponse(
        document_id=doc.id,
        status="PENDING",
        message="Document accepted for asynchronous processing"
    )


@router.post(
    "/upload-sample",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload sample document for demonstration",
    description="Loads a bundled sample document from sample_documents/ and submits it for processing."
)
async def upload_sample_document(
    background_tasks: BackgroundTasks,
    sample_name: str = Query(..., description="Filename in sample_documents/ (e.g. 01_digital_exam.pdf)"),
    group_id: Optional[uuid.UUID] = Query(None, description="Optional document group UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    import os
    safe_name = os.path.basename(sample_name)
    sample_path = os.path.join("sample_documents", safe_name)
    if not os.path.isfile(sample_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sample document '{safe_name}' not found.")
    
    with open(sample_path, "rb") as f:
        content = f.read()

    try:
        doc = await DocumentService.create_document(
            db=db,
            user_id=current_user.id,
            filename=safe_name,
            content=content,
            group_id=group_id
        )
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ve.message)

    if settings.CELERY_TASK_ALWAYS_EAGER:
        try:
            process_document_task.delay(str(doc.id))
        except Exception:
            pass
    elif _is_redis_online():
        try:
            process_document_task.apply_async(args=[str(doc.id)], retry=False)
        except Exception as e:
            logger.info(f"Celery queue unavailable ({e}). Running via asynchronous background task.")
            background_tasks.add_task(_run_pipeline_inline, doc.id)
    else:
        logger.info(f"Redis offline. Running sample {safe_name} via asynchronous background task.")
        background_tasks.add_task(_run_pipeline_inline, doc.id)

    return DocumentUploadResponse(
        document_id=doc.id,
        status="PENDING",
        message=f"Sample document '{safe_name}' accepted for asynchronous processing"
    )


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Get document processing status and progress",
    description="Retrieves the real-time processing progress, page statistics, and question counts for a document."
)
async def get_document_status(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    status_data = await DocumentService.get_document_status(
        db=db,
        document_id=document_id,
        user_id=current_user.id
    )
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found or unauthorized."
        )
    return status_data


@router.get(
    "/{document_id}/questions",
    response_model=QuestionListResponse,
    summary="List extracted questions for document",
    description="Retrieves structured question results with pagination and filtering by question type and review status."
)
async def get_document_questions(
    document_id: uuid.UUID,
    question_type: Optional[str] = Query(None, description="Filter by type (MULTIPLE_CHOICE, TRUE_FALSE, SHORT_ANSWER, DESCRIPTIVE, UNKNOWN)"),
    review_status: Optional[str] = Query(None, description="Filter by status (ACCEPTED, PENDING_REVIEW, REJECTED)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    items, total = await DocumentService.get_questions_for_document(
        db=db,
        document_id=document_id,
        user_id=current_user.id,
        question_type=question_type,
        review_status=review_status,
        page=page,
        page_size=page_size
    )
    return QuestionListResponse(
        items=[QuestionResponse.model_validate(q) for q in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{document_id}/answer-key",
    response_model=DocumentAnswerKeyResponse,
    summary="Get matched answer keys and provenance",
    description="Returns the answer matching report distinguishing matched, unmatched, uncertain, and not_available answers."
)
async def get_document_answer_key(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    answer_data = await DocumentService.get_document_answer_key(
        db=db,
        document_id=document_id,
        user_id=current_user.id
    )
    if not answer_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found or unauthorized."
        )
    return answer_data
