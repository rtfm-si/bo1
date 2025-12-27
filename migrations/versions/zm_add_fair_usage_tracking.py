"""Add fair usage tracking for variable-cost features.

Revision ID: zm_add_fair_usage_tracking
Revises: zl_add_marketing_assets
Create Date: 2025-12-27
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "zm_add_fair_usage_tracking"
down_revision: str | Sequence[str] | None = "zl_add_marketing_assets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add feature column to api_costs and create daily_user_feature_costs view.

    Changes:
    1. Add 'feature' column to api_costs (nullable, for backward compat)
    2. Create daily_user_feature_costs materialized view for fast per-user queries
    3. Add index on api_costs(user_id, feature, created_at) for aggregation
    """
    # Add feature column to api_costs (nullable for existing rows)
    op.execute("""
        ALTER TABLE api_costs
        ADD COLUMN IF NOT EXISTS feature VARCHAR(50);
    """)

    # Add index for fair usage queries (user + feature + date range)
    # Use IF NOT EXISTS since partitioned tables need special handling
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_costs_user_feature_date
        ON api_costs (user_id, feature, created_at DESC)
        WHERE user_id IS NOT NULL AND feature IS NOT NULL;
    """)

    # Create daily_user_feature_costs table for pre-aggregated daily totals
    # This is a regular table that we'll update via trigger/job, not a materialized view
    # (partitioned tables don't support materialized views well)
    op.execute("""
        CREATE TABLE IF NOT EXISTS daily_user_feature_costs (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            feature VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            total_cost NUMERIC(10, 6) NOT NULL DEFAULT 0,
            request_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (user_id, feature, date)
        );
    """)

    # Index for user lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_user_feature_user_date
        ON daily_user_feature_costs (user_id, date DESC);
    """)

    # Index for p90 calculations across all users for a feature
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_user_feature_feature_date
        ON daily_user_feature_costs (feature, date DESC);
    """)

    # Create function to upsert daily costs (called when api_costs inserted)
    op.execute("""
        CREATE OR REPLACE FUNCTION upsert_daily_user_feature_cost()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.user_id IS NOT NULL AND NEW.feature IS NOT NULL THEN
                INSERT INTO daily_user_feature_costs (user_id, feature, date, total_cost, request_count)
                VALUES (NEW.user_id, NEW.feature, DATE(NEW.created_at), NEW.total_cost, 1)
                ON CONFLICT (user_id, feature, date)
                DO UPDATE SET
                    total_cost = daily_user_feature_costs.total_cost + EXCLUDED.total_cost,
                    request_count = daily_user_feature_costs.request_count + 1,
                    updated_at = NOW();
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Note: Trigger on partitioned table requires PostgreSQL 11+
    # We'll handle this in the application layer instead to avoid partition issues


def downgrade() -> None:
    """Remove fair usage tracking."""
    op.execute("DROP FUNCTION IF EXISTS upsert_daily_user_feature_cost CASCADE;")
    op.execute("DROP TABLE IF EXISTS daily_user_feature_costs;")
    op.execute("DROP INDEX IF EXISTS idx_api_costs_user_feature_date;")
    op.execute("ALTER TABLE api_costs DROP COLUMN IF EXISTS feature;")
