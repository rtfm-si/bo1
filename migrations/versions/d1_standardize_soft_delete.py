"""Standardize soft-delete pattern: is_active -> deleted_at.

Migrates is_active boolean columns to deleted_at timestamp pattern
for promotions and session_shares tables.

Benefits:
- Records WHEN something was deleted (audit trail)
- Enables restore functionality with SET deleted_at = NULL
- Standard pattern across industry

Revision ID: d1_standardize_soft_delete
Revises: c6_drop_cache_cols
Create Date: 2025-12-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1_soft_delete"
down_revision: str | None = "c6_drop_cache_cols"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add deleted_at columns, backfill, drop is_active."""
    # --- promotions table ---
    # Add deleted_at column
    op.add_column(
        "promotions",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Backfill: is_active=false -> deleted_at = NOW()
    op.execute(
        """
        UPDATE promotions
        SET deleted_at = NOW()
        WHERE is_active = false
        """
    )

    # Drop old is_active index first
    op.execute("DROP INDEX IF EXISTS ix_promotions_is_active")

    # Drop is_active column
    op.drop_column("promotions", "is_active")

    # Add partial index for active records (deleted_at IS NULL)
    op.execute(
        """
        CREATE INDEX ix_promotions_active
        ON promotions(id)
        WHERE deleted_at IS NULL
        """
    )

    # --- session_shares table ---
    # Add deleted_at column
    op.add_column(
        "session_shares",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Backfill: is_active=false -> deleted_at = NOW()
    op.execute(
        """
        UPDATE session_shares
        SET deleted_at = NOW()
        WHERE is_active = false
        """
    )

    # Drop is_active column
    op.drop_column("session_shares", "is_active")

    # Add partial index for active records
    op.execute(
        """
        CREATE INDEX ix_session_shares_active
        ON session_shares(id)
        WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    """Restore is_active columns from deleted_at."""
    # --- promotions table ---
    # Drop new index
    op.execute("DROP INDEX IF EXISTS ix_promotions_active")

    # Add is_active column back
    op.add_column(
        "promotions",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )

    # Backfill: deleted_at IS NOT NULL -> is_active = false
    op.execute(
        """
        UPDATE promotions
        SET is_active = false
        WHERE deleted_at IS NOT NULL
        """
    )

    # Re-create is_active index
    op.create_index("ix_promotions_is_active", "promotions", ["is_active"])

    # Drop deleted_at column
    op.drop_column("promotions", "deleted_at")

    # --- session_shares table ---
    # Drop new index
    op.execute("DROP INDEX IF EXISTS ix_session_shares_active")

    # Add is_active column back
    op.add_column(
        "session_shares",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )

    # Backfill
    op.execute(
        """
        UPDATE session_shares
        SET is_active = false
        WHERE deleted_at IS NOT NULL
        """
    )

    # Drop deleted_at column
    op.drop_column("session_shares", "deleted_at")
