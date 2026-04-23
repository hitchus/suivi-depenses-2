import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class ExpenseCreate(BaseModel):
    title: str
    amount: Decimal
    currency: str = "MAD"
    date: date
    category_id: uuid.UUID | None = None
    space_id: uuid.UUID | None = None
    note: str | None = None

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


class ExpenseUpdate(BaseModel):
    title: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    date: date | None = None
    category_id: uuid.UUID | None = None
    note: str | None = None


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    amount: Decimal
    currency: str
    amount_mad: Decimal
    exchange_rate: Decimal | None
    date: date
    category_id: uuid.UUID | None
    user_id: uuid.UUID
    space_id: uuid.UUID | None
    note: str | None
    created_at: datetime
    updated_at: datetime
