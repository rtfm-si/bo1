"""Remove deprecated columns from sessions and session_clarifications.

Removes columns marked DEPRECATED in h3_add_deprecation_comments:
- sessions.max_rounds: Default 10, no graph logic references DB column (uses state dict)
- session_clarifications.asked_at_round: Denormalized; round_number on contributions is source

NOTE: research_cache.source_count and research_cache.freshness_days are NOT removed here
because they are actively used in cache_repository.py. Those require code changes first.

Revision ID: c5_remove_deprecated_columns
Revises: c4_add_perf_indexes
Create Date: 2025-12-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5_remove_deprecated_columns"
down_revision: str | None = "c4_add_perf_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove deprecated columns."""
    # Remove sessions.max_rounds - graph uses state dict, not DB column
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS max_rounds")

    # Remove session_clarifications.asked_at_round - denormalized field
    op.execute("ALTER TABLE session_clarifications DROP COLUMN IF EXISTS asked_at_round")


def downgrade() -> None:
    """Re-add columns for rollback safety."""
    # Re-add sessions.max_rounds
    op.add_column(
        "sessions",
        sa.Column("max_rounds", sa.Integer, nullable=True, server_default="10"),
    )

    # Re-add session_clarifications.asked_at_round
    op.add_column(
        "session_clarifications",
        sa.Column("asked_at_round", sa.Integer, nullable=True),
    )
