"""Add task status tracking to session_tasks.

Enables Kanban-style task management with todo/doing/done states.
Adds task_statuses JSONB column to track individual task statuses.

Revision ID: b1c2d3e4f5g6
Revises: a3b4c5d6e7f8
Create Date: 2025-12-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5g6"
down_revision: str | Sequence[str] | None = "a3b4c5d6e7f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add task_statuses column to session_tasks for Kanban tracking."""
    # Add task_statuses JSONB column
    # Format: {"task_1": "todo", "task_2": "doing", "task_3": "done"}
    op.add_column(
        "session_tasks",
        sa.Column(
            "task_statuses",
            JSONB,
            nullable=False,
            server_default="{}",
            comment="Per-task status tracking: {task_id: 'todo'|'doing'|'done'}",
        ),
    )

    # Add GIN index for efficient JSONB queries on task_statuses
    op.create_index(
        "idx_session_tasks_statuses",
        "session_tasks",
        ["task_statuses"],
        postgresql_using="gin",
    )

    # Add column comment
    op.execute("""
        COMMENT ON COLUMN session_tasks.task_statuses IS
        'Per-task status tracking as JSONB object. Keys are task IDs (e.g., "task_1"), values are status strings ("todo", "doing", "done"). Default status for new tasks is "todo".';
    """)


def downgrade() -> None:
    """Remove task_statuses column."""
    op.drop_index("idx_session_tasks_statuses", table_name="session_tasks")
    op.drop_column("session_tasks", "task_statuses")
