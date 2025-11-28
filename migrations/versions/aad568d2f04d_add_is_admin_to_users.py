"""Add is_admin to users.

Revision ID: aad568d2f04d
Revises: a1b2c3d4e5f6
Create Date: 2025-11-28 21:06:52.243789

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aad568d2f04d"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_admin column to users table
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Set si@boardof.one as admin
    op.execute(
        """
        UPDATE users
        SET is_admin = true
        WHERE email = 'si@boardof.one'
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop is_admin column
    op.drop_column("users", "is_admin")
