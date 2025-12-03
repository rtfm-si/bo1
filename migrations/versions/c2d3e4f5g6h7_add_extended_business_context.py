"""Add extended business context and onboarding tables.

Extends user_context with comprehensive business fields for:
- Company identification (name, website)
- Business stage and objectives
- Industry and market positioning
- Brand attributes and tech stack
- Customer profile and constraints
- Enrichment tracking

Also adds user_onboarding table for driver.js tour tracking.

Revision ID: c2d3e4f5g6h7
Revises: b1c2d3e4f5g6
Create Date: 2025-12-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5g6h7"
down_revision: str | Sequence[str] | None = "b1c2d3e4f5g6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add extended business context fields and onboarding tracking."""
    # ==========================================================================
    # Extend user_context table with new fields
    # ==========================================================================

    # Company identification
    op.add_column("user_context", sa.Column("company_name", sa.String(255), nullable=True))

    # Business stage and objectives
    op.add_column(
        "user_context",
        sa.Column(
            "business_stage",
            sa.String(50),
            nullable=True,
            comment="idea, early, growing, scaling",
        ),
    )
    op.add_column(
        "user_context",
        sa.Column(
            "primary_objective",
            sa.String(100),
            nullable=True,
            comment="acquire_customers, improve_retention, raise_capital, launch_product, reduce_costs",
        ),
    )

    # Industry and market
    op.add_column("user_context", sa.Column("industry", sa.String(100), nullable=True))
    op.add_column(
        "user_context",
        sa.Column(
            "product_categories",
            JSONB,
            nullable=True,
            comment="Array of product/service categories",
        ),
    )
    op.add_column("user_context", sa.Column("pricing_model", sa.String(100), nullable=True))

    # Brand attributes
    op.add_column("user_context", sa.Column("brand_positioning", sa.Text, nullable=True))
    op.add_column("user_context", sa.Column("brand_tone", sa.String(100), nullable=True))
    op.add_column(
        "user_context",
        sa.Column(
            "brand_maturity",
            sa.String(50),
            nullable=True,
            comment="startup, emerging, established, mature",
        ),
    )

    # Tech and SEO
    op.add_column(
        "user_context",
        sa.Column("tech_stack", JSONB, nullable=True, comment="Detected technologies"),
    )
    op.add_column(
        "user_context",
        sa.Column("seo_structure", JSONB, nullable=True, comment="SEO metadata from website"),
    )

    # Market intelligence
    op.add_column(
        "user_context",
        sa.Column(
            "detected_competitors", JSONB, nullable=True, comment="Auto-detected competitors"
        ),
    )
    op.add_column("user_context", sa.Column("ideal_customer_profile", sa.Text, nullable=True))
    op.add_column(
        "user_context",
        sa.Column("keywords", JSONB, nullable=True, comment="Market category keywords"),
    )

    # Target market details
    op.add_column("user_context", sa.Column("target_geography", sa.String(255), nullable=True))
    op.add_column(
        "user_context",
        sa.Column(
            "traffic_range",
            sa.String(50),
            nullable=True,
            comment="e.g., <1k, 1k-10k, 10k-100k, 100k+",
        ),
    )
    op.add_column(
        "user_context",
        sa.Column(
            "mau_bucket", sa.String(50), nullable=True, comment="Monthly active users bucket"
        ),
    )
    op.add_column(
        "user_context",
        sa.Column(
            "revenue_stage",
            sa.String(50),
            nullable=True,
            comment="pre-revenue, early, growth, mature",
        ),
    )

    # Value proposition and team
    op.add_column("user_context", sa.Column("main_value_proposition", sa.Text, nullable=True))
    op.add_column(
        "user_context",
        sa.Column(
            "team_size",
            sa.String(50),
            nullable=True,
            comment="solo, small (2-5), medium (6-20), large (20+)",
        ),
    )

    # Constraints
    op.add_column("user_context", sa.Column("budget_constraints", sa.Text, nullable=True))
    op.add_column("user_context", sa.Column("time_constraints", sa.Text, nullable=True))
    op.add_column("user_context", sa.Column("regulatory_constraints", sa.Text, nullable=True))

    # Enrichment tracking
    op.add_column(
        "user_context",
        sa.Column(
            "enrichment_source",
            sa.String(50),
            nullable=True,
            comment="manual, api, scrape",
        ),
    )
    op.add_column(
        "user_context",
        sa.Column("enrichment_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_context",
        sa.Column("last_refresh_prompt", sa.DateTime(timezone=True), nullable=True),
    )

    # Onboarding status
    op.add_column(
        "user_context",
        sa.Column("onboarding_completed", sa.Boolean, server_default="false", nullable=False),
    )
    op.add_column(
        "user_context",
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add check constraints for enum-like fields
    op.create_check_constraint(
        "user_context_business_stage_check",
        "user_context",
        "business_stage IS NULL OR business_stage IN ('idea', 'early', 'growing', 'scaling')",
    )
    op.create_check_constraint(
        "user_context_primary_objective_check",
        "user_context",
        "primary_objective IS NULL OR primary_objective IN ('acquire_customers', 'improve_retention', 'raise_capital', 'launch_product', 'reduce_costs')",
    )
    op.create_check_constraint(
        "user_context_enrichment_source_check",
        "user_context",
        "enrichment_source IS NULL OR enrichment_source IN ('manual', 'api', 'scrape')",
    )

    # ==========================================================================
    # Create user_onboarding table for tour tracking
    # ==========================================================================
    op.create_table(
        "user_onboarding",
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
            unique=True,
        ),
        # Tour tracking
        sa.Column("tour_completed", sa.Boolean, server_default="false", nullable=False),
        sa.Column("tour_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "steps_completed",
            JSONB,
            server_default="[]",
            nullable=False,
            comment="Array of completed step names: business_context, first_meeting, expert_panel, results",
        ),
        # First meeting tracking
        sa.Column("first_meeting_id", sa.String(255), nullable=True),
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
    )

    # Index for fast lookup
    op.create_index("idx_user_onboarding_user_id", "user_onboarding", ["user_id"])

    # Enable RLS
    op.execute("ALTER TABLE user_onboarding ENABLE ROW LEVEL SECURITY")

    # RLS policy for user_onboarding (users can only see their own)
    op.execute("""
        CREATE POLICY user_onboarding_own_data ON user_onboarding
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', true))
        WITH CHECK (user_id = current_setting('app.current_user_id', true));
    """)


def downgrade() -> None:
    """Remove extended business context fields and onboarding table."""
    # Drop user_onboarding table
    op.execute("DROP POLICY IF EXISTS user_onboarding_own_data ON user_onboarding")
    op.drop_index("idx_user_onboarding_user_id", table_name="user_onboarding")
    op.drop_table("user_onboarding")

    # Drop check constraints
    op.drop_constraint("user_context_enrichment_source_check", "user_context", type_="check")
    op.drop_constraint("user_context_primary_objective_check", "user_context", type_="check")
    op.drop_constraint("user_context_business_stage_check", "user_context", type_="check")

    # Drop columns from user_context (in reverse order of addition)
    columns_to_drop = [
        "onboarding_completed_at",
        "onboarding_completed",
        "last_refresh_prompt",
        "enrichment_date",
        "enrichment_source",
        "regulatory_constraints",
        "time_constraints",
        "budget_constraints",
        "team_size",
        "main_value_proposition",
        "revenue_stage",
        "mau_bucket",
        "traffic_range",
        "target_geography",
        "keywords",
        "ideal_customer_profile",
        "detected_competitors",
        "seo_structure",
        "tech_stack",
        "brand_maturity",
        "brand_tone",
        "brand_positioning",
        "pricing_model",
        "product_categories",
        "industry",
        "primary_objective",
        "business_stage",
        "company_name",
    ]

    for column in columns_to_drop:
        op.drop_column("user_context", column)
