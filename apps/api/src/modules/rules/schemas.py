import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from modules.rules.models import RuleKind, RuleVersionStatus


class RuleCreate(BaseModel):
    company_id: uuid.UUID
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    kind: RuleKind
    description: str | None = None
    body: dict[str, Any] = Field(default_factory=dict)


class RuleVersionCreate(BaseModel):
    body: dict[str, Any]
    change_reason: str | None = None


class RuleVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_id: uuid.UUID
    company_id: uuid.UUID
    version_number: int
    status: RuleVersionStatus
    body: dict[str, Any]
    change_reason: str | None
    created_at: datetime


class RuleDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    code: str
    name: str
    kind: RuleKind
    description: str | None
    current_version_id: uuid.UUID | None
    created_at: datetime
