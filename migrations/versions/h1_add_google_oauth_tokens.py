"""Add Google OAuth token columns to users table.

Stores access_token, refresh_token, and scopes for Google Sheets API access.
Auth is handled by SuperTokens; tokens stored in PostgreSQL.

Revision ID: h1_google_oauth_tokens
Revises: g3_add_dataset_sessions
Create Date: 2025-12-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "h1_google_oauth_tokens"
down_revision: str | Sequence[str] | None = "g3_add_dataset_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add Google OAuth token columns to users table."""
    # JSONB for storing {access_token, refresh_token, expires_at}
    op.add_column(
        "users",
        sa.Column("google_oauth_tokens", JSONB, nullable=True),
    )
    # Track which scopes user has authorized (comma-separated)
    op.add_column(
        "users",
        sa.Column("google_oauth_scopes", sa.Text, nullable=True),
    )
    # When tokens were last updated (for refresh logic)
    op.add_column(
        "users",
        sa.Column(
            "google_tokens_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove Google OAuth token columns from users table."""
    op.drop_column("users", "google_tokens_updated_at")
    op.drop_column("users", "google_oauth_scopes")
    op.drop_column("users", "google_oauth_tokens")
