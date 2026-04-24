import uuid
from decimal import Decimal

from pydantic import BaseModel


class CategoryProgress(BaseModel):
    category_id: uuid.UUID
    name: str
    emoji: str
    color: str
    bg_color: str
    spent: Decimal
    budget: Decimal | None  # None if no budget defined
    expense_count: int


class MonthlyPoint(BaseModel):
    month: str  # YYYY-MM
    total: Decimal


class DashboardResponse(BaseModel):
    month: str
    total: Decimal
    budget_global: Decimal | None
    restant: Decimal | None  # None if no global budget defined
    by_category: list[CategoryProgress]
    monthly_trend: list[MonthlyPoint]
