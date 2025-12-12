"""Merge all migration heads into single chain.

Merges p1_add_feature_flags, s1_encrypt_oauth_tokens, and z3_add_session_termination
into a single head for the workspaces schema.

Revision ID: aa0_merge_all_heads
Revises: p1_add_feature_flags, s1_encrypt_oauth_tokens, z3_add_session_termination
Create Date: 2025-12-12

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "aa0_merge_all_heads"
down_revision: str | Sequence[str] | None = (
    "p1_add_feature_flags",
    "s1_encrypt_oauth_tokens",
    "z3_add_session_termination",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge heads - no schema changes."""
    pass


def downgrade() -> None:
    """Reverse merge."""
    pass
