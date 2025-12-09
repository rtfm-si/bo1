"""add clarifications column to user_context

Revision ID: e1_add_clarifications
Revises: d1_add_session_counts
Create Date: 2025-12-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "e1_add_clarifications"
down_revision: str | Sequence[str] | None = "d1_add_session_counts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add clarifications JSONB column to user_context."""
    op.add_column(
        "user_context",
        sa.Column("clarifications", JSONB, server_default="{}", nullable=True),
    )


def downgrade() -> None:
    """Remove clarifications column."""
    op.drop_column("user_context", "clarifications")
