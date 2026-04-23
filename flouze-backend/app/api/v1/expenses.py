import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.services import expense_service

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("", response_model=list[ExpenseResponse])
async def list_expenses(
    month: str | None = None,
    category_id: uuid.UUID | None = None,
    space_id: uuid.UUID | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await expense_service.get_expenses(
        db, current_user.id, month, category_id, space_id, q,
        min(limit, 100), offset,
    )


@router.post("", response_model=ExpenseResponse, status_code=201)
async def create_expense(
    body: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await expense_service.create_expense(
        db, current_user.id, body, current_user.currency
    )


@router.patch("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: uuid.UUID,
    body: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await expense_service.update_expense(
        db, expense_id, current_user.id, body, current_user.currency
    )


@router.delete("/{expense_id}", status_code=204)
async def delete_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await expense_service.delete_expense(db, expense_id, current_user.id)
