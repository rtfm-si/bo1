"""Add composite index on session_events(session_id, sequence) for event ordering.

Revision ID: c1_events_seq_idx
Revises: b3_user_id_fac_decisions
Create Date: 2025-12-09

Optimizes ORDER BY sequence queries used by get_events() in session_repository.
Performance improvement: ~O(n log n) to ~O(log n) for ordered event retrieval.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1_events_seq_idx"
down_revision: str | Sequence[str] | None = "b3_user_id_fac_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add composite index for session_id + sequence ordering."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'session_events') THEN
                CREATE INDEX IF NOT EXISTS idx_session_events_session_sequence
                ON session_events (session_id, sequence);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Remove the composite index."""
    op.execute("DROP INDEX IF EXISTS idx_session_events_session_sequence")
