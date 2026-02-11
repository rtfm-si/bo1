"""Backfill sessions.task_count from top-level actions.

Revision ID: zzzj_backfill_task_count
Revises: zzzi_add_action_hierarchy
Create Date: 2026-02-11

Sets task_count to number of top-level actions (parent_action_id IS NULL)
instead of total tasks + parents.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "zzzj_backfill_task_count"
down_revision: str = "zzzi_add_action_hierarchy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill task_count with top-level action count."""
    op.execute("""
        UPDATE sessions s
        SET task_count = sub.cnt
        FROM (
            SELECT source_session_id, COUNT(*) as cnt
            FROM actions
            WHERE parent_action_id IS NULL AND deleted_at IS NULL
            GROUP BY source_session_id
        ) sub
        WHERE s.id = sub.source_session_id;
    """)


def downgrade() -> None:
    """No-op: previous task_count values were incorrect."""
    pass
