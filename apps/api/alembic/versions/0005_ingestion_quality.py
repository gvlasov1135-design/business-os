"""ingestion and data quality tables

Revision ID: 0005_ingestion_quality
Revises: 0004_document_intelligence
Create Date: 2026-08-08 16:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_ingestion_quality"
down_revision: str | None = "0004_document_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("freshness_hours", sa.Integer(), server_default="24", nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_sources_company_code"),
    )
    op.create_index("ix_sources_company_id", "sources", ["company_id"], unique=False)

    op.create_table(
        "raw_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "checksum_sha256", name="uq_raw_records_source_checksum"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_raw_records_source_external_id"),
    )
    op.create_index("ix_raw_records_source_id", "raw_records", ["source_id"], unique=False)
    op.create_index("ix_raw_records_company_id", "raw_records", ["company_id"], unique=False)

    op.create_table(
        "observed_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("predicate", sa.String(length=255), nullable=False),
        sa.Column("value_text", sa.String(length=1000), nullable=False),
        sa.Column("value_structured", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trust_index", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("lineage", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["raw_record_id"], ["raw_records.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_observed_facts_company_id", "observed_facts", ["company_id"], unique=False)
    op.create_index("ix_observed_facts_source_id", "observed_facts", ["source_id"], unique=False)
    op.create_index("ix_observed_facts_raw_record_id", "observed_facts", ["raw_record_id"], unique=False)

    op.create_table(
        "data_quality_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("blocks_analysis", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["raw_record_id"], ["raw_records.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_quality_issues_company_id", "data_quality_issues", ["company_id"], unique=False)
    op.create_index("ix_data_quality_issues_raw_record_id", "data_quality_issues", ["raw_record_id"], unique=False)
    op.create_index("ix_data_quality_issues_source_id", "data_quality_issues", ["source_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_data_quality_issues_source_id", table_name="data_quality_issues")
    op.drop_index("ix_data_quality_issues_raw_record_id", table_name="data_quality_issues")
    op.drop_index("ix_data_quality_issues_company_id", table_name="data_quality_issues")
    op.drop_table("data_quality_issues")
    op.drop_index("ix_observed_facts_raw_record_id", table_name="observed_facts")
    op.drop_index("ix_observed_facts_source_id", table_name="observed_facts")
    op.drop_index("ix_observed_facts_company_id", table_name="observed_facts")
    op.drop_table("observed_facts")
    op.drop_index("ix_raw_records_company_id", table_name="raw_records")
    op.drop_index("ix_raw_records_source_id", table_name="raw_records")
    op.drop_table("raw_records")
    op.drop_index("ix_sources_company_id", table_name="sources")
    op.drop_table("sources")
