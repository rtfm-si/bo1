"""Add deleted_at column to projects table for soft-delete tracking.

Enables counting soft-deleted projects in admin extended KPIs.

Revision ID: z31_add_projects_soft_delete
Revises: z30_add_goal_history
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z31_add_projects_soft_delete"
down_revision: str | Sequence[str] | None = "z30_add_goal_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add deleted_at column to projects table."""
    op.add_column(
        "projects",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Partial index for efficient queries on non-deleted projects
    op.create_index(
        "ix_projects_not_deleted",
        "projects",
        ["user_id", "workspace_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Remove deleted_at column from projects table."""
    op.drop_index("ix_projects_not_deleted", table_name="projects")
    op.drop_column("projects", "deleted_at")
