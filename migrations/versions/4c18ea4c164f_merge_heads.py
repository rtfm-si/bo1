"""Merge migration heads.

Revision ID: 4c18ea4c164f
Revises: 9f3c7b8e2d1a, 2f7e9d4c8b1a
Create Date: 2025-11-20 19:29:44.181024

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "4c18ea4c164f"
down_revision: str | Sequence[str] | None = ("9f3c7b8e2d1a", "2f7e9d4c8b1a")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
