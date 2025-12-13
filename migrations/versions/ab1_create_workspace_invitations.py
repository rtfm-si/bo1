"""Create workspace_invitations table.

Revision ID: ab1_create_workspace_invitations
Revises: aa3_add_workspace_to_datasets
Create Date: 2025-12-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab1_create_workspace_invitations"
down_revision: str | Sequence[str] | None = "aa3_add_workspace_to_datasets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create workspace_invitations table."""
    op.create_table(
        "workspace_invitations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.UUID(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.String(16),
            nullable=False,
            comment="Role to assign: admin, member",
        ),
        sa.Column("token", sa.UUID(), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="pending",
            comment="Status: pending, accepted, declined, revoked, expired",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "invited_by",
            sa.String(255),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Unique constraint: only one pending invitation per email+workspace
        sa.UniqueConstraint(
            "workspace_id",
            "email",
            "status",
            name="uq_workspace_invitation_pending",
        ),
    )

    # Index on token for lookups
    op.create_index(
        "ix_workspace_invitations_token",
        "workspace_invitations",
        ["token"],
    )

    # Index on workspace_id for listing
    op.create_index(
        "ix_workspace_invitations_workspace_id",
        "workspace_invitations",
        ["workspace_id"],
    )

    # Index on email for user lookup
    op.create_index(
        "ix_workspace_invitations_email",
        "workspace_invitations",
        ["email"],
    )

    # Index on status for filtering pending
    op.create_index(
        "ix_workspace_invitations_status",
        "workspace_invitations",
        ["status"],
    )


def downgrade() -> None:
    """Drop workspace_invitations table."""
    op.drop_index("ix_workspace_invitations_status", table_name="workspace_invitations")
    op.drop_index("ix_workspace_invitations_email", table_name="workspace_invitations")
    op.drop_index("ix_workspace_invitations_workspace_id", table_name="workspace_invitations")
    op.drop_index("ix_workspace_invitations_token", table_name="workspace_invitations")
    op.drop_table("workspace_invitations")
