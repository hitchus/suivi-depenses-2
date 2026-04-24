import calendar
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.models.recurring_rule import RecurringRule
from app.models.user import User
from app.schemas.recurring import RecurringRuleCreate
from app.services.exchange_rate_service import get_rate


def _next_occurrence(frequency: str, from_date: date) -> datetime:
    if frequency == "weekly":
        d = from_date + timedelta(days=7)
    elif frequency == "monthly":
        month = from_date.month + 1
        year = from_date.year
        if month > 12:
            month = 1
            year += 1
        last_day = calendar.monthrange(year, month)[1]
        d = date(year, month, min(from_date.day, last_day))
    elif frequency == "yearly":
        year = from_date.year + 1
        last_day = calendar.monthrange(year, from_date.month)[1]
        d = date(year, from_date.month, min(from_date.day, last_day))
    else:
        raise ValueError(f"Fréquence inconnue : {frequency}")
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


async def create_rule(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: RecurringRuleCreate,
) -> RecurringRule:
    rule = RecurringRule(
        id=uuid.uuid4(),
        user_id=user_id,
        title=data.title,
        amount=data.amount,
        currency=data.currency,
        category_id=data.category_id,
        space_id=data.space_id,
        frequency=data.frequency,
        next_run=datetime(
            data.start_date.year,
            data.start_date.month,
            data.start_date.day,
            tzinfo=timezone.utc,
        ),
        active=True,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def get_rules(
    db: AsyncSession,
    user_id: uuid.UUID,
    include_inactive: bool = False,
) -> list[RecurringRule]:
    q = select(RecurringRule).where(RecurringRule.user_id == user_id)
    if not include_inactive:
        q = q.where(RecurringRule.active.is_(True))
    q = q.order_by(RecurringRule.created_at.desc())
    return list((await db.execute(q)).scalars().all())


async def deactivate_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
    user_id: uuid.UUID,
) -> RecurringRule:
    rule = await db.get(RecurringRule, rule_id)
    if rule is None or rule.user_id != user_id:
        raise HTTPException(404, "Règle introuvable")
    rule.active = False
    await db.commit()
    await db.refresh(rule)
    return rule


async def process_due_rules(db: AsyncSession) -> int:
    """Instantiate all recurring rules whose next_run is now or past. Returns count."""
    from app.services.expense_service import _invalidate_dashboard_cache

    now = datetime.now(timezone.utc)
    rules = list(
        (
            await db.execute(
                select(RecurringRule).where(
                    and_(
                        RecurringRule.active.is_(True),
                        RecurringRule.next_run <= now,
                    )
                )
            )
        ).scalars().all()
    )

    count = 0
    affected_users: set[uuid.UUID] = set()

    for rule in rules:
        user = await db.get(User, rule.user_id)
        if user is None:
            continue

        rate = await get_rate(db, rule.currency, user.currency)
        amount_mad = (rule.amount * rate).quantize(Decimal("0.01"))

        expense = Expense(
            id=uuid.uuid4(),
            title=rule.title,
            amount=rule.amount,
            currency=rule.currency,
            amount_mad=amount_mad,
            exchange_rate=rate if rule.currency != user.currency else None,
            date=rule.next_run.date(),
            category_id=rule.category_id,
            user_id=rule.user_id,
            space_id=rule.space_id,
            recurring_rule_id=rule.id,
        )
        db.add(expense)

        rule.next_run = _next_occurrence(rule.frequency, rule.next_run.date())
        affected_users.add(rule.user_id)
        count += 1

    if count > 0:
        await db.commit()
        for uid in affected_users:
            await _invalidate_dashboard_cache(uid)

    return count
