import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from infrastructure.db import Base


class AlignmentCheckStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"


class AlignmentIssueSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlignmentIssueStatus(str, enum.Enum):
    open = "open"
    confirmed = "confirmed"
    rejected = "rejected"
    accepted_deviation = "accepted_deviation"
    needs_data = "needs_data"


class AlignmentCheck(Base):
    __tablename__ = "alignment_checks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("rule_versions.id"), nullable=True, index=True
    )
    status: Mapped[AlignmentCheckStatus] = mapped_column(
        Enum(AlignmentCheckStatus, name="alignment_check_status", native_enum=False),
        nullable=False,
        default=AlignmentCheckStatus.pending,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AlignmentIssue(Base):
    __tablename__ = "alignment_issues"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    check_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alignment_checks.id"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id"), nullable=True, index=True
    )
    statement_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("extracted_statements.id"), nullable=True, index=True
    )
    fact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("observed_facts.id"), nullable=True, index=True
    )
    normative_value: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    actual_value: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    deviation_value: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    severity: Mapped[AlignmentIssueSeverity] = mapped_column(
        Enum(AlignmentIssueSeverity, name="alignment_issue_severity", native_enum=False),
        nullable=False,
    )
    trust_index: Mapped[float] = mapped_column(Float(), nullable=False, default=0.5)
    status: Mapped[AlignmentIssueStatus] = mapped_column(
        Enum(AlignmentIssueStatus, name="alignment_issue_status", native_enum=False),
        nullable=False,
        default=AlignmentIssueStatus.open,
    )
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
