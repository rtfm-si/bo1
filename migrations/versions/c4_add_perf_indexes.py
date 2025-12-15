"""Add performance indexes for multi-tag filtering and user share queries.

Adds:
- ix_action_tags_action_tag: Composite index on action_tags(action_id, tag_id) for multi-tag filtering
- ix_session_shares_created_by_at: Composite index on session_shares(created_by, created_at) for user-based access

Revision ID: c4_add_perf_indexes
Revises: c3_add_session_recovery_flags
Create Date: 2025-12-14

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4_add_perf_indexes"
down_revision: str | None = "c3_add_session_recovery_flags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add performance indexes."""
    # Composite index on action_tags for multi-tag filtering queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_action_tags_action_tag
        ON action_tags (action_id, tag_id)
    """)

    # Composite index on session_shares for user-based access patterns
    # Supports queries filtering by created_by and ordering by created_at
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_session_shares_created_by_at
        ON session_shares (created_by, created_at)
    """)


def downgrade() -> None:
    """Remove performance indexes."""
    op.execute("DROP INDEX IF EXISTS ix_session_shares_created_by_at")
    op.execute("DROP INDEX IF EXISTS ix_action_tags_action_tag")
