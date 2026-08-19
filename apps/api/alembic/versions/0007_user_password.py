"""user password hash

Revision ID: 0007_user_password
Revises: 0006_align_knowledge_ai
Create Date: 2026-08-08 17:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_user_password"
down_revision: str | None = "0006_align_knowledge_ai"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
