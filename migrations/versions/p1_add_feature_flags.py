"""Add feature flags tables.

Tables for:
- feature_flags: Flag definitions with rollout settings
- feature_flag_overrides: Per-user flag overrides

Revision ID: p1_add_feature_flags
Revises: o1_add_user_cost_tracking
Create Date: 2025-12-11
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "p1_add_feature_flags"
down_revision: str | Sequence[str] | None = "o1_add_user_cost_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Feature flag definitions
    op.execute("""
        CREATE TABLE IF NOT EXISTS feature_flags (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            enabled BOOLEAN NOT NULL DEFAULT FALSE,
            rollout_pct INTEGER NOT NULL DEFAULT 100 CHECK (rollout_pct >= 0 AND rollout_pct <= 100),
            tiers JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Per-user flag overrides
    op.execute("""
        CREATE TABLE IF NOT EXISTS feature_flag_overrides (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            flag_id UUID NOT NULL REFERENCES feature_flags(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL,
            enabled BOOLEAN NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_flag_user_override UNIQUE (flag_id, user_id)
        )
    """)

    # Index for fast override lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_feature_flag_overrides_user
        ON feature_flag_overrides (user_id)
    """)

    # Index for flag name lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_feature_flags_name
        ON feature_flags (name)
    """)

    # Seed initial feature flags
    op.execute("""
        INSERT INTO feature_flags (name, description, enabled, rollout_pct, tiers)
        VALUES
            ('datasets', 'Data analysis feature', TRUE, 100, '["starter", "pro"]'::jsonb),
            ('mentor_chat', 'AI mentor chat feature', FALSE, 100, '["pro"]'::jsonb),
            ('api_access', 'External API access', TRUE, 100, '["pro"]'::jsonb)
        ON CONFLICT (name) DO NOTHING
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS idx_feature_flags_name")
    op.execute("DROP INDEX IF EXISTS idx_feature_flag_overrides_user")
    op.execute("DROP TABLE IF EXISTS feature_flag_overrides")
    op.execute("DROP TABLE IF EXISTS feature_flags")
