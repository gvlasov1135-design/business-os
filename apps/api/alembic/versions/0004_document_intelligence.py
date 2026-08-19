"""document intelligence tables

Revision ID: 0004_document_intelligence
Revises: 0003_documents
Create Date: 2026-08-08 16:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_document_intelligence"
down_revision: str | None = "0003_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_fragments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("fragment_type", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["version_id"], ["document_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_fragments_version_id", "document_fragments", ["version_id"], unique=False)

    op.create_table(
        "extracted_statements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fragment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("statement_type", sa.String(length=32), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=False),
        sa.Column("value_structured", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_anchor", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["fragment_id"], ["document_fragments.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["document_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_extracted_statements_document_id", "extracted_statements", ["document_id"], unique=False)
    op.create_index("ix_extracted_statements_version_id", "extracted_statements", ["version_id"], unique=False)
    op.create_index("ix_extracted_statements_fragment_id", "extracted_statements", ["fragment_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_extracted_statements_fragment_id", table_name="extracted_statements")
    op.drop_index("ix_extracted_statements_version_id", table_name="extracted_statements")
    op.drop_index("ix_extracted_statements_document_id", table_name="extracted_statements")
    op.drop_table("extracted_statements")
    op.drop_index("ix_document_fragments_version_id", table_name="document_fragments")
    op.drop_table("document_fragments")
