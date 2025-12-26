"""Expand benchmark metrics from 12 to ~20.

Adds new metric templates: dau, mau, dau_mau_ratio, arpu, arr_growth_rate,
grr, active_churn, revenue_churn, nps, quick_ratio.

LTV already exists - no action needed.

Revision ID: z25_expand_benchmark_metrics
Revises: ab1_persona_exp
Create Date: 2025-12-26
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z25_expand_benchmark_metrics"
down_revision: str | Sequence[str] | None = "ab1_persona_exp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Insert new metric templates (idempotent - ON CONFLICT DO NOTHING)."""
    op.execute("""
        INSERT INTO metric_templates (metric_key, name, definition, importance, category, value_unit, display_order, applies_to) VALUES
        ('dau', 'Daily Active Users', 'Number of unique users engaging with product daily', 'Key engagement metric - indicates product stickiness and daily value delivery', 'growth', 'count', 20, '["all"]'),
        ('mau', 'Monthly Active Users', 'Number of unique users engaging with product monthly', 'Core growth metric - tracks overall user base and market penetration', 'growth', 'count', 21, '["all"]'),
        ('dau_mau_ratio', 'DAU/MAU Ratio', 'Daily active users divided by monthly active users', 'Stickiness indicator - >20% is good, >50% is exceptional (like social apps)', 'retention', '%', 22, '["all"]'),
        ('arpu', 'Average Revenue Per User', 'Total revenue divided by number of active users', 'Monetization efficiency - indicates value extracted per customer', 'financial', '$', 23, '["all"]'),
        ('arr_growth_rate', 'ARR Growth Rate', 'Year-over-year percentage increase in ARR', 'Key growth indicator - >100% is hyper-growth, >40% is strong', 'growth', '%', 24, '["saas"]'),
        ('grr', 'Gross Revenue Retention', 'Revenue retained from existing customers excluding expansion', 'Churn indicator - >90% is good, >95% is excellent', 'retention', '%', 25, '["saas"]'),
        ('active_churn', 'Customer Churn Rate', 'Percentage of customers lost over a period', 'Customer retention health - <5% annual is good for B2B SaaS', 'retention', '%', 26, '["all"]'),
        ('revenue_churn', 'Revenue Churn Rate', 'Percentage of recurring revenue lost over a period', 'Revenue retention - often more important than customer count churn', 'retention', '%', 27, '["saas"]'),
        ('nps', 'Net Promoter Score', 'Customer likelihood to recommend (promoters minus detractors)', 'Customer satisfaction proxy - >50 is excellent, >70 is world-class', 'retention', 'score', 28, '["all"]'),
        ('quick_ratio', 'SaaS Quick Ratio', 'New MRR plus expansion divided by churned MRR plus contraction', 'Growth efficiency - >4 is excellent, indicates healthy growth', 'growth', 'ratio', 29, '["saas"]')
        ON CONFLICT (metric_key) DO NOTHING;
    """)


def downgrade() -> None:
    """Remove the newly added metric templates."""
    op.execute("""
        DELETE FROM metric_templates
        WHERE metric_key IN (
            'dau', 'mau', 'dau_mau_ratio', 'arpu', 'arr_growth_rate',
            'grr', 'active_churn', 'revenue_churn', 'nps', 'quick_ratio'
        );
    """)
