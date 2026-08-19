"""knowledge relations + search

Revision ID: 0008_knowledge_relations
Revises: 0007_user_password
Create Date: 2026-08-08 17:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_knowledge_relations"
down_revision: str | None = "0007_user_password"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["from_record_id"], ["knowledge_records.id"]),
        sa.ForeignKeyConstraint(["to_record_id"], ["knowledge_records.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_record_id", "to_record_id", "relation_type", name="uq_knowledge_relation_edge"),
    )
    op.create_index("ix_knowledge_relations_company_id", "knowledge_relations", ["company_id"])
    op.create_index("ix_knowledge_relations_from_record_id", "knowledge_relations", ["from_record_id"])
    op.create_index("ix_knowledge_relations_to_record_id", "knowledge_relations", ["to_record_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_relations_to_record_id", table_name="knowledge_relations")
    op.drop_index("ix_knowledge_relations_from_record_id", table_name="knowledge_relations")
    op.drop_index("ix_knowledge_relations_company_id", table_name="knowledge_relations")
    op.drop_table("knowledge_relations")
