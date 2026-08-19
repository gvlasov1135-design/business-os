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
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from infrastructure.db import Base


class FragmentType(str, enum.Enum):
    page = "page"
    section = "section"
    paragraph = "paragraph"


class StatementType(str, enum.Enum):
    obligation = "obligation"
    responsible = "responsible"
    deadline = "deadline"
    kpi = "kpi"
    limit = "limit"
    process_stage = "process_stage"


class StatementStatus(str, enum.Enum):
    proposed = "proposed"
    confirmed = "confirmed"
    rejected = "rejected"


class DocumentFragment(Base):
    __tablename__ = "document_fragments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("document_versions.id"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    fragment_type: Mapped[FragmentType] = mapped_column(
        Enum(FragmentType, name="fragment_type", native_enum=False),
        nullable=False,
        default=FragmentType.paragraph,
    )
    text: Mapped[str] = mapped_column(Text(), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    char_start: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    statements: Mapped[list["ExtractedStatement"]] = relationship(back_populates="fragment")


class ExtractedStatement(Base):
    __tablename__ = "extracted_statements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("document_versions.id"), nullable=False, index=True
    )
    fragment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("document_fragments.id"), nullable=False, index=True
    )
    statement_type: Mapped[StatementType] = mapped_column(
        Enum(StatementType, name="statement_type", native_enum=False),
        nullable=False,
    )
    value_text: Mapped[str] = mapped_column(Text(), nullable=False)
    value_structured: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    confidence: Mapped[float] = mapped_column(Float(), nullable=False, default=0.5)
    status: Mapped[StatementStatus] = mapped_column(
        Enum(StatementStatus, name="statement_status", native_enum=False),
        nullable=False,
        default=StatementStatus.proposed,
    )
    source_anchor: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    fragment: Mapped[DocumentFragment] = relationship(back_populates="statements")
