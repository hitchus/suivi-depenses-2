import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.notification import Notification


async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    type_: str,
    payload: dict,
) -> Notification:
    notif = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        type=type_,
        payload=payload,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)

    redis = await get_redis()
    await redis.publish(
        f"notify:{user_id}",
        json.dumps({"id": str(notif.id), "type": notif.type, "payload": notif.payload}),
    )
    return notif


async def list_notifications(
    db: AsyncSession,
    user_id: uuid.UUID,
    unread_only: bool = False,
) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.read_at.is_(None))
    q = q.order_by(Notification.created_at.desc()).limit(50)
    return list((await db.execute(q)).scalars().all())


async def mark_as_read(
    db: AsyncSession,
    notif_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification:
    notif = await db.get(Notification, notif_id)
    if notif is None or notif.user_id != user_id:
        raise HTTPException(404, "Notification introuvable")
    if notif.read_at is None:
        notif.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(notif)
    return notif
