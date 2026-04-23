import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.space import SpaceMember
from app.schemas.category import CategoryCreate, CategoryUpdate


async def _accessible_space_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    result = await db.execute(
        select(SpaceMember.space_id).where(SpaceMember.user_id == user_id)
    )
    return [row[0] for row in result.fetchall()]


async def get_categories(
    db: AsyncSession,
    user_id: uuid.UUID,
    include_archived: bool = False,
) -> list[Category]:
    space_ids = await _accessible_space_ids(db, user_id)

    from sqlalchemy import or_

    if space_ids:
        ownership_clause = or_(
            Category.owner_id == user_id,
            Category.space_id.in_(space_ids),
        )
    else:
        ownership_clause = Category.owner_id == user_id

    query = select(Category).where(ownership_clause)
    if not include_archived:
        query = query.where(Category.archived_at.is_(None))
    query = query.order_by(Category.created_at)

    result = await db.execute(query)
    return list(result.scalars().all())


async def _get_or_403(
    db: AsyncSession, category_id: uuid.UUID, user_id: uuid.UUID
) -> Category:
    cat = await db.get(Category, category_id)
    if cat is None:
        raise HTTPException(404, "Catégorie introuvable")

    space_ids = await _accessible_space_ids(db, user_id)
    if cat.owner_id != user_id and cat.space_id not in space_ids:
        raise HTTPException(403, "Accès refusé")
    return cat


async def create_category(
    db: AsyncSession, user_id: uuid.UUID, data: CategoryCreate
) -> Category:
    cat = Category(
        id=uuid.uuid4(),
        name=data.name,
        emoji=data.emoji,
        color=data.color,
        bg_color=data.bg_color,
        owner_id=user_id if data.space_id is None else None,
        space_id=data.space_id,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


async def update_category(
    db: AsyncSession,
    category_id: uuid.UUID,
    user_id: uuid.UUID,
    data: CategoryUpdate,
) -> Category:
    cat = await _get_or_403(db, category_id, user_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(cat, field, value)
    await db.commit()
    await db.refresh(cat)
    return cat


async def archive_category(
    db: AsyncSession, category_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    cat = await _get_or_403(db, category_id, user_id)
    cat.archived_at = datetime.now(timezone.utc)
    await db.commit()
