import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from modules.outbox.models import OutboxStatus


class OutboxEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    event_type: str
    aggregate_type: str
    aggregate_id: uuid.UUID | None
    payload: dict[str, Any] = Field(default_factory=dict)
    status: OutboxStatus
    error_message: str | None
    created_at: datetime
    published_at: datetime | None
