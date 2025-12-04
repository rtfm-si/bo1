"""Add business metrics tables for Layer 3 context.

Creates metric_templates (predefined SaaS metrics) and business_metrics
(user-specific metric values) tables for tracking business KPIs.

This enables context-aware expert recommendations based on actual
business performance data.

Revision ID: d3e4f5g6h7i8
Revises: c2d3e4f5g6h7
Create Date: 2025-12-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "d3e4f5g6h7i8"
down_revision: str | Sequence[str] | None = "c2d3e4f5g6h7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create metric_templates and business_metrics tables with seed data."""
    # ==========================================================================
    # Create metric_templates table (predefined metrics)
    # ==========================================================================
    op.create_table(
        "metric_templates",
        sa.Column("metric_key", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("definition", sa.Text, nullable=False),
        sa.Column("importance", sa.Text, nullable=False),
        sa.Column(
            "category",
            sa.String(50),
            nullable=False,
            comment="financial, growth, retention, efficiency",
        ),
        sa.Column(
            "value_unit",
            sa.String(20),
            nullable=False,
            comment="$, %, months, ratio, days",
        ),
        sa.Column("display_order", sa.Integer, server_default="0", nullable=False),
        sa.Column(
            "applies_to",
            JSONB,
            server_default='["all"]',
            nullable=False,
            comment="Business models: saas, ecommerce, marketplace, all",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ==========================================================================
    # Create business_metrics table (user-specific values)
    # ==========================================================================
    op.create_table(
        "business_metrics",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_key", sa.String(50), nullable=False),
        # Metric definition (can override template for custom metrics)
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("definition", sa.Text, nullable=True),
        sa.Column("importance", sa.Text, nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        # Value
        sa.Column("value", sa.Numeric(20, 4), nullable=True),
        sa.Column("value_unit", sa.String(20), nullable=True),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the value was captured/measured",
        ),
        sa.Column(
            "source",
            sa.String(50),
            server_default="manual",
            nullable=False,
            comment="manual, clarification, integration",
        ),
        # Metadata
        sa.Column(
            "is_predefined",
            sa.Boolean,
            server_default="false",
            nullable=False,
            comment="True if based on a template",
        ),
        sa.Column("display_order", sa.Integer, server_default="0", nullable=False),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        # Unique constraint: one metric per user
        sa.UniqueConstraint("user_id", "metric_key", name="uq_business_metrics_user_key"),
    )

    # Indexes for business_metrics
    op.create_index("idx_business_metrics_user_id", "business_metrics", ["user_id"])
    op.create_index("idx_business_metrics_category", "business_metrics", ["category"])

    # Check constraint for source values
    op.create_check_constraint(
        "business_metrics_source_check",
        "business_metrics",
        "source IN ('manual', 'clarification', 'integration')",
    )

    # Check constraint for category values
    op.create_check_constraint(
        "business_metrics_category_check",
        "business_metrics",
        "category IS NULL OR category IN ('financial', 'growth', 'retention', 'efficiency', 'custom')",
    )

    # Enable RLS on business_metrics
    op.execute("ALTER TABLE business_metrics ENABLE ROW LEVEL SECURITY")

    # RLS policy for business_metrics (users can only see/modify their own)
    op.execute("""
        CREATE POLICY business_metrics_own_data ON business_metrics
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', true))
        WITH CHECK (user_id = current_setting('app.current_user_id', true));
    """)

    # ==========================================================================
    # Seed metric_templates with predefined SaaS metrics
    # ==========================================================================
    op.execute("""
        INSERT INTO metric_templates (metric_key, name, definition, importance, category, value_unit, display_order, applies_to) VALUES
        ('mrr', 'Monthly Recurring Revenue', 'Total predictable revenue per month from subscriptions', 'Core health metric - indicates business scale and growth trajectory', 'financial', '$', 1, '["saas"]'),
        ('arr', 'Annual Recurring Revenue', 'MRR × 12 - annualized recurring revenue', 'Standard metric for valuation and planning', 'financial', '$', 2, '["saas"]'),
        ('cac', 'Customer Acquisition Cost', 'Total sales & marketing spend divided by new customers acquired', 'Measures efficiency of growth spend - lower is better', 'growth', '$', 3, '["all"]'),
        ('ltv', 'Customer Lifetime Value', 'Average revenue per customer over their entire relationship', 'Indicates long-term customer worth - should be >3x CAC', 'growth', '$', 4, '["all"]'),
        ('ltv_cac_ratio', 'LTV:CAC Ratio', 'Lifetime value divided by acquisition cost', 'Unit economics health - 3:1 is good, 5:1 is excellent', 'efficiency', 'ratio', 5, '["all"]'),
        ('monthly_churn', 'Monthly Churn Rate', 'Percentage of customers lost per month', 'Retention health - <2% monthly is good for SaaS', 'retention', '%', 6, '["saas"]'),
        ('nrr', 'Net Revenue Retention', 'Revenue retained from existing customers including expansion', 'Growth indicator - >100% means growing without new customers', 'retention', '%', 7, '["saas"]'),
        ('conversion_rate', 'Conversion Rate', 'Percentage of trials/leads that become paying customers', 'Funnel efficiency - varies by model (freemium vs sales-led)', 'growth', '%', 8, '["all"]'),
        ('payback_period', 'CAC Payback Period', 'Months required to recover customer acquisition cost', 'Cash flow efficiency - <12 months is good', 'efficiency', 'months', 9, '["saas"]'),
        ('gross_margin', 'Gross Margin', 'Revenue minus cost of goods sold, as percentage', 'Profitability baseline - >70% typical for SaaS', 'financial', '%', 10, '["all"]'),
        ('burn_rate', 'Monthly Burn Rate', 'Net cash spent per month', 'Runway indicator - how fast spending cash reserves', 'financial', '$', 11, '["all"]'),
        ('runway', 'Runway', 'Months of operation remaining at current burn rate', 'Survival metric - aim for >12 months', 'financial', 'months', 12, '["all"]');
    """)


def downgrade() -> None:
    """Remove business metrics tables."""
    # Drop RLS policy and business_metrics table
    op.execute("DROP POLICY IF EXISTS business_metrics_own_data ON business_metrics")
    op.drop_constraint("business_metrics_category_check", "business_metrics", type_="check")
    op.drop_constraint("business_metrics_source_check", "business_metrics", type_="check")
    op.drop_index("idx_business_metrics_category", table_name="business_metrics")
    op.drop_index("idx_business_metrics_user_id", table_name="business_metrics")
    op.drop_table("business_metrics")

    # Drop metric_templates table
    op.drop_table("metric_templates")
