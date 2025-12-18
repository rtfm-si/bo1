"""Add failure_acknowledged_at column to sessions table.

Enables tracking when a user acknowledges a failed meeting, allowing
actions from that meeting to become visible in their action list.

Revision ID: z11_add_failure_acknowledged
Revises: z10_seed_beta_whitelist
Create Date: 2025-12-18

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z11_add_failure_acknowledged"
down_revision: str | Sequence[str] | None = "z10_seed_beta_whitelist"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add failure_acknowledged_at column to sessions table."""
    # Add failure_acknowledged_at column (nullable timestamp)
    op.execute("""
        ALTER TABLE sessions
        ADD COLUMN IF NOT EXISTS failure_acknowledged_at TIMESTAMPTZ;
    """)

    # Create partial index for efficient filtering of acknowledged failures
    # Only indexes rows where failure_acknowledged_at is NOT NULL
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_failure_acknowledged
        ON sessions (user_id, status, failure_acknowledged_at)
        WHERE failure_acknowledged_at IS NOT NULL;
    """)


def downgrade() -> None:
    """Remove failure_acknowledged_at column from sessions table."""
    op.execute("DROP INDEX IF EXISTS idx_sessions_failure_acknowledged;")
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS failure_acknowledged_at;")
