"""Add research_cache date index for performance.

Adds index on research_cache.research_date to optimize time-based queries
when filtering cached research results by date/freshness.

Expected performance improvement: 10-100x faster date-based filtering
on large datasets (>10K rows).

Revision ID: 2dda9a3a5df2
Revises: 012a6abb33ac
Create Date: 2025-11-23 19:59:02.024638

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2dda9a3a5df2"
down_revision: str | Sequence[str] | None = "012a6abb33ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add missing index for query performance."""
    # Add index on research_cache.research_date for time-based filtering
    # Use IF NOT EXISTS for idempotency (safe to run multiple times)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_research_cache_research_date
        ON research_cache(research_date DESC);
        """
    )


def downgrade() -> None:
    """Remove the index."""
    op.execute("DROP INDEX IF EXISTS idx_research_cache_research_date;")
