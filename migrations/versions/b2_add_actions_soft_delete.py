"""Add soft delete support to actions table.

Adds deleted_at column for soft delete functionality.
Regular users won't see deleted actions; admins can view all.

Revision ID: b2_add_actions_soft_delete
Revises: b1_add_final_rec
Create Date: 2025-12-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2_add_actions_soft_delete"
down_revision: str | Sequence[str] | None = "b1_add_final_rec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add deleted_at column for soft delete support."""
    # Add deleted_at column
    op.add_column(
        "actions",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when action was soft-deleted (NULL = not deleted)",
        ),
    )

    # Add index for efficient filtering of non-deleted actions
    op.create_index(
        "idx_actions_deleted_at",
        "actions",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Add composite index for common query: user's non-deleted actions
    op.create_index(
        "idx_actions_user_not_deleted",
        "actions",
        ["user_id", "deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Add comment
    op.execute("""
        COMMENT ON COLUMN actions.deleted_at IS 'Soft delete timestamp. NULL means not deleted. Admins can view deleted actions.';
    """)


def downgrade() -> None:
    """Remove soft delete support."""
    op.drop_index("idx_actions_user_not_deleted", table_name="actions")
    op.drop_index("idx_actions_deleted_at", table_name="actions")
    op.drop_column("actions", "deleted_at")
