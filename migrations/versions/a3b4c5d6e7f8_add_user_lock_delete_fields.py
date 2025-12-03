"""Add user lock and soft delete fields.

Revision ID: a3b4c5d6e7f8
Revises: f29ed88cde9d
Create Date: 2025-12-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: str | Sequence[str] | None = "0eb64c2f78e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add lock and soft delete columns to users table."""
    # Add lock-related columns
    op.add_column(
        "users",
        sa.Column("is_locked", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("locked_by", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("lock_reason", sa.String(length=500), nullable=True),
    )

    # Add soft delete columns
    op.add_column(
        "users",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("deleted_by", sa.String(length=255), nullable=True),
    )

    # Add indexes for efficient queries
    op.create_index("idx_users_is_locked", "users", ["is_locked"])
    op.create_index("idx_users_deleted_at", "users", ["deleted_at"])


def downgrade() -> None:
    """Remove lock and soft delete columns from users table."""
    op.drop_index("idx_users_deleted_at")
    op.drop_index("idx_users_is_locked")
    op.drop_column("users", "deleted_by")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "lock_reason")
    op.drop_column("users", "locked_by")
    op.drop_column("users", "locked_at")
    op.drop_column("users", "is_locked")
