import uuid
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget


async def get_budgets_for_month(
    db: AsyncSession, user_id: uuid.UUID, month: str
) -> list[Budget]:
    result = await db.execute(
        select(Budget).where(
            and_(Budget.user_id == user_id, Budget.month == month)
        )
    )
    return list(result.scalars().all())


async def upsert_budget(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_id: uuid.UUID | None,
    month: str,
    amount: Decimal,
) -> Budget:
    result = await db.execute(
        select(Budget).where(
            and_(
                Budget.user_id == user_id,
                Budget.category_id == category_id,
                Budget.month == month,
            )
        )
    )
    budget = result.scalar_one_or_none()

    if budget:
        budget.amount = amount
    else:
        budget = Budget(
            id=uuid.uuid4(),
            user_id=user_id,
            category_id=category_id,
            month=month,
            amount=amount,
        )
        db.add(budget)

    await db.commit()
    await db.refresh(budget)
    return budget
