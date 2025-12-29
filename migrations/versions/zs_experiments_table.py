"""Create experiments table for A/B testing.

Tracks experiment definitions with variants, metrics, and status lifecycle.

Revision ID: zs_experiments_table
Revises: zr_add_cost_category
Create Date: 2025-12-29
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers
revision: str = "zs_experiments_table"
down_revision: str = "zr_add_cost_category"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create experiments table."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'paused', 'concluded')),
            variants JSONB NOT NULL DEFAULT '[{"name": "control", "weight": 50}, {"name": "treatment", "weight": 50}]'::jsonb,
            metrics JSONB NOT NULL DEFAULT '[]'::jsonb,
            start_date TIMESTAMPTZ,
            end_date TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Index for status filtering
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_experiments_status
        ON experiments (status)
    """)

    # Index for name lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_experiments_name
        ON experiments (name)
    """)


def downgrade() -> None:
    """Drop experiments table."""
    op.execute("DROP INDEX IF EXISTS idx_experiments_name")
    op.execute("DROP INDEX IF EXISTS idx_experiments_status")
    op.execute("DROP TABLE IF EXISTS experiments")
