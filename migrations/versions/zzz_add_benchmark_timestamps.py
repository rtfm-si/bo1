"""Add benchmark_timestamps to user_context.

Stores last-updated timestamps for each benchmark metric.
Schema: { "metric_key": "2025-01-15T12:00:00Z", ... }

This column was referenced in code but never migrated.

Revision ID: zzz_add_benchmark_timestamps
Revises: zzy_published_decisions
Create Date: 2026-02-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "zzz_add_benchmark_timestamps"
down_revision: str | Sequence[str] | None = "zzy_published_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add benchmark_timestamps JSONB column to user_context."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'user_context' AND column_name = 'benchmark_timestamps'"
        )
    )
    if result.fetchone() is None:
        op.add_column(
            "user_context",
            sa.Column(
                "benchmark_timestamps",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
                server_default="{}",
                comment="Last-updated timestamps for each benchmark metric: {metric_key: ISO8601}",
            ),
        )


def downgrade() -> None:
    """Remove benchmark_timestamps column."""
    op.drop_column("user_context", "benchmark_timestamps")
