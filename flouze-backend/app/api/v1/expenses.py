import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.services import expense_service, export_service

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("/export")
async def export_expenses(
    format: str = "xlsx",
    month: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    m = month or date.today().strftime("%Y-%m")
    fmt = format.lower()
    if fmt not in ("xlsx", "pdf"):
        raise HTTPException(400, "format doit être 'xlsx' ou 'pdf'")

    if fmt == "xlsx":
        content = await export_service.generate_excel(db, current_user.id, m)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="flouze_{m}.xlsx"'},
        )
    else:
        content = await export_service.generate_pdf(db, current_user.id, m)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="flouze_{m}.pdf"'},
        )


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
