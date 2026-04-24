import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.budget import BudgetResponse, BudgetUpsert
from app.services import budget_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    month: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    m = month or date.today().strftime("%Y-%m")
    return await budget_service.get_budgets_for_month(db, current_user.id, m)


@router.put("/global", response_model=BudgetResponse)
async def upsert_global_budget(
    body: BudgetUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set / update the monthly global budget (no category restriction)."""
    return await budget_service.upsert_budget(
        db, current_user.id, None, body.month, body.amount
    )


@router.put("/{category_id}", response_model=BudgetResponse)
async def upsert_category_budget(
    category_id: uuid.UUID,
    body: BudgetUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set / update a monthly budget for a specific category."""
    return await budget_service.upsert_budget(
        db, current_user.id, category_id, body.month, body.amount
    )
