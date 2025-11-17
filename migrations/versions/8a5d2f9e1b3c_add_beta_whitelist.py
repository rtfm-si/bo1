"""Add beta whitelist table.

Add beta_whitelist table for managing closed beta access control.
Allows admin to dynamically add/remove beta testers.

Revision ID: 8a5d2f9e1b3c
Revises: 71a746e3c1d9
Create Date: 2025-11-17 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "8a5d2f9e1b3c"
down_revision: str | Sequence[str] | None = "71a746e3c1d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # beta_whitelist table - Email whitelist for closed beta
    op.create_table(
        "beta_whitelist",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("added_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Create index on email for fast lookups
    op.create_index("idx_beta_whitelist_email", "beta_whitelist", ["email"], unique=True)

    # Create trigger to auto-update updated_at timestamp
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER update_beta_whitelist_updated_at
        BEFORE UPDATE ON beta_whitelist
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS update_beta_whitelist_updated_at ON beta_whitelist")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    op.drop_index("idx_beta_whitelist_email", table_name="beta_whitelist")
    op.drop_table("beta_whitelist")
