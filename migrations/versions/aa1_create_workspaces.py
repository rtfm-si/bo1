"""Create workspaces and workspace_members tables.

Revision ID: aa1_create_workspaces
Revises: z3_add_session_termination
Create Date: 2025-12-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa1_create_workspaces"
down_revision: str | Sequence[str] | None = "aa0_merge_all_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create workspaces and workspace_members tables."""
    # Create workspaces table
    op.create_table(
        "workspaces",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(63), nullable=False, unique=True),
        sa.Column(
            "owner_id",
            sa.String(255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create workspace_members table
    op.create_table(
        "workspace_members",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.UUID(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(16),
            nullable=False,
            comment="Role: owner, admin, member",
        ),
        sa.Column(
            "invited_by",
            sa.String(255),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Composite unique constraint - each user can only be in a workspace once
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
    )

    # Index on workspace_id for member lookups
    op.create_index(
        "ix_workspace_members_workspace_id",
        "workspace_members",
        ["workspace_id"],
    )

    # Index on user_id for finding user's workspaces
    op.create_index(
        "ix_workspace_members_user_id",
        "workspace_members",
        ["user_id"],
    )

    # Index on slug for workspace lookups by slug
    op.create_index(
        "ix_workspaces_slug",
        "workspaces",
        ["slug"],
    )

    # Index on owner_id for owner queries
    op.create_index(
        "ix_workspaces_owner_id",
        "workspaces",
        ["owner_id"],
    )


def downgrade() -> None:
    """Drop workspaces and workspace_members tables."""
    op.drop_index("ix_workspaces_owner_id", table_name="workspaces")
    op.drop_index("ix_workspaces_slug", table_name="workspaces")
    op.drop_index("ix_workspace_members_user_id", table_name="workspace_members")
    op.drop_index("ix_workspace_members_workspace_id", table_name="workspace_members")
    op.drop_table("workspace_members")
    op.drop_table("workspaces")
