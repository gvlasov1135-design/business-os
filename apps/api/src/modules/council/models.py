import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from infrastructure.db import Base


class CouncilSessionStatus(str, enum.Enum):
    open = "open"
    closed = "closed"


class CouncilChannel(str, enum.Enum):
    table = "table"
    private = "private"


class CouncilMessageRole(str, enum.Enum):
    user = "user"
    agent = "agent"
    system = "system"


class CouncilAgent(str, enum.Enum):
    executive = "executive"
    sales = "sales"
    critic = "critic"
    data_doctor = "data_doctor"


class CouncilSession(Base):
    __tablename__ = "council_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_analyses.id"), nullable=True, index=True
    )
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[CouncilSessionStatus] = mapped_column(
        Enum(CouncilSessionStatus, name="council_session_status", native_enum=False),
        nullable=False,
        default=CouncilSessionStatus.open,
    )
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CouncilMessage(Base):
    __tablename__ = "council_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("council_sessions.id"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    channel: Mapped[CouncilChannel] = mapped_column(
        Enum(CouncilChannel, name="council_channel", native_enum=False),
        nullable=False,
    )
    role: Mapped[CouncilMessageRole] = mapped_column(
        Enum(CouncilMessageRole, name="council_message_role", native_enum=False),
        nullable=False,
    )
    agent: Mapped[CouncilAgent | None] = mapped_column(
        Enum(CouncilAgent, name="council_agent", native_enum=False),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
