"""Add goal_history table for tracking north star goal changes.

Stores history of goal changes with timestamps for progress tracking.
Shows goal evolution over time and enables staleness prompts.

Revision ID: z30_add_goal_history
Revises: z29_add_trend_summary
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z30_add_goal_history"
down_revision: str | Sequence[str] | None = "z29_add_trend_summary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create goal_history table."""
    op.create_table(
        "goal_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("goal_text", sa.String(200), nullable=False),
        sa.Column("previous_goal", sa.String(200), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Index for efficient history lookups: most recent first
    op.create_index(
        "ix_goal_history_user_changed",
        "goal_history",
        ["user_id", sa.text("changed_at DESC")],
    )


def downgrade() -> None:
    """Drop goal_history table."""
    op.drop_index("ix_goal_history_user_changed", table_name="goal_history")
    op.drop_table("goal_history")
