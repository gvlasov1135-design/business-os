import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    payload: dict[str, Any] | None = None
    created_at: datetime


class JobEnqueueResponse(BaseModel):
    job_id: str
    queue: str = Field(default="business-os:jobs")
    type: str
