from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    payload: dict
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
