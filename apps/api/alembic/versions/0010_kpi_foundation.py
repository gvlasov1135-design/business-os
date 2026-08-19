"""kpi foundation

Revision ID: 0010_kpi_foundation
Revises: 0009_entity_resolution
Create Date: 2026-08-09 11:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_kpi_foundation"
down_revision: str | None = "0009_entity_resolution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kpi_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("owner_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trust_index", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_kpi_company_code"),
    )
    op.create_index("ix_kpi_definitions_company_id", "kpi_definitions", ["company_id"])

    op.create_table(
        "kpi_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kpi_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("formula", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("formula_text", sa.String(length=500), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["kpi_id"], ["kpi_definitions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kpi_id", "version_number", name="uq_kpi_version_number"),
    )
    op.create_index("ix_kpi_versions_kpi_id", "kpi_versions", ["kpi_id"])
    op.create_index("ix_kpi_versions_company_id", "kpi_versions", ["company_id"])

    op.create_table(
        "kpi_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kpi_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("actual_value", sa.Float(), nullable=True),
        sa.Column("trust_index", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("conflict_flag", sa.Boolean(), nullable=False),
        sa.Column("blocks_analysis", sa.Boolean(), nullable=False),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("lineage", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["kpi_id"], ["kpi_definitions.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["kpi_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kpi_snapshots_kpi_id", "kpi_snapshots", ["kpi_id"])
    op.create_index("ix_kpi_snapshots_version_id", "kpi_snapshots", ["version_id"])
    op.create_index("ix_kpi_snapshots_company_id", "kpi_snapshots", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_kpi_snapshots_company_id", table_name="kpi_snapshots")
    op.drop_index("ix_kpi_snapshots_version_id", table_name="kpi_snapshots")
    op.drop_index("ix_kpi_snapshots_kpi_id", table_name="kpi_snapshots")
    op.drop_table("kpi_snapshots")
    op.drop_index("ix_kpi_versions_company_id", table_name="kpi_versions")
    op.drop_index("ix_kpi_versions_kpi_id", table_name="kpi_versions")
    op.drop_table("kpi_versions")
    op.drop_index("ix_kpi_definitions_company_id", table_name="kpi_definitions")
    op.drop_table("kpi_definitions")
