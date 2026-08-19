import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, computed_field

from modules.alignment.models import AlignmentCheckStatus, AlignmentIssueSeverity, AlignmentIssueStatus


class AlignmentCheckRequest(BaseModel):
    company_id: uuid.UUID
    statement_id: uuid.UUID
    fact_id: uuid.UUID
    check_type: str = "deadline"  # deadline | responsible | process_stage


class AlignmentCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    rule_code: str
    status: AlignmentCheckStatus
    created_at: datetime


class AlignmentIssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    check_id: uuid.UUID
    company_id: uuid.UUID
    document_id: uuid.UUID | None
    statement_id: uuid.UUID | None
    fact_id: uuid.UUID | None
    normative_value: dict[str, Any]
    actual_value: dict[str, Any]
    deviation_value: dict[str, Any]
    severity: AlignmentIssueSeverity
    trust_index: float
    status: AlignmentIssueStatus
    evidence: dict[str, Any]
    owner_user_id: uuid.UUID | None
    created_at: datetime
    reviewed_at: datetime | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def proposed_change(self) -> dict[str, Any] | None:
        return (self.evidence or {}).get("proposed_change")


class AlignmentCheckResponse(BaseModel):
    check: AlignmentCheckRead
    issue: AlignmentIssueRead
