import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from infrastructure.db import Base


class EntityType(str, enum.Enum):
    counterparty = "counterparty"
    employee = "employee"
    document = "document"
    lead = "lead"


class MatchMethod(str, enum.Enum):
    exact = "exact"
    deterministic = "deterministic"
    candidate = "candidate"


class CandidateStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"


class MembershipStatus(str, enum.Enum):
    active = "active"
    split = "split"


class MergeEventType(str, enum.Enum):
    merge = "merge"
    split = "split"
    auto_link = "auto_link"


class CanonicalEntity(Base):
    __tablename__ = "canonical_entities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type", native_enum=False),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    trust_index: Mapped[float] = mapped_column(Float(), nullable=False, default=0.7, server_default="0.7")
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class EntityMembership(Base):
    """Связь исходной записи с канонической сущностью. Исходные записи не удаляются."""

    __tablename__ = "entity_memberships"
    __table_args__ = (
        UniqueConstraint("raw_record_id", name="uq_entity_membership_raw_record"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("canonical_entities.id"), nullable=False, index=True
    )
    raw_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("raw_records.id"), nullable=False, index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sources.id"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    match_method: Mapped[MatchMethod] = mapped_column(
        Enum(MatchMethod, name="membership_match_method", native_enum=False),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float(), nullable=False, default=1.0)
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, name="membership_status", native_enum=False),
        nullable=False,
        default=MembershipStatus.active,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EntityMatchCandidate(Base):
    __tablename__ = "entity_match_candidates"
    __table_args__ = (
        UniqueConstraint(
            "left_raw_record_id",
            "right_raw_record_id",
            "match_method",
            name="uq_entity_match_pair",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="candidate_entity_type", native_enum=False),
        nullable=False,
    )
    left_raw_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("raw_records.id"), nullable=False, index=True
    )
    right_raw_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("raw_records.id"), nullable=False, index=True
    )
    proposed_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("canonical_entities.id"), nullable=True, index=True
    )
    match_method: Mapped[MatchMethod] = mapped_column(
        Enum(MatchMethod, name="candidate_match_method", native_enum=False),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float(), nullable=False)
    match_key: Mapped[str] = mapped_column(String(255), nullable=False)
    match_value: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[CandidateStatus] = mapped_column(
        Enum(CandidateStatus, name="candidate_status", native_enum=False),
        nullable=False,
        default=CandidateStatus.pending,
    )
    requires_confirmation: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    blocks_analysis: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EntityMergeEvent(Base):
    __tablename__ = "entity_merge_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    event_type: Mapped[MergeEventType] = mapped_column(
        Enum(MergeEventType, name="merge_event_type", native_enum=False),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("canonical_entities.id"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("entity_match_candidates.id"), nullable=True
    )
    raw_record_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("raw_records.id"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
