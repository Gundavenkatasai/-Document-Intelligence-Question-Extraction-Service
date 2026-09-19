import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.group import DocumentGroup
from app.api.deps import get_current_user
from app.schemas.group import (
    GroupCreate,
    GroupResponse,
    GroupDetailResponse,
    GroupDocumentSummary,
)

router = APIRouter(prefix="/groups", tags=["Document Groups"])


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new document group",
    description="Creates a group for associating related documents (e.g., Question Paper + Answer Key)."
)
async def create_group(
    req: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    group = DocumentGroup(
        user_id=current_user.id,
        name=req.name,
        description=req.description
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


@router.get(
    "/{group_id}",
    response_model=GroupDetailResponse,
    summary="Get document group details and member documents",
    description="Retrieves document group information and list of associated documents."
)
async def get_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(DocumentGroup)
        .where(DocumentGroup.id == group_id, DocumentGroup.user_id == current_user.id)
        .options(selectinload(DocumentGroup.documents))
    )
    res = await db.execute(stmt)
    group = res.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document group {group_id} not found or unauthorized."
        )

    doc_summaries = [GroupDocumentSummary.model_validate(d) for d in group.documents]
    return GroupDetailResponse(
        id=group.id,
        user_id=group.user_id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        updated_at=group.updated_at,
        documents=doc_summaries,
    )
