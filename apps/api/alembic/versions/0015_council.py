"""council sessions

Revision ID: 0015_council
Revises: 0014_versioned_rules
Create Date: 2026-08-09 16:50:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_council"
down_revision: str | None = "0014_versioned_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "council_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("topic", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("context_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["ai_analyses.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_council_sessions_company_id", "council_sessions", ["company_id"])
    op.create_index("ix_council_sessions_analysis_id", "council_sessions", ["analysis_id"])

    op.create_table(
        "council_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("agent", sa.String(length=50), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["council_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_council_messages_session_id", "council_messages", ["session_id"])
    op.create_index("ix_council_messages_company_id", "council_messages", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_council_messages_company_id", table_name="council_messages")
    op.drop_index("ix_council_messages_session_id", table_name="council_messages")
    op.drop_table("council_messages")
    op.drop_index("ix_council_sessions_analysis_id", table_name="council_sessions")
    op.drop_index("ix_council_sessions_company_id", table_name="council_sessions")
    op.drop_table("council_sessions")
