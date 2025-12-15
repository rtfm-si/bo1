"""Drop deprecated columns from research_cache.

Removes columns that are now computed on-the-fly:
- source_count: Now computed as COALESCE(jsonb_array_length(sources), 0)
- freshness_days: Now hardcoded to 90 (was always unused after insertion)

Code changes in cache_repository.py already compute these values in SELECT/RETURNING.

Revision ID: c6_drop_research_cache_deprecated
Revises: c5_remove_deprecated_columns
Create Date: 2025-12-14

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6_drop_cache_cols"
down_revision: str | None = "c5_remove_deprecated_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop deprecated columns from research_cache."""
    # Drop source_count - now computed from sources JSONB
    op.execute("ALTER TABLE research_cache DROP COLUMN IF EXISTS source_count")

    # Drop freshness_days - hardcoded to 90, never used after save
    op.execute("ALTER TABLE research_cache DROP COLUMN IF EXISTS freshness_days")


def downgrade() -> None:
    """Re-add columns for rollback safety."""
    # Re-add source_count with computed default
    op.execute(
        """
        ALTER TABLE research_cache
        ADD COLUMN IF NOT EXISTS source_count INTEGER
        DEFAULT 0
        """
    )
    # Backfill source_count from sources JSONB
    op.execute(
        """
        UPDATE research_cache
        SET source_count = COALESCE(jsonb_array_length(sources), 0)
        WHERE source_count IS NULL OR source_count = 0
        """
    )

    # Re-add freshness_days with default
    op.execute(
        """
        ALTER TABLE research_cache
        ADD COLUMN IF NOT EXISTS freshness_days INTEGER
        DEFAULT 90
        """
    )
