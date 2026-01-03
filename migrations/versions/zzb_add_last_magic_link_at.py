"""Add last_magic_link_at column to users table.

Revision ID: zzb_add_last_magic_link_at
Revises: zza_add_preferred_currency
Create Date: 2026-01-03
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "zzb_add_last_magic_link_at"
down_revision = "zza_add_preferred_currency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add last_magic_link_at column for magic link rate limiting."""
    op.add_column(
        "users",
        sa.Column(
            "last_magic_link_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Timestamp of last magic link request for rate limiting",
        ),
    )


def downgrade() -> None:
    """Remove last_magic_link_at column."""
    op.drop_column("users", "last_magic_link_at")
