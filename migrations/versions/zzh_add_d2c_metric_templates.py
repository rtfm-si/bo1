"""Add D2C/product-specific metric templates.

Revision ID: zzh_add_d2c_metric_templates
Revises: zzg_add_is_relevant_to_metrics
Create Date: 2026-01-05

Adds inventory, margin, conversion, AOV, COGS, and return rate metrics
for D2C and retail businesses.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "zzh_add_d2c_metric_templates"
down_revision = "zzg_add_is_relevant_to_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add D2C metric templates."""
    op.execute("""
        INSERT INTO metric_templates (metric_key, name, definition, importance, category, value_unit, display_order, applies_to) VALUES
        ('inventory_turnover', 'Inventory Turnover', 'Number of times inventory is sold and replaced per period', 'Efficiency of inventory management - higher is better, typically 4-12x annually', 'efficiency', 'turns', 20, '["d2c", "retail", "ecommerce"]'),
        ('average_order_value', 'Average Order Value', 'Average revenue per order (total revenue / number of orders)', 'Key driver of revenue - increasing AOV can improve margins significantly', 'financial', '$', 21, '["d2c", "retail", "ecommerce"]'),
        ('return_rate', 'Return Rate', 'Percentage of orders returned by customers', 'Quality and product-market fit indicator - lower is better, <5% is good', 'retention', '%', 22, '["d2c", "retail", "ecommerce"]'),
        ('cost_of_goods_sold', 'Cost of Goods Sold', 'Direct costs of producing/sourcing products sold', 'Key profitability driver - track to maintain healthy gross margins', 'financial', '$', 23, '["d2c", "retail", "ecommerce"]')
        ON CONFLICT (metric_key) DO UPDATE SET
            applies_to = EXCLUDED.applies_to,
            display_order = EXCLUDED.display_order;
    """)


def downgrade() -> None:
    """Remove D2C metric templates."""
    op.execute("""
        DELETE FROM metric_templates
        WHERE metric_key IN ('inventory_turnover', 'average_order_value', 'return_rate', 'cost_of_goods_sold')
    """)
