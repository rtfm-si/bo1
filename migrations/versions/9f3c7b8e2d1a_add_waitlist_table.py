"""Add waitlist table for landing page signups.

Separate from beta_whitelist - this captures all interested users.
Beta_whitelist is for admin-controlled access, waitlist is for public signups.

Revision ID: 9f3c7b8e2d1a
Revises: 8a5d2f9e1b3c
Create Date: 2025-11-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "9f3c7b8e2d1a"
down_revision: str | Sequence[str] | None = "8a5d2f9e1b3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # waitlist table - Public signups from landing page
    op.create_table(
        "waitlist",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
            comment="Status: pending, invited, converted",
        ),
        sa.Column(
            "source",
            sa.String(length=100),
            nullable=True,
            comment="Where they signed up: landing_page, footer, etc.",
        ),
        sa.Column("notes", sa.Text, nullable=True, comment="Admin notes about this signup"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Create index on email for fast lookups
    op.create_index("idx_waitlist_email", "waitlist", ["email"], unique=True)

    # Create index on status for filtering
    op.create_index("idx_waitlist_status", "waitlist", ["status"])

    # Create trigger to auto-update updated_at timestamp
    op.execute(
        """
        CREATE TRIGGER update_waitlist_updated_at
        BEFORE UPDATE ON waitlist
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS update_waitlist_updated_at ON waitlist")
    op.drop_index("idx_waitlist_status", table_name="waitlist")
    op.drop_index("idx_waitlist_email", table_name="waitlist")
    op.drop_table("waitlist")
