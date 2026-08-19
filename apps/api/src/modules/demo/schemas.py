import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DemoRunRequest(BaseModel):
    company_id: uuid.UUID | None = None


class DemoRunResponse(BaseModel):
    company_id: uuid.UUID
    document_id: uuid.UUID
    version_id: uuid.UUID
    statement_id: uuid.UUID
    source_id: uuid.UUID
    raw_record_id: uuid.UUID
    fact_id: uuid.UUID
    check_id: uuid.UUID
    issue_id: uuid.UUID
    knowledge_id: uuid.UUID
    analysis_id: uuid.UUID
    recommendation_id: uuid.UUID | None = None
    decision_id: uuid.UUID
    extras: dict[str, Any] = Field(default_factory=dict)
