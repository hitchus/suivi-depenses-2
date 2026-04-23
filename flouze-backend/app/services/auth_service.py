import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.category import Category
from app.models.user import User

DEFAULT_CATEGORIES = [
    {"name": "Alimentation",  "emoji": "🛒", "color": "#2D5F3F", "bg_color": "#EAF3DE"},
    {"name": "Transport",     "emoji": "🚗", "color": "#185FA5", "bg_color": "#E6F1FB"},
    {"name": "Logement",      "emoji": "🏠", "color": "#534AB7", "bg_color": "#EEEDFE"},
    {"name": "Loisirs",       "emoji": "🎬", "color": "#D85A30", "bg_color": "#FAECE7"},
    {"name": "Santé",         "emoji": "💊", "color": "#0F6E56", "bg_color": "#E1F5EE"},
    {"name": "Professionnel", "emoji": "💼", "color": "#BA7517", "bg_color": "#FAEEDA"},
]


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    display_name: str,
    currency: str = "MAD",
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_pwd=hash_password(password),
        display_name=display_name,
        currency=currency,
    )
    db.add(user)
    await db.flush()  # resolve user.id before seeding categories

    for cat in DEFAULT_CATEGORIES:
        db.add(Category(id=uuid.uuid4(), owner_id=user.id, **cat))

    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not user.hashed_pwd:
        return None
    if not verify_password(password, user.hashed_pwd):
        return None
    return user


async def issue_tokens(user: User) -> tuple[str, str]:
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token()
    redis = await get_redis()
    ttl = settings.refresh_token_expire_days * 86_400
    await redis.setex(f"refresh:{refresh_token}", ttl, str(user.id))
    return access_token, refresh_token


async def revoke_refresh_token(refresh_token: str) -> None:
    redis = await get_redis()
    await redis.delete(f"refresh:{refresh_token}")


async def rotate_refresh_token(old_token: str) -> tuple[str, str] | None:
    redis = await get_redis()
    user_id = await redis.get(f"refresh:{old_token}")
    if not user_id:
        return None
    await redis.delete(f"refresh:{old_token}")
    new_access = create_access_token(subject=user_id)
    new_refresh = create_refresh_token()
    ttl = settings.refresh_token_expire_days * 86_400
    await redis.setex(f"refresh:{new_refresh}", ttl, user_id)
    return new_access, new_refresh
