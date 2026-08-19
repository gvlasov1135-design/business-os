import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from modules.resolution.models import (
    CandidateStatus,
    EntityType,
    MatchMethod,
    MembershipStatus,
    MergeEventType,
)


class CanonicalEntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    entity_type: EntityType
    display_name: str
    trust_index: float
    attributes: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EntityMembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    entity_id: uuid.UUID
    raw_record_id: uuid.UUID
    source_id: uuid.UUID
    external_id: str
    match_method: MatchMethod
    confidence: float
    status: MembershipStatus
    created_at: datetime


class EntityMatchCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    entity_type: EntityType
    left_raw_record_id: uuid.UUID
    right_raw_record_id: uuid.UUID
    proposed_entity_id: uuid.UUID | None
    match_method: MatchMethod
    confidence: float
    match_key: str
    match_value: str
    status: CandidateStatus
    requires_confirmation: bool
    blocks_analysis: bool
    evidence: dict[str, Any]
    created_at: datetime
    resolved_at: datetime | None


class EntityMergeEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    event_type: MergeEventType
    entity_id: uuid.UUID
    candidate_id: uuid.UUID | None
    raw_record_id: uuid.UUID | None
    note: str | None
    payload: dict[str, Any]
    created_at: datetime


class ResolveRawRecordResponse(BaseModel):
    entity: CanonicalEntityRead | None = None
    membership: EntityMembershipRead | None = None
    candidates: list[EntityMatchCandidateRead] = Field(default_factory=list)
    auto_linked: bool = False


class SplitMembershipRequest(BaseModel):
    note: str | None = None


class ConfirmCandidateRequest(BaseModel):
    note: str | None = None
