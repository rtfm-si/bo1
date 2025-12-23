"""Add covering indexes for index-only scans.

Creates covering indexes with INCLUDE clauses for:
- sessions (user_id, created_at) with commonly queried columns
- session_events (session_id, created_at) with event_type and sequence

Revision ID: z15_add_covering_indexes
Revises: z14_recommendations_rls
Create Date: 2025-12-22
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z15_add_covering_indexes"
down_revision: str | Sequence[str] | None = "z14_recommendations_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add covering indexes for index-only scans."""
    # 1. Sessions covering index for list_by_user() queries
    # Drop the old index if it exists (may not exist in all environments)
    op.execute("DROP INDEX IF EXISTS idx_sessions_user_created")

    # Create covering index with commonly queried columns (excludes large TEXT fields)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user_created_covering
        ON sessions (user_id, created_at DESC)
        INCLUDE (id, status, phase, total_cost, round_number, expert_count,
                 contribution_count, focus_area_count, task_count, workspace_id)
    """)

    # 2. Session events covering index for event listing queries
    # Drop the old index if it exists
    op.execute("DROP INDEX IF EXISTS idx_session_events_session_id")

    # Create covering index for partitioned table (includes event_type and sequence)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_session_events_session_created_covering
        ON session_events (session_id, created_at DESC)
        INCLUDE (event_type, sequence)
    """)


def downgrade() -> None:
    """Restore original indexes without INCLUDE clause."""
    # Drop covering indexes
    op.execute("DROP INDEX IF EXISTS idx_sessions_user_created_covering")
    op.execute("DROP INDEX IF EXISTS idx_session_events_session_created_covering")

    # Restore original indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user_created
        ON sessions (user_id, created_at DESC)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_session_events_session_id
        ON session_events (session_id)
    """)
