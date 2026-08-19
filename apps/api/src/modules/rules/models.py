import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from infrastructure.db import Base


class RuleKind(str, enum.Enum):
    alignment = "alignment"
    trust = "trust"
    freshness = "freshness"
    kpi_formula = "kpi_formula"
    extraction = "extraction"
    prompt = "prompt"
    agent_profile = "agent_profile"
    decision_dna = "decision_dna"


class RuleVersionStatus(str, enum.Enum):
    active = "active"
    superseded = "superseded"
    draft = "draft"


class RuleDefinition(Base):
    __tablename__ = "rule_definitions"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_rule_company_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[RuleKind] = mapped_column(
        Enum(RuleKind, name="rule_kind", native_enum=False),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RuleVersion(Base):
    __tablename__ = "rule_versions"
    __table_args__ = (UniqueConstraint("rule_id", "version_number", name="uq_rule_version_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("rule_definitions.id"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[RuleVersionStatus] = mapped_column(
        Enum(RuleVersionStatus, name="rule_version_status", native_enum=False),
        nullable=False,
        default=RuleVersionStatus.active,
    )
    body: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    change_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
