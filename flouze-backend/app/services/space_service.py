import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.space import Space, SpaceMember
from app.models.user import User
from app.schemas.space import SpaceCreate, SpaceResponse


async def get_user_spaces(db: AsyncSession, user_id: uuid.UUID) -> list[SpaceResponse]:
    result = await db.execute(
        select(Space)
        .join(SpaceMember, SpaceMember.space_id == Space.id)
        .where(SpaceMember.user_id == user_id)
        .order_by(Space.created_at)
    )
    spaces = result.scalars().all()
    return [SpaceResponse.model_validate(s) for s in spaces]


async def create_space(
    db: AsyncSession, user_id: uuid.UUID, data: SpaceCreate
) -> SpaceResponse:
    space = Space(id=uuid.uuid4(), name=data.name, owner_id=user_id)
    db.add(space)
    await db.flush()

    db.add(SpaceMember(space_id=space.id, user_id=user_id, role="admin"))
    await db.commit()
    await db.refresh(space)
    return SpaceResponse.model_validate(space)


async def _require_admin(db: AsyncSession, space_id: uuid.UUID, user_id: uuid.UUID) -> None:
    member = await db.get(SpaceMember, (space_id, user_id))
    if member is None or member.role != "admin":
        raise HTTPException(403, "Seul un administrateur peut effectuer cette action")


async def invite_member(
    db: AsyncSession, space_id: uuid.UUID, inviter_id: uuid.UUID, email: str
) -> SpaceMember:
    await _require_admin(db, space_id, inviter_id)

    result = await db.execute(select(User).where(User.email == email))
    invited = result.scalar_one_or_none()
    if invited is None:
        raise HTTPException(404, "Aucun compte trouvé pour cet email")

    existing = await db.get(SpaceMember, (space_id, invited.id))
    if existing is not None:
        raise HTTPException(409, "Cet utilisateur est déjà membre de l'espace")

    member = SpaceMember(space_id=space_id, user_id=invited.id, role="member")
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def update_member_role(
    db: AsyncSession,
    space_id: uuid.UUID,
    actor_id: uuid.UUID,
    target_user_id: uuid.UUID,
    role: str,
) -> SpaceMember:
    await _require_admin(db, space_id, actor_id)

    if role not in ("admin", "member"):
        raise HTTPException(400, "Rôle invalide, valeurs acceptées : admin, member")

    member = await db.get(SpaceMember, (space_id, target_user_id))
    if member is None:
        raise HTTPException(404, "Membre introuvable")

    member.role = role
    await db.commit()
    await db.refresh(member)
    return member
