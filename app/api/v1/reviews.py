import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.user import User
from app.api.deps import get_current_user
from app.services.document_service import DocumentService
from app.schemas.review import (
    ReviewListResponse,
    ReviewItemResponse,
    ReviewResolveRequest,
)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get(
    "/flagged",
    response_model=ReviewListResponse,
    summary="Get flagged review items queue",
    description="Retrieves flagged items for human verification, with filtering by document, confidence score, and status."
)
async def get_flagged_reviews(
    document_id: Optional[uuid.UUID] = Query(None, description="Filter by document UUID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by review status (PENDING, RESOLVED, DISMISSED)"),
    confidence_max: Optional[float] = Query(None, description="Filter by max confidence score (e.g. 0.75)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    items, total = await DocumentService.get_flagged_reviews(
        db=db,
        user_id=current_user.id,
        document_id=document_id,
        status=status_filter,
        confidence_max=confidence_max,
        page=page,
        page_size=page_size
    )
    return ReviewListResponse(
        items=[ReviewItemResponse.model_validate(it) for it in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post(
    "/{review_id}/resolve",
    response_model=ReviewItemResponse,
    summary="Resolve or dismiss a review item",
    description="Updates the status of a review item to RESOLVED or DISMISSED."
)
async def resolve_review_item(
    review_id: uuid.UUID,
    req: ReviewResolveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    item = await DocumentService.resolve_review_item(
        db=db,
        review_id=review_id,
        user_id=current_user.id,
        status=req.status,
        notes=req.notes
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item {review_id} not found or unauthorized."
        )
    return ReviewItemResponse.model_validate(item)


@router.patch(
    "/{review_id}/status",
    response_model=ReviewItemResponse,
    summary="Update review item status via query params",
    description="Updates review item status (RESOLVED, DISMISSED) with optional notes."
)
async def update_review_status(
    review_id: uuid.UUID,
    status: str = Query(..., description="RESOLVED or DISMISSED"),
    resolution_notes: Optional[str] = Query(None, description="Resolution notes"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    item = await DocumentService.resolve_review_item(
        db=db,
        review_id=review_id,
        user_id=current_user.id,
        status=status,
        notes=resolution_notes
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item {review_id} not found or unauthorized."
        )
    return ReviewItemResponse.model_validate(item)
