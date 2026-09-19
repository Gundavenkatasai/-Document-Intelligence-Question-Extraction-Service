import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.user import User
from app.api.deps import get_current_user
from app.services.document_service import DocumentService
from app.schemas.question import QuestionResponse

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.get(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="Get detailed question by ID",
    description="Returns detailed question data including options, matched answer, confidence score, source pages, and provenance warnings."
)
async def get_question(
    question_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    question = await DocumentService.get_question_by_id(
        db=db,
        question_id=question_id,
        user_id=current_user.id
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question {question_id} not found or unauthorized."
        )
    return QuestionResponse.model_validate(question)
