"""Add workspace_id FK to sessions table.

Revision ID: aa2_add_workspace_to_sessions
Revises: aa1_create_workspaces
Create Date: 2025-12-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa2_add_workspace_to_sessions"
down_revision: str | Sequence[str] | None = "aa1_create_workspaces"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable workspace_id column to sessions table."""
    op.add_column(
        "sessions",
        sa.Column(
            "workspace_id",
            sa.UUID(),
            sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
            nullable=True,
            comment="Workspace this session belongs to (NULL for personal sessions)",
        ),
    )

    # Index for workspace filtering
    op.create_index(
        "ix_sessions_workspace_id",
        "sessions",
        ["workspace_id"],
    )


def downgrade() -> None:
    """Remove workspace_id column from sessions table."""
    op.drop_index("ix_sessions_workspace_id", table_name="sessions")
    op.drop_column("sessions", "workspace_id")
