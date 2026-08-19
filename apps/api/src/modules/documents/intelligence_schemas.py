import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from modules.documents.intelligence_models import (
    FragmentType,
    StatementStatus,
    StatementType,
)


class SourceAnchor(BaseModel):
    fragment_id: uuid.UUID
    quote: str
    char_start: int | None = None
    char_end: int | None = None
    page_number: int | None = None


class DocumentFragmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_id: uuid.UUID
    ordinal: int
    fragment_type: FragmentType
    text: str
    page_number: int | None
    char_start: int | None
    char_end: int | None
    created_at: datetime


class ExtractedStatementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    version_id: uuid.UUID
    fragment_id: uuid.UUID
    statement_type: StatementType
    value_text: str
    value_structured: dict | None
    confidence: float
    status: StatementStatus
    source_anchor: dict
    created_at: datetime
    reviewed_at: datetime | None


class ExtractionRunResult(BaseModel):
    fragment: DocumentFragmentRead
    statement: ExtractedStatementRead
    statements: list[ExtractedStatementRead] = Field(default_factory=list)


class ManualStatementCreate(BaseModel):
    fragment_id: uuid.UUID
    statement_type: StatementType = StatementType.deadline
    value_text: str = Field(min_length=1)
    value_structured: dict | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    quote: str | None = None
    char_start: int | None = None
    char_end: int | None = None
