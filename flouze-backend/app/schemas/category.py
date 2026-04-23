import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class CategoryCreate(BaseModel):
    name: str
    emoji: str = "📦"
    color: str = "#2D5F3F"
    bg_color: str = "#EAF3DE"
    space_id: uuid.UUID | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Le nom ne peut pas être vide")
        return v.strip()


class CategoryUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    color: str | None = None
    bg_color: str | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    emoji: str
    color: str
    bg_color: str
    owner_id: uuid.UUID | None
    space_id: uuid.UUID | None
    archived_at: datetime | None
    created_at: datetime
