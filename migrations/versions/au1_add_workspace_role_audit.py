"""Add workspace role change audit table.

Tracks all role changes (promotions, demotions, ownership transfers)
for audit and history purposes.

Revision ID: au1_add_workspace_role_audit
Revises: at1_add_workspace_join_requests
Create Date: 2025-12-14
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "au1_add_workspace_role_audit"
down_revision = "at1_add_workspace_join_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create workspace_role_changes audit table."""
    op.create_table(
        "workspace_role_changes",
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
            comment="User whose role was changed",
        ),
        sa.Column(
            "old_role",
            sa.String(16),
            nullable=False,
            comment="Previous role: owner, admin, member",
        ),
        sa.Column(
            "new_role",
            sa.String(16),
            nullable=False,
            comment="New role: owner, admin, member",
        ),
        sa.Column(
            "change_type",
            sa.String(32),
            nullable=False,
            comment="Type of change: transfer_ownership, promote, demote",
        ),
        sa.Column(
            "changed_by",
            sa.String(255),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="User who made the change",
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Indexes for common lookups
    op.create_index(
        "ix_workspace_role_changes_workspace_id",
        "workspace_role_changes",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_role_changes_user_id",
        "workspace_role_changes",
        ["user_id"],
    )
    op.create_index(
        "ix_workspace_role_changes_changed_at",
        "workspace_role_changes",
        ["changed_at"],
    )


def downgrade() -> None:
    """Drop workspace_role_changes table."""
    op.drop_index(
        "ix_workspace_role_changes_changed_at",
        table_name="workspace_role_changes",
    )
    op.drop_index(
        "ix_workspace_role_changes_user_id",
        table_name="workspace_role_changes",
    )
    op.drop_index(
        "ix_workspace_role_changes_workspace_id",
        table_name="workspace_role_changes",
    )
    op.drop_table("workspace_role_changes")
