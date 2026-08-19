import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
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


class KpiStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    archived = "archived"


class KpiVersionStatus(str, enum.Enum):
    active = "active"
    superseded = "superseded"


class KpiSnapshotStatus(str, enum.Enum):
    calculated = "calculated"
    conflict = "conflict"
    incomplete = "incomplete"


class KpiDefinition(Base):
    __tablename__ = "kpi_definitions"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_kpi_company_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False, default="minutes")
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[KpiStatus] = mapped_column(
        Enum(KpiStatus, name="kpi_status", native_enum=False),
        nullable=False,
        default=KpiStatus.draft,
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    trust_index: Mapped[float] = mapped_column(Float(), nullable=False, default=0.7, server_default="0.7")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        default=lambda: datetime.now(),
    )


class KpiVersion(Base):
    __tablename__ = "kpi_versions"
    __table_args__ = (UniqueConstraint("kpi_id", "version_number", name="uq_kpi_version_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kpi_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("kpi_definitions.id"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[KpiVersionStatus] = mapped_column(
        Enum(KpiVersionStatus, name="kpi_version_status", native_enum=False),
        nullable=False,
        default=KpiVersionStatus.active,
    )
    # Structured formula only — no free-form eval
    formula: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    source_mapping: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    target_value: Mapped[float | None] = mapped_column(Float(), nullable=True)
    formula_text: Mapped[str] = mapped_column(String(500), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KpiSnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kpi_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("kpi_definitions.id"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("kpi_versions.id"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_value: Mapped[float | None] = mapped_column(Float(), nullable=True)
    actual_value: Mapped[float | None] = mapped_column(Float(), nullable=True)
    trust_index: Mapped[float] = mapped_column(Float(), nullable=False, default=0.0)
    status: Mapped[KpiSnapshotStatus] = mapped_column(
        Enum(KpiSnapshotStatus, name="kpi_snapshot_status", native_enum=False),
        nullable=False,
        default=KpiSnapshotStatus.calculated,
    )
    conflict_flag: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    blocks_analysis: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=list
    )
    lineage: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
