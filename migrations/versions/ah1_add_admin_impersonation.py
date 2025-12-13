"""Add admin impersonation sessions table.

This migration adds:
- admin_impersonation_sessions table for tracking impersonation sessions

Revision ID: ah1_add_admin_impersonation
Revises: ag1_add_usage_tracking
Create Date: 2025-12-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ah1_add_admin_impersonation"
down_revision: str | Sequence[str] | None = "ag1_add_usage_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add admin impersonation sessions table."""
    op.create_table(
        "admin_impersonation_sessions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "admin_user_id",
            sa.String(length=255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_user_id",
            sa.String(length=255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("is_write_mode", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "ended_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Index for active session lookup (admin_user_id + expires_at for cleanup)
    op.create_index(
        "ix_admin_impersonation_admin_expires",
        "admin_impersonation_sessions",
        ["admin_user_id", "expires_at"],
    )

    # Index for audit queries (by target user)
    op.create_index(
        "ix_admin_impersonation_target",
        "admin_impersonation_sessions",
        ["target_user_id"],
    )


def downgrade() -> None:
    """Remove admin impersonation sessions table."""
    op.drop_index("ix_admin_impersonation_target", table_name="admin_impersonation_sessions")
    op.drop_index("ix_admin_impersonation_admin_expires", table_name="admin_impersonation_sessions")
    op.drop_table("admin_impersonation_sessions")
