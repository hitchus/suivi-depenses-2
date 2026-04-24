import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class BudgetUpsert(BaseModel):
    amount: Decimal
    month: str  # YYYY-MM

    @field_validator("amount")
    @classmethod
    def amount_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Le budget ne peut pas être négatif")
        return v

    @field_validator("month")
    @classmethod
    def valid_month_format(cls, v: str) -> str:
        parts = v.split("-")
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            raise ValueError("Format invalide, utiliser YYYY-MM")
        return v


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    space_id: uuid.UUID | None
    category_id: uuid.UUID | None
    amount: Decimal
    month: str
    created_at: datetime
    updated_at: datetime
