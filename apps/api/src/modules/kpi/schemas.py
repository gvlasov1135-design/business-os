import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from modules.kpi.models import KpiSnapshotStatus, KpiStatus, KpiVersionStatus


class KpiCreate(BaseModel):
    company_id: uuid.UUID
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    unit: str = "minutes"
    owner_name: str = Field(min_length=1, max_length=255)
    formula: dict[str, Any]
    source_mapping: dict[str, Any] = Field(default_factory=dict)
    target_value: float | None = None
    activate: bool = True


class KpiVersionCreate(BaseModel):
    formula: dict[str, Any]
    source_mapping: dict[str, Any] = Field(default_factory=dict)
    target_value: float | None = None
    change_reason: str | None = None


class KpiRecalculateRequest(BaseModel):
    period_start: datetime
    period_end: datetime


class KpiVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kpi_id: uuid.UUID
    company_id: uuid.UUID
    version_number: int
    status: KpiVersionStatus
    formula: dict[str, Any]
    source_mapping: dict[str, Any]
    target_value: float | None
    formula_text: str
    change_reason: str | None
    created_at: datetime


class KpiSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kpi_id: uuid.UUID
    version_id: uuid.UUID
    company_id: uuid.UUID
    period_start: datetime
    period_end: datetime
    target_value: float | None
    actual_value: float | None
    trust_index: float
    status: KpiSnapshotStatus
    conflict_flag: bool
    blocks_analysis: bool
    sources: list[dict[str, Any]]
    lineage: dict[str, Any]
    calculated_at: datetime


class KpiDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    code: str
    name: str
    description: str | None
    unit: str
    owner_name: str
    status: KpiStatus
    current_version_id: uuid.UUID | None
    trust_index: float
    created_at: datetime
    updated_at: datetime
