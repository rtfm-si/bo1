"""Add workspace join requests and discoverability.

Supports approval workflow for join requests and workspace discoverability settings.

Revision ID: at1_add_workspace_join_requests
Revises: as1_add_default_workspace
Create Date: 2025-12-14
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "at1_add_workspace_join_requests"
down_revision = "as1_add_default_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create workspace_join_requests table and add discoverability column."""
    # Add discoverability column to workspaces
    op.add_column(
        "workspaces",
        sa.Column(
            "discoverability",
            sa.String(16),
            nullable=False,
            server_default="private",
            comment="Discoverability setting: private, invite_only, request_to_join",
        ),
    )

    # Create workspace_join_requests table
    op.create_table(
        "workspace_join_requests",
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
            "message",
            sa.Text(),
            nullable=True,
            comment="Optional message from requester",
        ),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="pending",
            comment="Status: pending, approved, rejected, cancelled",
        ),
        sa.Column(
            "rejection_reason",
            sa.Text(),
            nullable=True,
            comment="Reason provided when rejecting request",
        ),
        sa.Column(
            "reviewed_by",
            sa.String(255),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Only one pending request per user per workspace
        sa.UniqueConstraint(
            "workspace_id",
            "user_id",
            "status",
            name="uq_workspace_join_request_pending",
        ),
    )

    # Indexes for common lookups
    op.create_index(
        "ix_workspace_join_requests_workspace_id",
        "workspace_join_requests",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_join_requests_user_id",
        "workspace_join_requests",
        ["user_id"],
    )
    op.create_index(
        "ix_workspace_join_requests_status",
        "workspace_join_requests",
        ["status"],
    )
    op.create_index(
        "ix_workspace_join_requests_workspace_status",
        "workspace_join_requests",
        ["workspace_id", "status"],
    )


def downgrade() -> None:
    """Drop workspace_join_requests table and discoverability column."""
    op.drop_index(
        "ix_workspace_join_requests_workspace_status",
        table_name="workspace_join_requests",
    )
    op.drop_index(
        "ix_workspace_join_requests_status",
        table_name="workspace_join_requests",
    )
    op.drop_index(
        "ix_workspace_join_requests_user_id",
        table_name="workspace_join_requests",
    )
    op.drop_index(
        "ix_workspace_join_requests_workspace_id",
        table_name="workspace_join_requests",
    )
    op.drop_table("workspace_join_requests")
    op.drop_column("workspaces", "discoverability")
