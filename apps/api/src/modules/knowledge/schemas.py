import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from modules.knowledge.models import KnowledgeRecordStatus, KnowledgeRecordType, KnowledgeRelationType


class KnowledgeRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    body: str
    record_type: KnowledgeRecordType
    status: KnowledgeRecordStatus
    trust_index: float
    source_refs: list[dict[str, Any]]
    alignment_issue_id: uuid.UUID | None
    statement_id: uuid.UUID | None
    valid_from: datetime | None
    valid_to: datetime | None
    created_at: datetime


class KnowledgeRelationCreate(BaseModel):
    company_id: uuid.UUID
    from_record_id: uuid.UUID
    to_record_id: uuid.UUID
    relation_type: KnowledgeRelationType = KnowledgeRelationType.relates_to


class KnowledgeRelationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    from_record_id: uuid.UUID
    to_record_id: uuid.UUID
    relation_type: KnowledgeRelationType
    created_at: datetime


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeRecordRead] = Field(default_factory=list)
