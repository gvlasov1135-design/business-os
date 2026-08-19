"""alignment, knowledge, analysis, decisions tables

Revision ID: 0006_align_knowledge_ai
Revises: 0005_ingestion_quality
Create Date: 2026-08-08 16:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_align_knowledge_ai"
down_revision: str | None = "0005_ingestion_quality"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alignment_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("rule_code", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alignment_checks_company_id", "alignment_checks", ["company_id"], unique=False)

    op.create_table(
        "alignment_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("statement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("normative_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("actual_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("deviation_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("trust_index", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["check_id"], ["alignment_checks.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["statement_id"], ["extracted_statements.id"]),
        sa.ForeignKeyConstraint(["fact_id"], ["observed_facts.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alignment_issues_check_id", "alignment_issues", ["check_id"], unique=False)
    op.create_index("ix_alignment_issues_company_id", "alignment_issues", ["company_id"], unique=False)
    op.create_index("ix_alignment_issues_document_id", "alignment_issues", ["document_id"], unique=False)
    op.create_index("ix_alignment_issues_statement_id", "alignment_issues", ["statement_id"], unique=False)
    op.create_index("ix_alignment_issues_fact_id", "alignment_issues", ["fact_id"], unique=False)

    op.create_table(
        "knowledge_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("record_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("trust_index", sa.Float(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("alignment_issue_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("statement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["alignment_issue_id"], ["alignment_issues.id"]),
        sa.ForeignKeyConstraint(["statement_id"], ["extracted_statements.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_records_company_id", "knowledge_records", ["company_id"], unique=False)
    op.create_index(
        "ix_knowledge_records_alignment_issue_id", "knowledge_records", ["alignment_issue_id"], unique=False
    )
    op.create_index("ix_knowledge_records_statement_id", "knowledge_records", ["statement_id"], unique=False)

    op.create_table(
        "ai_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("blocked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("block_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("context_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("trust_index", sa.Float(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_analyses_company_id", "ai_analyses", ["company_id"], unique=False)

    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["ai_analyses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendations_analysis_id", "recommendations", ["analysis_id"], unique=False)

    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("owner_name", sa.String(length=255), nullable=False),
        sa.Column("checkpoint_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_result", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["analysis_id"], ["ai_analyses.id"]),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decisions_company_id", "decisions", ["company_id"], unique=False)
    op.create_index("ix_decisions_analysis_id", "decisions", ["analysis_id"], unique=False)
    op.create_index("ix_decisions_recommendation_id", "decisions", ["recommendation_id"], unique=False)

    op.create_table(
        "decision_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actual_result", sa.Text(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("deviation_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("decision_id"),
    )
    op.create_index("ix_decision_results_decision_id", "decision_results", ["decision_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_decision_results_decision_id", table_name="decision_results")
    op.drop_table("decision_results")
    op.drop_index("ix_decisions_recommendation_id", table_name="decisions")
    op.drop_index("ix_decisions_analysis_id", table_name="decisions")
    op.drop_index("ix_decisions_company_id", table_name="decisions")
    op.drop_table("decisions")
    op.drop_index("ix_recommendations_analysis_id", table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_index("ix_ai_analyses_company_id", table_name="ai_analyses")
    op.drop_table("ai_analyses")
    op.drop_index("ix_knowledge_records_statement_id", table_name="knowledge_records")
    op.drop_index("ix_knowledge_records_alignment_issue_id", table_name="knowledge_records")
    op.drop_index("ix_knowledge_records_company_id", table_name="knowledge_records")
    op.drop_table("knowledge_records")
    op.drop_index("ix_alignment_issues_fact_id", table_name="alignment_issues")
    op.drop_index("ix_alignment_issues_statement_id", table_name="alignment_issues")
    op.drop_index("ix_alignment_issues_document_id", table_name="alignment_issues")
    op.drop_index("ix_alignment_issues_company_id", table_name="alignment_issues")
    op.drop_index("ix_alignment_issues_check_id", table_name="alignment_issues")
    op.drop_table("alignment_issues")
    op.drop_index("ix_alignment_checks_company_id", table_name="alignment_checks")
    op.drop_table("alignment_checks")
