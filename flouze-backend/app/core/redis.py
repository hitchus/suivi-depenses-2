from redis.asyncio import Redis
from redis.asyncio import from_url

from app.core.config import settings

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = await from_url(settings.redis_url, decode_responses=True)
    return _redis


async def check_redis_connection() -> bool:
    try:
        r = await get_redis()
        await r.ping()
        return True
    except Exception:
        return False
