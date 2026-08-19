"""agent opinions

Revision ID: 0011_agent_opinions
Revises: 0010_kpi_foundation
Create Date: 2026-08-09 11:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_agent_opinions"
down_revision: str | None = "0010_kpi_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_opinions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent", sa.String(length=50), nullable=False),
        sa.Column("decision_dna", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("opinion", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("missing_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trust_index", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["ai_analyses.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_opinions_analysis_id", "agent_opinions", ["analysis_id"])
    op.create_index("ix_agent_opinions_company_id", "agent_opinions", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_opinions_company_id", table_name="agent_opinions")
    op.drop_index("ix_agent_opinions_analysis_id", table_name="agent_opinions")
    op.drop_table("agent_opinions")
