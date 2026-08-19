import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from modules.quality.models import IssueSeverity, IssueStatus


class DataQualityIssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    raw_record_id: uuid.UUID | None
    source_id: uuid.UUID | None
    code: str
    message: str
    severity: IssueSeverity
    status: IssueStatus
    blocks_analysis: bool
    created_at: datetime


class AnalysisGateResponse(BaseModel):
    blocked: bool
    reasons: list[str]


class DataDoctorExplanation(BaseModel):
    issue_id: uuid.UUID
    explanation: str
    likely_cause: str
    suggested_fix: str
    suggested_owner: str
    prepared_task: str
    read_only: bool = True
    can_unblock_analysis: bool = False
    provider: str = "mock"


class ResolveIssueRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class ResolveIssueResponse(DataQualityIssueRead):
    resolution_reason: str | None = None
