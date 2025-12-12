"""Add skip_clarification column to users table.

Allows users to skip pre-meeting clarifying questions by default.

Revision ID: t1_add_skip_clarification
Revises: 55f7196a2e5d
Create Date: 2025-12-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "t1_add_skip_clarification"
down_revision: str | Sequence[str] | None = "55f7196a2e5d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add skip_clarification column with default FALSE."""
    op.add_column(
        "users",
        sa.Column(
            "skip_clarification",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    """Remove skip_clarification column."""
    op.drop_column("users", "skip_clarification")
