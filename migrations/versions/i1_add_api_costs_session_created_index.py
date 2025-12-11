"""Add composite index on api_costs(session_id, created_at).

Optimizes get_session_costs() aggregation and time-range queries per session.
Addresses [PERF][P0] and [DATA][P1] audit tasks.

Revision ID: i1_session_created_idx
Revises: h3_deprecation_comments
Create Date: 2025-12-10

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i1_session_created_idx"
down_revision: str | Sequence[str] | None = "h3_deprecation_comments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add composite index for session cost aggregation queries."""
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_costs_session_created
        ON api_costs (session_id, created_at DESC)
    """)


def downgrade() -> None:
    """Remove composite index."""
    op.execute("DROP INDEX IF EXISTS idx_api_costs_session_created")
