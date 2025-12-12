"""Add workspace_id FK to datasets table.

Revision ID: aa3_add_workspace_to_datasets
Revises: aa2_add_workspace_to_sessions
Create Date: 2025-12-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa3_add_workspace_to_datasets"
down_revision: str | Sequence[str] | None = "aa2_add_workspace_to_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable workspace_id column to datasets table."""
    op.add_column(
        "datasets",
        sa.Column(
            "workspace_id",
            sa.UUID(),
            sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
            nullable=True,
            comment="Workspace this dataset belongs to (NULL for personal datasets)",
        ),
    )

    # Index for workspace filtering
    op.create_index(
        "ix_datasets_workspace_id",
        "datasets",
        ["workspace_id"],
    )


def downgrade() -> None:
    """Remove workspace_id column from datasets table."""
    op.drop_index("ix_datasets_workspace_id", table_name="datasets")
    op.drop_column("datasets", "workspace_id")
