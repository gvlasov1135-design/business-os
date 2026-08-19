import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from infrastructure.db import Base


class KnowledgeRecordType(str, enum.Enum):
    norm = "norm"
    fact = "fact"
    alignment = "alignment"
    lesson = "lesson"


class KnowledgeRecordStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    superseded = "superseded"


class KnowledgeRelationType(str, enum.Enum):
    supports = "supports"
    conflicts = "conflicts"
    derived_from = "derived_from"
    relates_to = "relates_to"


class KnowledgeRecord(Base):
    __tablename__ = "knowledge_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    record_type: Mapped[KnowledgeRecordType] = mapped_column(
        Enum(KnowledgeRecordType, name="knowledge_record_type", native_enum=False),
        nullable=False,
    )
    status: Mapped[KnowledgeRecordStatus] = mapped_column(
        Enum(KnowledgeRecordStatus, name="knowledge_record_status", native_enum=False),
        nullable=False,
        default=KnowledgeRecordStatus.draft,
    )
    trust_index: Mapped[float] = mapped_column(Float(), nullable=False, default=0.8)
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=list
    )
    alignment_issue_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alignment_issues.id"), nullable=True, index=True
    )
    statement_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("extracted_statements.id"), nullable=True, index=True
    )
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KnowledgeRelation(Base):
    __tablename__ = "knowledge_relations"
    __table_args__ = (
        UniqueConstraint(
            "from_record_id",
            "to_record_id",
            "relation_type",
            name="uq_knowledge_relation_edge",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    from_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("knowledge_records.id"), nullable=False, index=True
    )
    to_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("knowledge_records.id"), nullable=False, index=True
    )
    relation_type: Mapped[KnowledgeRelationType] = mapped_column(
        Enum(KnowledgeRelationType, name="knowledge_relation_type", native_enum=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
