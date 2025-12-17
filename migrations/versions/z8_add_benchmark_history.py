"""Add benchmark_history to user_context.

Stores up to 6 monthly historical values per benchmark metric.
Schema: { "metric_key": [{ "value": X, "date": "YYYY-MM-DD" }, ...] }

Revision ID: z8_add_benchmark_history
Revises: z7_add_cost_tracking
Create Date: 2025-12-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "z8_add_benchmark_history"
down_revision: str | Sequence[str] | None = "z7_add_cost_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add benchmark_history JSONB column to user_context."""
    op.add_column(
        "user_context",
        sa.Column(
            "benchmark_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
            comment="Historical benchmark values: {metric_key: [{value, date}, ...]} max 6 per metric",
        ),
    )


def downgrade() -> None:
    """Remove benchmark_history column."""
    op.drop_column("user_context", "benchmark_history")
