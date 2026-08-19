"""decision memory tasks lessons review

Revision ID: 0013_decision_memory
Revises: 0012_executive_outbox
Create Date: 2026-08-09 11:50:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_decision_memory"
down_revision: str | None = "0012_executive_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("decisions", sa.Column("selected_option", sa.String(length=500), nullable=True))
    op.add_column("decision_results", sa.Column("review_notes", sa.Text(), nullable=True))
    op.add_column("decision_results", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "decision_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("assignee_name", sa.String(length=255), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_tasks_decision_id", "decision_tasks", ["decision_id"])
    op.create_index("ix_decision_tasks_company_id", "decision_tasks", ["company_id"])

    op.create_table(
        "decision_lessons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_lessons_decision_id", "decision_lessons", ["decision_id"])
    op.create_index("ix_decision_lessons_company_id", "decision_lessons", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_decision_lessons_company_id", table_name="decision_lessons")
    op.drop_index("ix_decision_lessons_decision_id", table_name="decision_lessons")
    op.drop_table("decision_lessons")
    op.drop_index("ix_decision_tasks_company_id", table_name="decision_tasks")
    op.drop_index("ix_decision_tasks_decision_id", table_name="decision_tasks")
    op.drop_table("decision_tasks")
    op.drop_column("decision_results", "reviewed_at")
    op.drop_column("decision_results", "review_notes")
    op.drop_column("decisions", "selected_option")
