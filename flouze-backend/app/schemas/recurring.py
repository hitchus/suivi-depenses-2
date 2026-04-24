import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class RecurringRuleCreate(BaseModel):
    title: str
    amount: Decimal
    currency: str = "MAD"
    category_id: uuid.UUID | None = None
    space_id: uuid.UUID | None = None
    frequency: Literal["weekly", "monthly", "yearly"]
    start_date: date

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Le titre ne peut pas être vide")
        return v.strip()

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Le montant doit être positif")
        return v


class RecurringRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    amount: Decimal
    currency: str
    category_id: uuid.UUID | None
    space_id: uuid.UUID | None
    frequency: str
    next_run: datetime
    active: bool
    created_at: datetime
