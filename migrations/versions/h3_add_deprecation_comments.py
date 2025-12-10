"""Add deprecation comments to unused columns.

Marks columns for removal in v2.0:
- sessions.max_rounds - Default 10, no graph logic references
- session_clarifications.asked_at_round - Denormalized; round_number on contributions is source
- research_cache.source_count - Duplicates info in sources JSONB
- research_cache.freshness_days - Hardcoded 90, no eviction implemented

Revision ID: h3_deprecation_comments
Revises: h2_fix_datasets_rls
Create Date: 2025-12-10
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h3_deprecation_comments"
down_revision: str | Sequence[str] | None = "h2_fix_datasets_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add deprecation comments to unused columns for v2.0 removal."""
    # Add deprecation comments to unused columns
    op.execute(
        "COMMENT ON COLUMN sessions.max_rounds IS 'DEPRECATED: Remove in v2.0 - Default 10, no graph logic references';"
    )
    op.execute(
        "COMMENT ON COLUMN session_clarifications.asked_at_round IS 'DEPRECATED: Remove in v2.0 - Denormalized; round_number on contributions is source';"
    )
    op.execute(
        "COMMENT ON COLUMN research_cache.source_count IS 'DEPRECATED: Remove in v2.0 - Duplicates info in sources JSONB';"
    )
    op.execute(
        "COMMENT ON COLUMN research_cache.freshness_days IS 'DEPRECATED: Remove in v2.0 - Hardcoded 90, no eviction implemented';"
    )


def downgrade() -> None:
    """Remove deprecation comments from columns."""
    # Remove deprecation comments
    op.execute("COMMENT ON COLUMN sessions.max_rounds IS NULL;")
    op.execute("COMMENT ON COLUMN session_clarifications.asked_at_round IS NULL;")
    op.execute("COMMENT ON COLUMN research_cache.source_count IS NULL;")
    op.execute("COMMENT ON COLUMN research_cache.freshness_days IS NULL;")
