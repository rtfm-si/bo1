"""Add Bluesky authentication fields.

Adds bluesky_did and bluesky_handle columns to users table
for AT Protocol OAuth integration.

Revision ID: af1_add_bluesky_auth
Revises: ae1_impl_realist_persona
Create Date: 2025-12-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "af1_add_bluesky_auth"
down_revision: str | Sequence[str] | None = "ae1_impl_realist_persona"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add Bluesky authentication fields to users table."""
    # Add bluesky_did column (Decentralized Identifier - unique across AT Protocol)
    op.add_column(
        "users",
        sa.Column("bluesky_did", sa.String(255), nullable=True),
    )

    # Add bluesky_handle column (e.g., user.bsky.social)
    op.add_column(
        "users",
        sa.Column("bluesky_handle", sa.String(255), nullable=True),
    )

    # Create index on bluesky_did for fast lookups
    op.create_index(
        "ix_users_bluesky_did",
        "users",
        ["bluesky_did"],
        unique=True,
        postgresql_where=sa.text("bluesky_did IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove Bluesky authentication fields from users table."""
    op.drop_index("ix_users_bluesky_did", table_name="users")
    op.drop_column("users", "bluesky_handle")
    op.drop_column("users", "bluesky_did")
