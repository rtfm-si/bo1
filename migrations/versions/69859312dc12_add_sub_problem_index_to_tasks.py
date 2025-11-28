"""add_sub_problem_index_to_tasks

Revision ID: 69859312dc12
Revises: 80cf34f1b577
Create Date: 2025-11-28 17:05:59.491113

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "69859312dc12"
down_revision: str | Sequence[str] | None = "80cf34f1b577"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add sub_problem_index column to session_tasks table
    op.add_column(
        "session_tasks",
        sa.Column("sub_problem_index", sa.Integer(), nullable=True),
    )
    # Create index for efficient filtering by sub_problem_index
    op.create_index(
        "ix_session_tasks_sub_problem_index",
        "session_tasks",
        ["sub_problem_index"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index first
    op.drop_index("ix_session_tasks_sub_problem_index", "session_tasks")
    # Drop column
    op.drop_column("session_tasks", "sub_problem_index")
