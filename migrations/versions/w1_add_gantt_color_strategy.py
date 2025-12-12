"""Add gantt_color_strategy column to users table.

Allows users to select preferred Gantt chart color coding strategy.

Revision ID: w1_add_gantt_color_strategy
Revises: v1_add_alert_history
Create Date: 2025-12-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "w1_add_gantt_color_strategy"
down_revision: str | Sequence[str] | None = "v1_add_alert_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add gantt_color_strategy column with default BY_STATUS."""
    op.add_column(
        "users",
        sa.Column(
            "gantt_color_strategy",
            sa.String(20),
            nullable=False,
            server_default="BY_STATUS",
        ),
    )


def downgrade() -> None:
    """Remove gantt_color_strategy column."""
    op.drop_column("users", "gantt_color_strategy")
