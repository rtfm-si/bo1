"""Add storage_path to datasets table for workspace/user organization.

This migration adds a storage_path column to store the prefix path for files
in Spaces (e.g., "workspace_id/user_id"), allowing backward-compatible reads
of old uploads without a prefix.

Revision ID: z1_add_storage_path
Revises: j1_add_dataset_clarifications
Create Date: 2025-12-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z1_add_storage_path"
down_revision: str | Sequence[str] | None = "y1_add_insight_timestamps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add storage_path column to datasets table."""
    op.add_column(
        "datasets",
        sa.Column(
            "storage_path",
            sa.String(length=500),
            nullable=True,
            comment="Prefix path for file in Spaces (e.g., user_id, workspace_id/user_id)",
        ),
    )


def downgrade() -> None:
    """Remove storage_path column from datasets table."""
    op.drop_column("datasets", "storage_path")
