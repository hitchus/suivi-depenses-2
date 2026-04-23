import uuid
from decimal import Decimal

import httpx
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.models.exchange_rate import ExchangeRateLog

_CACHE_TTL = 3600  # 1 hour


async def get_rate(
    db: AsyncSession, from_currency: str, to_currency: str
) -> Decimal:
    """Return the exchange rate from_currency → to_currency.

    Resolution order:
    1. Redis cache (TTL 1h)
    2. External API (exchangerate.host)
    3. Latest persisted rate in exchange_rates_log
    4. 1.0 fallback (no API key configured in dev)
    """
    if from_currency == to_currency:
        return Decimal("1")

    redis = await get_redis()
    cache_key = f"rate:{from_currency}:{to_currency}"

    cached = await redis.get(cache_key)
    if cached:
        return Decimal(cached)

    rate = await _fetch_from_api(from_currency, to_currency)

    if rate is not None:
        await redis.setex(cache_key, _CACHE_TTL, str(rate))
        db.add(
            ExchangeRateLog(
                id=uuid.uuid4(),
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
            )
        )
        await db.flush()
        return rate

    # Fallback: last known rate from DB
    result = await db.execute(
        select(ExchangeRateLog)
        .where(
            ExchangeRateLog.from_currency == from_currency,
            ExchangeRateLog.to_currency == to_currency,
        )
        .order_by(desc(ExchangeRateLog.fetched_at))
        .limit(1)
    )
    log = result.scalar_one_or_none()
    if log:
        return log.rate

    return Decimal("1")  # dev fallback when no API key configured


async def _fetch_from_api(from_currency: str, to_currency: str) -> Decimal | None:
    if not settings.exchangerate_api_key:
        return None
    try:
        url = (
            f"https://api.exchangerate.host/convert"
            f"?from={from_currency}&to={to_currency}"
            f"&access_key={settings.exchangerate_api_key}"
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            data = resp.json()
            if data.get("success"):
                return Decimal(str(data["result"]))
    except Exception:
        pass
    return None
