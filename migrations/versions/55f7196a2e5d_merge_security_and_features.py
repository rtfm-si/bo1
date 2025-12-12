"""merge_security_and_features

Revision ID: 55f7196a2e5d
Revises: p1_add_feature_flags, s1_encrypt_oauth_tokens
Create Date: 2025-12-12 13:07:53.951485

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "55f7196a2e5d"
down_revision: str | Sequence[str] | None = ("p1_add_feature_flags", "s1_encrypt_oauth_tokens")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
