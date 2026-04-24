import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class SpaceCreate(BaseModel):
    name: str


class InviteRequest(BaseModel):
    email: EmailStr


class MemberRoleUpdate(BaseModel):
    role: str  # admin | member


class SpaceMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    space_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime


class SpaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime
