"""entity resolution

Revision ID: 0009_entity_resolution
Revises: 0008_knowledge_relations
Create Date: 2026-08-08 17:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_entity_resolution"
down_revision: str | None = "0008_knowledge_relations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canonical_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=500), nullable=False),
        sa.Column("trust_index", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_canonical_entities_company_id", "canonical_entities", ["company_id"])

    op.create_table(
        "entity_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("match_method", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["entity_id"], ["canonical_entities.id"]),
        sa.ForeignKeyConstraint(["raw_record_id"], ["raw_records.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_record_id", name="uq_entity_membership_raw_record"),
    )
    op.create_index("ix_entity_memberships_company_id", "entity_memberships", ["company_id"])
    op.create_index("ix_entity_memberships_entity_id", "entity_memberships", ["entity_id"])
    op.create_index("ix_entity_memberships_raw_record_id", "entity_memberships", ["raw_record_id"])
    op.create_index("ix_entity_memberships_source_id", "entity_memberships", ["source_id"])

    op.create_table(
        "entity_match_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("left_raw_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("right_raw_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposed_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("match_method", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("match_key", sa.String(length=255), nullable=False),
        sa.Column("match_value", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("requires_confirmation", sa.Boolean(), nullable=False),
        sa.Column("blocks_analysis", sa.Boolean(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["left_raw_record_id"], ["raw_records.id"]),
        sa.ForeignKeyConstraint(["proposed_entity_id"], ["canonical_entities.id"]),
        sa.ForeignKeyConstraint(["right_raw_record_id"], ["raw_records.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "left_raw_record_id",
            "right_raw_record_id",
            "match_method",
            name="uq_entity_match_pair",
        ),
    )
    op.create_index("ix_entity_match_candidates_company_id", "entity_match_candidates", ["company_id"])
    op.create_index(
        "ix_entity_match_candidates_left_raw_record_id",
        "entity_match_candidates",
        ["left_raw_record_id"],
    )
    op.create_index(
        "ix_entity_match_candidates_right_raw_record_id",
        "entity_match_candidates",
        ["right_raw_record_id"],
    )
    op.create_index(
        "ix_entity_match_candidates_proposed_entity_id",
        "entity_match_candidates",
        ["proposed_entity_id"],
    )

    op.create_table(
        "entity_merge_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["entity_match_candidates.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["entity_id"], ["canonical_entities.id"]),
        sa.ForeignKeyConstraint(["raw_record_id"], ["raw_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entity_merge_events_company_id", "entity_merge_events", ["company_id"])
    op.create_index("ix_entity_merge_events_entity_id", "entity_merge_events", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_entity_merge_events_entity_id", table_name="entity_merge_events")
    op.drop_index("ix_entity_merge_events_company_id", table_name="entity_merge_events")
    op.drop_table("entity_merge_events")
    op.drop_index("ix_entity_match_candidates_proposed_entity_id", table_name="entity_match_candidates")
    op.drop_index("ix_entity_match_candidates_right_raw_record_id", table_name="entity_match_candidates")
    op.drop_index("ix_entity_match_candidates_left_raw_record_id", table_name="entity_match_candidates")
    op.drop_index("ix_entity_match_candidates_company_id", table_name="entity_match_candidates")
    op.drop_table("entity_match_candidates")
    op.drop_index("ix_entity_memberships_source_id", table_name="entity_memberships")
    op.drop_index("ix_entity_memberships_raw_record_id", table_name="entity_memberships")
    op.drop_index("ix_entity_memberships_entity_id", table_name="entity_memberships")
    op.drop_index("ix_entity_memberships_company_id", table_name="entity_memberships")
    op.drop_table("entity_memberships")
    op.drop_index("ix_canonical_entities_company_id", table_name="canonical_entities")
    op.drop_table("canonical_entities")
