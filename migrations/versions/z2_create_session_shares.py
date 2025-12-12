"""Create session_shares table for public session sharing.

This migration creates the session_shares table to enable time-limited
public sharing of completed sessions via unique tokens.

Revision ID: z2_create_session_shares
Revises: a2_add_action_progress
Create Date: 2025-12-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z2_create_session_shares"
down_revision: str | Sequence[str] | None = "a2_add_action_progress"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create session_shares table."""
    op.create_table(
        "session_shares",
        sa.Column(
            "id", sa.String(36), nullable=False, primary_key=True, comment="UUID primary key"
        ),
        sa.Column("session_id", sa.String(36), nullable=False, comment="FK to sessions table"),
        sa.Column(
            "created_by", sa.String(36), nullable=False, comment="FK to users table (creator)"
        ),
        sa.Column(
            "token",
            sa.String(64),
            nullable=False,
            unique=True,
            comment="Unique share token (24+ random chars)",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Token expiry timestamp (UTC)",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            default=True,
            comment="Soft-delete flag (false = revoked)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="Share creation timestamp (UTC)",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.Index("session_shares_token_idx", "token"),
        sa.Index("session_shares_session_id_idx", "session_id"),
        sa.Index("session_shares_created_by_idx", "created_by"),
        sa.Index("session_shares_expires_at_idx", "expires_at"),
    )


def downgrade() -> None:
    """Drop session_shares table."""
    op.drop_table("session_shares")
