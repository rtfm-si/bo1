"""Add default_workspace_id to users table.

Supports auto-creation of personal workspace on signup.
Users can have a default workspace that's used when no workspace is selected.

Revision ID: as1_add_default_workspace
Revises: ar2_seed_error_patterns
Create Date: 2025-12-13
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "as1_add_default_workspace"
down_revision = "ar2_seed_error_patterns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add default_workspace_id column to users table."""
    # Add default_workspace_id column with FK to workspaces
    op.add_column(
        "users",
        sa.Column(
            "default_workspace_id",
            sa.UUID(),
            sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Create index for faster lookups
    op.create_index(
        "ix_users_default_workspace_id",
        "users",
        ["default_workspace_id"],
    )


def downgrade() -> None:
    """Remove default_workspace_id column from users table."""
    op.drop_index("ix_users_default_workspace_id", table_name="users")
    op.drop_column("users", "default_workspace_id")
