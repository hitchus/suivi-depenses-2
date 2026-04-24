import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.space import (
    InviteRequest,
    MemberRoleUpdate,
    SpaceCreate,
    SpaceMemberResponse,
    SpaceResponse,
)
from app.services import space_service

router = APIRouter(prefix="/spaces", tags=["spaces"])


@router.get("", response_model=list[SpaceResponse])
async def list_spaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await space_service.get_user_spaces(db, current_user.id)


@router.post("", response_model=SpaceResponse, status_code=201)
async def create_space(
    body: SpaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await space_service.create_space(db, current_user.id, body)


@router.post("/{space_id}/invite", response_model=SpaceMemberResponse, status_code=201)
async def invite_member(
    space_id: uuid.UUID,
    body: InviteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await space_service.invite_member(db, space_id, current_user.id, body.email)


@router.patch("/{space_id}/members/{target_user_id}", response_model=SpaceMemberResponse)
async def update_member_role(
    space_id: uuid.UUID,
    target_user_id: uuid.UUID,
    body: MemberRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await space_service.update_member_role(
        db, space_id, current_user.id, target_user_id, body.role
    )
