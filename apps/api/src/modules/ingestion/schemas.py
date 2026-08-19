import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from modules.ingestion.models import RawRecordStatus, SourceStatus, SourceType


class SourceCreate(BaseModel):
    company_id: uuid.UUID
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    source_type: SourceType
    freshness_hours: int = Field(default=24, ge=1)


class SourceStatusUpdate(BaseModel):
    status: SourceStatus | None = None


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    code: str
    name: str
    source_type: SourceType
    status: SourceStatus
    freshness_hours: int
    last_synced_at: datetime | None
    created_at: datetime


class ImportRequest(BaseModel):
    source_id: uuid.UUID
    payload: dict[str, Any]


class RawRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    company_id: uuid.UUID
    external_id: str
    payload: dict[str, Any]
    checksum_sha256: str
    status: RawRecordStatus
    created_at: datetime


class ObservedFactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    source_id: uuid.UUID
    raw_record_id: uuid.UUID
    subject: str
    predicate: str
    value_text: str
    value_structured: dict[str, Any] | None
    observed_at: datetime
    trust_index: float
    lineage: dict[str, Any]
    created_at: datetime


class ImportResponse(BaseModel):
    raw_record: RawRecordRead
    fact: ObservedFactRead | None = None
    duplicate: bool = False
    blocked: bool = False
    issues: list[dict[str, Any]] = Field(default_factory=list)


class WorkbookImportResponse(BaseModel):
    filename: str | None = None
    workbook_kind: str | None = None
    notes: list[str] = Field(default_factory=list)
    sheets: list[dict[str, Any]] = Field(default_factory=list)
    source_ids: dict[str, str] = Field(default_factory=dict)
    metrics_total: int = 0
    imported: int = 0
    duplicates: int = 0
    by_origin: dict[str, int] = Field(default_factory=dict)
    fact_ids: list[str] = Field(default_factory=list)
    fact_count: int = 0
