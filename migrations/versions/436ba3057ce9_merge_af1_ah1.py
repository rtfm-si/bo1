"""merge_af1_ah1

Revision ID: 436ba3057ce9
Revises: af1_add_bluesky_auth, ah1_add_admin_impersonation
Create Date: 2025-12-13 02:16:32.237588

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "436ba3057ce9"
down_revision: str | Sequence[str] | None = ("af1_add_bluesky_auth", "ah1_add_admin_impersonation")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
