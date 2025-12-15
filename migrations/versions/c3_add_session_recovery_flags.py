"""Add recovery flags to sessions for crash recovery and cost tracking resilience.

Adds:
- has_untracked_costs: True when cost inserts failed (retry queue active)
- recovery_needed: True when in-flight contributions exist

Revision ID: c3_add_session_recovery_flags
Revises: c2_add_contribution_status
Create Date: 2025-12-14

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3_add_session_recovery_flags"
down_revision: str | None = "c2_add_contribution_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add recovery flags to sessions table."""
    # Add has_untracked_costs flag
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sessions' AND column_name = 'has_untracked_costs'
            ) THEN
                ALTER TABLE sessions ADD COLUMN has_untracked_costs BOOLEAN DEFAULT FALSE;
            END IF;
        END $$;
    """)

    # Add recovery_needed flag
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sessions' AND column_name = 'recovery_needed'
            ) THEN
                ALTER TABLE sessions ADD COLUMN recovery_needed BOOLEAN DEFAULT FALSE;
            END IF;
        END $$;
    """)

    # Create partial index for sessions needing recovery (fast lookup)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_recovery_needed
        ON sessions (id)
        WHERE recovery_needed = TRUE
    """)

    # Create partial index for sessions with untracked costs
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_has_untracked_costs
        ON sessions (id)
        WHERE has_untracked_costs = TRUE
    """)


def downgrade() -> None:
    """Remove recovery flags from sessions table."""
    op.execute("DROP INDEX IF EXISTS idx_sessions_has_untracked_costs")
    op.execute("DROP INDEX IF EXISTS idx_sessions_recovery_needed")
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS recovery_needed")
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS has_untracked_costs")
