import uuid
from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.budget import Budget
from app.models.expense import Expense
from app.schemas.dashboard import CategoryProgress, DashboardResponse, MonthlyPoint
from app.services.category_service import get_categories

_CACHE_TTL = 300  # 5 minutes


def _prev_months(year: int, month: int, n: int) -> list[tuple[int, int]]:
    """Return the n months ending at (year, month), oldest first."""
    result = []
    y, m = year, month
    for _ in range(n):
        result.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(result))


async def get_dashboard(
    db: AsyncSession, user_id: uuid.UUID, month: str
) -> DashboardResponse:
    cache_key = f"dash:{user_id}:{month}"
    redis = await get_redis()

    cached = await redis.get(cache_key)
    if cached:
        return DashboardResponse.model_validate_json(cached)

    year, month_num = (int(p) for p in month.split("-"))

    # ── Expenses for month, grouped by category ───────────────────────────
    expense_rows = (
        await db.execute(
            select(
                Expense.category_id,
                func.sum(Expense.amount_mad).label("spent"),
                func.count(Expense.id).label("cnt"),
            )
            .where(
                and_(
                    Expense.deleted_at.is_(None),
                    Expense.user_id == user_id,
                    extract("year", Expense.date) == year,
                    extract("month", Expense.date) == month_num,
                )
            )
            .group_by(Expense.category_id)
        )
    ).all()

    expenses_by_cat: dict[uuid.UUID | None, tuple[Decimal, int]] = {
        row.category_id: (Decimal(str(row.spent or 0)), int(row.cnt))
        for row in expense_rows
    }
    total = sum(v[0] for v in expenses_by_cat.values()) or Decimal("0")

    # ── Budgets for month ─────────────────────────────────────────────────
    budget_rows = (
        await db.execute(
            select(Budget).where(
                and_(Budget.user_id == user_id, Budget.month == month)
            )
        )
    ).scalars().all()
    # category_id=None → global monthly budget
    budgets_by_cat: dict[uuid.UUID | None, Decimal] = {
        b.category_id: b.amount for b in budget_rows
    }
    global_budget = budgets_by_cat.get(None)

    # ── Active categories (personal) ──────────────────────────────────────
    categories = await get_categories(db, user_id)
    by_category: list[CategoryProgress] = [
        CategoryProgress(
            category_id=cat.id,
            name=cat.name,
            emoji=cat.emoji,
            color=cat.color,
            bg_color=cat.bg_color,
            spent=expenses_by_cat.get(cat.id, (Decimal("0"), 0))[0],
            budget=budgets_by_cat.get(cat.id),
            expense_count=expenses_by_cat.get(cat.id, (Decimal("0"), 0))[1],
        )
        for cat in categories
    ]

    # ── Monthly trend — last 6 months ─────────────────────────────────────
    months_range = _prev_months(year, month_num, 6)
    first_y, first_m = months_range[0]
    last_y, last_m = months_range[-1]
    _, last_day = monthrange(last_y, last_m)

    trend_rows = (
        await db.execute(
            select(
                extract("year", Expense.date).label("y"),
                extract("month", Expense.date).label("m"),
                func.sum(Expense.amount_mad).label("total"),
            )
            .where(
                and_(
                    Expense.deleted_at.is_(None),
                    Expense.user_id == user_id,
                    Expense.date >= date(first_y, first_m, 1),
                    Expense.date <= date(last_y, last_m, last_day),
                )
            )
            .group_by("y", "m")
            .order_by("y", "m")
        )
    ).all()

    trend_map = {
        (int(row.y), int(row.m)): Decimal(str(row.total or 0))
        for row in trend_rows
    }
    monthly_trend: list[MonthlyPoint] = [
        MonthlyPoint(
            month=f"{y:04d}-{m:02d}",
            total=trend_map.get((y, m), Decimal("0")),
        )
        for y, m in months_range
    ]

    response = DashboardResponse(
        month=month,
        total=total,
        budget_global=global_budget,
        restant=(global_budget - total) if global_budget is not None else None,
        by_category=by_category,
        monthly_trend=monthly_trend,
    )

    await redis.setex(cache_key, _CACHE_TTL, response.model_dump_json())
    return response
