"""Add sessions indexes for cost analytics.

Optimizes cost analytics queries:
- sessions(created_at DESC) - for daily/time-based cost aggregation
- sessions(user_id, created_at DESC) - for per-user cost analytics

Revision ID: n1_add_sessions_cost_analytics_indexes
Revises: m1_add_session_kills
Create Date: 2025-12-11
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n1_sessions_cost_idx"
down_revision: str | Sequence[str] | None = "m1_add_session_kills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Index for time-based queries (daily cost aggregation)
    # Used by: get_daily_costs(), get_cost_summary()
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_created_at
        ON sessions (created_at DESC)
    """)

    # Composite index for user cost analytics
    # Used by: get_user_costs()
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user_created
        ON sessions (user_id, created_at DESC)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS idx_sessions_user_created")
    op.execute("DROP INDEX IF EXISTS idx_sessions_created_at")
