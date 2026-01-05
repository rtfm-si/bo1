"""Add priority field to metric_templates.

Revision ID: zzj_add_priority_to_metric_templates
Revises: zzh_add_d2c_metric_templates
Create Date: 2026-01-05

Adds priority column (1=high, 2=medium, 3=low) for smart metric selection.
High priority: universal metrics (LTV, CAC, Churn)
Medium priority: common but situational (DAU, NPS)
Low priority: specialized metrics
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "zzj_priority_templates"
down_revision = "zzh_add_d2c_metric_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add priority column and seed values."""
    # Add priority column with default of 2 (medium)
    op.add_column(
        "metric_templates",
        sa.Column(
            "priority",
            sa.Integer,
            server_default="2",
            nullable=False,
            comment="1=high (universal), 2=medium, 3=low (specialized)",
        ),
    )

    # Set priorities based on metric importance/universality
    # Priority 1 (high): Universal core metrics everyone tracks
    op.execute("""
        UPDATE metric_templates
        SET priority = 1
        WHERE metric_key IN ('mrr', 'arr', 'cac', 'ltv', 'ltv_cac_ratio', 'monthly_churn', 'gross_margin')
    """)

    # Priority 2 (medium): Common but situational
    op.execute("""
        UPDATE metric_templates
        SET priority = 2
        WHERE metric_key IN ('nrr', 'conversion_rate', 'payback_period', 'average_order_value', 'return_rate')
    """)

    # Priority 3 (low): Specialized or less commonly tracked
    op.execute("""
        UPDATE metric_templates
        SET priority = 3
        WHERE metric_key IN ('burn_rate', 'runway', 'inventory_turnover', 'cost_of_goods_sold')
    """)


def downgrade() -> None:
    """Remove priority column."""
    op.drop_column("metric_templates", "priority")
