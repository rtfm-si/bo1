"""Add kanban_columns preference to users table.

This migration adds a JSONB column for user-defined kanban columns.
NULL = use default 3-column layout (todo, in_progress, done).

Revision ID: z5_add_kanban_columns
Revises: z4_add_action_close_replan
Create Date: 2025-12-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "z5_add_kanban_columns"
down_revision: str | Sequence[str] | None = "z4_add_action_close_replan"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add kanban_columns JSONB column to users table."""
    op.add_column(
        "users",
        sa.Column(
            "kanban_columns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="User-defined kanban columns config (null = default 3 columns)",
        ),
    )


def downgrade() -> None:
    """Remove kanban_columns column from users table."""
    op.drop_column("users", "kanban_columns")
