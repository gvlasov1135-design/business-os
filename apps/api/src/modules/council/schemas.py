import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from modules.council.models import CouncilAgent, CouncilChannel, CouncilMessageRole, CouncilSessionStatus


class CouncilSessionCreate(BaseModel):
    company_id: uuid.UUID
    topic: str | None = None
    analysis_id: uuid.UUID | None = None


class CouncilMessageCreate(BaseModel):
    channel: CouncilChannel
    body: str = Field(min_length=1, max_length=8000)
    agent: CouncilAgent | None = None


class CouncilMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    company_id: uuid.UUID
    channel: CouncilChannel
    role: CouncilMessageRole
    agent: CouncilAgent | None
    body: str
    created_at: datetime


class CouncilSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    analysis_id: uuid.UUID | None
    topic: str
    status: CouncilSessionStatus
    context_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    messages: list[CouncilMessageRead] = Field(default_factory=list)


class CouncilSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    analysis_id: uuid.UUID | None
    topic: str
    status: CouncilSessionStatus
    created_at: datetime
