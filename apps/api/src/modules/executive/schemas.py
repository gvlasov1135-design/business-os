import uuid
from typing import Any

from pydantic import BaseModel, Field


class MetricBlock(BaseModel):
    score: float
    label: str
    detail: str
    status: str  # ready | warn | blocked


class ExecutiveReadinessResponse(BaseModel):
    company_id: uuid.UUID
    analysis_ready: bool
    gate_reasons: list[str] = Field(default_factory=list)
    completeness: MetricBlock
    trust_index: MetricBlock
    alignment_score: MetricBlock
    document_health: MetricBlock
    kpi_health: MetricBlock
    counts: dict[str, int] = Field(default_factory=dict)
    latest_analysis_id: uuid.UUID | None = None
    latest_decision_id: uuid.UUID | None = None
    limitations: list[str] = Field(default_factory=list)
    evidence_preview: list[dict[str, Any]] = Field(default_factory=list)
    sla_axes: dict[str, int] = Field(default_factory=dict)
