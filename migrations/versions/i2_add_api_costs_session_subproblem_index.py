"""Add composite index on api_costs(session_id, sub_problem_index).

Optimizes get_subproblem_costs() aggregation queries for cost attribution.
Addresses [COST][P2] task for sub-problem cost breakdown.

Revision ID: i2_session_subproblem_idx
Revises: i1_session_created_idx
Create Date: 2025-12-10

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i2_session_subproblem_idx"
down_revision: str | Sequence[str] | None = "i1_session_created_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add composite index for sub-problem cost aggregation queries."""
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_costs_session_subproblem
        ON api_costs (session_id, sub_problem_index)
    """)


def downgrade() -> None:
    """Remove composite index."""
    op.execute("DROP INDEX IF EXISTS idx_api_costs_session_subproblem")
