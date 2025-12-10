"""Add dataset_id to sessions table.

Allow attaching a dataset to a meeting for data-driven deliberations.

Revision ID: g3_add_dataset_sessions
Revises: g2_create_dataset_analyses
Create Date: 2025-12-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "g3_add_dataset_sessions"
down_revision: str | Sequence[str] | None = "g2_dataset_analyses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add dataset_id column to sessions table."""
    # Add nullable dataset_id column with FK to datasets
    op.add_column(
        "sessions",
        sa.Column("dataset_id", UUID(as_uuid=True), nullable=True),
    )

    # Add foreign key constraint (SET NULL on delete to preserve session if dataset deleted)
    op.create_foreign_key(
        "fk_sessions_dataset_id",
        "sessions",
        "datasets",
        ["dataset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add index for efficient lookups
    op.create_index("ix_sessions_dataset_id", "sessions", ["dataset_id"])


def downgrade() -> None:
    """Remove dataset_id column from sessions table."""
    op.drop_index("ix_sessions_dataset_id", table_name="sessions")
    op.drop_constraint("fk_sessions_dataset_id", "sessions", type_="foreignkey")
    op.drop_column("sessions", "dataset_id")
