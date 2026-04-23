import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import and_, extract, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.expense import Expense
from app.models.space import SpaceMember
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.services.exchange_rate_service import get_rate


async def _accessible_space_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    result = await db.execute(
        select(SpaceMember.space_id).where(SpaceMember.user_id == user_id)
    )
    return [row[0] for row in result.fetchall()]


async def get_expenses(
    db: AsyncSession,
    user_id: uuid.UUID,
    month: str | None = None,
    category_id: uuid.UUID | None = None,
    space_id: uuid.UUID | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Expense]:
    space_ids = await _accessible_space_ids(db, user_id)

    if space_ids:
        ownership = or_(
            Expense.user_id == user_id,
            Expense.space_id.in_(space_ids),
        )
    else:
        ownership = Expense.user_id == user_id

    query = select(Expense).where(and_(Expense.deleted_at.is_(None), ownership))

    if month:
        year_n, month_n = (int(p) for p in month.split("-"))
        query = query.where(
            and_(
                extract("year", Expense.date) == year_n,
                extract("month", Expense.date) == month_n,
            )
        )
    if category_id:
        query = query.where(Expense.category_id == category_id)
    if space_id:
        query = query.where(Expense.space_id == space_id)
    if q:
        query = query.where(Expense.title.ilike(f"%{q}%"))

    query = query.order_by(Expense.date.desc(), Expense.created_at.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    return list(result.scalars().all())


async def create_expense(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: ExpenseCreate,
    user_currency: str = "MAD",
) -> Expense:
    rate = await get_rate(db, data.currency, user_currency)
    amount_mad = (data.amount * rate).quantize(Decimal("0.01"))

    expense = Expense(
        id=uuid.uuid4(),
        title=data.title,
        amount=data.amount,
        currency=data.currency,
        amount_mad=amount_mad,
        exchange_rate=rate if data.currency != user_currency else None,
        date=data.date,
        category_id=data.category_id,
        user_id=user_id,
        space_id=data.space_id,
        note=data.note,
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    await _invalidate_dashboard_cache(user_id)
    return expense


async def update_expense(
    db: AsyncSession,
    expense_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ExpenseUpdate,
    user_currency: str = "MAD",
) -> Expense:
    expense = await _get_or_403(db, expense_id, user_id)
    update = data.model_dump(exclude_none=True)

    if "currency" in update or "amount" in update:
        new_currency = update.get("currency", expense.currency)
        new_amount = Decimal(str(update.get("amount", expense.amount)))
        rate = await get_rate(db, new_currency, user_currency)
        update["amount_mad"] = (new_amount * rate).quantize(Decimal("0.01"))
        update["exchange_rate"] = rate if new_currency != user_currency else None

    for field, value in update.items():
        setattr(expense, field, value)

    await db.commit()
    await db.refresh(expense)
    await _invalidate_dashboard_cache(user_id)
    return expense


async def delete_expense(
    db: AsyncSession, expense_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    expense = await _get_or_403(db, expense_id, user_id)
    expense.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await _invalidate_dashboard_cache(user_id)


async def _get_or_403(
    db: AsyncSession, expense_id: uuid.UUID, user_id: uuid.UUID
) -> Expense:
    expense = await db.get(Expense, expense_id)
    if expense is None or expense.deleted_at is not None:
        raise HTTPException(404, "Dépense introuvable")

    space_ids = await _accessible_space_ids(db, user_id)
    if expense.user_id != user_id and expense.space_id not in space_ids:
        raise HTTPException(403, "Accès refusé")
    return expense


async def _invalidate_dashboard_cache(user_id: uuid.UUID) -> None:
    redis = await get_redis()
    keys = await redis.keys(f"dash:{user_id}:*")
    if keys:
        await redis.delete(*keys)
