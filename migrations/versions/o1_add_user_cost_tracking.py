"""Add user cost tracking tables.

Tables for:
- user_cost_periods: Monthly cost aggregates per user
- user_budget_settings: Admin-configured cost limits per user

Revision ID: o1_add_user_cost_tracking
Revises: n1_sessions_cost_idx
Create Date: 2025-12-11
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "o1_add_user_cost_tracking"
down_revision: str | Sequence[str] | None = "n1_sessions_cost_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Monthly cost aggregates per user
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_cost_periods (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id TEXT NOT NULL,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            total_cost_cents INTEGER NOT NULL DEFAULT 0,
            session_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_user_cost_period UNIQUE (user_id, period_start)
        )
    """)

    # Admin-configured cost limits
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_budget_settings (
            user_id TEXT PRIMARY KEY,
            monthly_cost_limit_cents INTEGER,
            alert_threshold_pct INTEGER NOT NULL DEFAULT 80,
            hard_limit_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            alert_sent_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Indexes for efficient queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_cost_periods_user
        ON user_cost_periods (user_id, period_start DESC)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_cost_periods_period
        ON user_cost_periods (period_start, period_end)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS idx_user_cost_periods_period")
    op.execute("DROP INDEX IF EXISTS idx_user_cost_periods_user")
    op.execute("DROP TABLE IF EXISTS user_budget_settings")
    op.execute("DROP TABLE IF EXISTS user_cost_periods")
