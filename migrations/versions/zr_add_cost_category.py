"""Add cost_category column to api_costs table.

Distinguishes user costs vs internal costs (SEO, system jobs).
Values: 'user' (default), 'internal_seo', 'internal_system'.

Revision ID: zr_add_cost_category
Revises: zq_add_heatmap_history_months
Create Date: 2025-12-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "zr_add_cost_category"
down_revision: str = "zq_add_heatmap_history_months"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add cost_category column to api_costs."""
    op.add_column(
        "api_costs",
        sa.Column(
            "cost_category",
            sa.String(50),
            nullable=False,
            server_default="user",
            comment="Cost category: user, internal_seo, internal_system",
        ),
    )

    # Add index for filtering by category
    op.create_index(
        "idx_api_costs_category",
        "api_costs",
        ["cost_category"],
    )


def downgrade() -> None:
    """Remove cost_category column."""
    op.drop_index("idx_api_costs_category", table_name="api_costs")
    op.drop_column("api_costs", "cost_category")
