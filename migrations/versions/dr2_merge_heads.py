"""Merge terms and retention reminder migrations.

Revision ID: dr2_merge_heads
Revises: dr1_del_remind, tc2_seed_initial_terms
Create Date: 2025-12-26
"""

from collections.abc import Sequence

revision: str = "dr2_merge_heads"
down_revision: str | Sequence[str] | None = (
    "dr1_del_remind",
    "tc2_seed_initial_terms",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge heads - no additional changes needed."""
    pass


def downgrade() -> None:
    """Reverse merge."""
    pass
