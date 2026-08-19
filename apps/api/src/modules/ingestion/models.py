import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from infrastructure.db import Base


class SourceType(str, enum.Enum):
    crm = "crm"
    csv = "csv"
    api = "api"
    workbook = "workbook"


class SourceStatus(str, enum.Enum):
    active = "active"
    stale = "stale"
    disabled = "disabled"


class RawRecordStatus(str, enum.Enum):
    received = "received"
    normalized = "normalized"
    quarantine = "quarantine"


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_sources_company_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type", native_enum=False),
        nullable=False,
    )
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, name="source_status", native_enum=False),
        nullable=False,
        default=SourceStatus.active,
    )
    freshness_hours: Mapped[int] = mapped_column(Integer(), nullable=False, default=24, server_default="24")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RawRecord(Base):
    __tablename__ = "raw_records"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_raw_records_source_external_id"),
        UniqueConstraint("source_id", "checksum_sha256", name="uq_raw_records_source_checksum"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sources.id"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[RawRecordStatus] = mapped_column(
        Enum(RawRecordStatus, name="raw_record_status", native_enum=False),
        nullable=False,
        default=RawRecordStatus.received,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ObservedFact(Base):
    __tablename__ = "observed_facts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sources.id"), nullable=False, index=True
    )
    raw_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("raw_records.id"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    predicate: Mapped[str] = mapped_column(String(255), nullable=False)
    value_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    value_structured: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trust_index: Mapped[float] = mapped_column(Float(), nullable=False, default=0.7, server_default="0.7")
    lineage: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
