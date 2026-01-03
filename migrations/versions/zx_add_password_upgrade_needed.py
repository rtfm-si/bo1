"""Add password_upgrade_needed column to users table.

Revision ID: zx_add_password_upgrade_needed
Revises: 307364da3a1a
Create Date: 2026-01-02

Tracks whether a user's password needs upgrading to meet current strength requirements.
Set to True on login if existing password is weak; cleared after successful upgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "zx_add_password_upgrade_needed"
down_revision: str | Sequence[str] | None = "307364da3a1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add password_upgrade_needed column."""
    op.add_column(
        "users",
        sa.Column(
            "password_upgrade_needed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Remove password_upgrade_needed column."""
    op.drop_column("users", "password_upgrade_needed")
