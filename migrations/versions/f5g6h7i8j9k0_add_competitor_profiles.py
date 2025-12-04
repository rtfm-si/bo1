"""Add competitor_profiles table for Competitor Watch feature.

Stores enriched competitor data with tier-based depth:
- Free: 3 competitors, basic data (name, url, tagline)
- Starter: 5 competitors, standard data (+ product, pricing, target market)
- Pro: 8 competitors, deep data (+ value prop, tech stack, news)

Includes monthly refresh tracking and change detection.

Revision ID: f5g6h7i8j9k0
Revises: e4f5g6h7i8j9
Create Date: 2025-12-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "f5g6h7i8j9k0"
down_revision: str | Sequence[str] | None = "e4f5g6h7i8j9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create competitor_profiles table."""
    op.create_table(
        "competitor_profiles",
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
        # Basic tier fields (Free)
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("tagline", sa.Text, nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        # Standard tier fields (Starter)
        sa.Column("product_description", sa.Text, nullable=True),
        sa.Column("pricing_model", sa.String(100), nullable=True),
        sa.Column("target_market", sa.Text, nullable=True),
        sa.Column("business_model", sa.String(100), nullable=True),
        # Deep tier fields (Pro)
        sa.Column("value_proposition", sa.Text, nullable=True),
        sa.Column("tech_stack", JSONB, nullable=True),
        sa.Column("recent_news", JSONB, nullable=True),  # [{title, url, date}]
        sa.Column("funding_info", sa.Text, nullable=True),
        sa.Column("employee_count", sa.String(50), nullable=True),
        # Metadata
        sa.Column("display_order", sa.Integer, server_default="0", nullable=False),
        sa.Column(
            "is_primary",
            sa.Boolean,
            server_default="false",
            nullable=False,
            comment="User's top competitors for focus",
        ),
        sa.Column(
            "data_depth",
            sa.String(20),
            server_default="basic",
            nullable=False,
            comment="basic, standard, deep",
        ),
        sa.Column("source", sa.String(50), server_default="tavily", nullable=False),
        # Change tracking
        sa.Column("last_enriched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "previous_snapshot", JSONB, nullable=True, comment="Previous data for change detection"
        ),
        sa.Column(
            "changes_detected",
            JSONB,
            nullable=True,
            comment="List of fields that changed in last refresh",
        ),
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
        # Unique constraint: one profile per competitor per user
        sa.UniqueConstraint("user_id", "name", name="uq_competitor_profiles_user_name"),
    )

    # Indexes
    op.create_index("idx_competitor_profiles_user_id", "competitor_profiles", ["user_id"])
    op.create_index(
        "idx_competitor_profiles_last_enriched", "competitor_profiles", ["last_enriched_at"]
    )

    # Check constraint for data_depth
    op.create_check_constraint(
        "competitor_profiles_depth_check",
        "competitor_profiles",
        "data_depth IN ('basic', 'standard', 'deep')",
    )

    # Enable RLS
    op.execute("ALTER TABLE competitor_profiles ENABLE ROW LEVEL SECURITY")

    # RLS policy (users can only see/modify their own)
    op.execute("""
        CREATE POLICY competitor_profiles_own_data ON competitor_profiles
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', true))
        WITH CHECK (user_id = current_setting('app.current_user_id', true));
    """)


def downgrade() -> None:
    """Drop competitor_profiles table."""
    op.execute("DROP POLICY IF EXISTS competitor_profiles_own_data ON competitor_profiles")
    op.drop_constraint("competitor_profiles_depth_check", "competitor_profiles", type_="check")
    op.drop_index("idx_competitor_profiles_last_enriched", table_name="competitor_profiles")
    op.drop_index("idx_competitor_profiles_user_id", table_name="competitor_profiles")
    op.drop_table("competitor_profiles")
