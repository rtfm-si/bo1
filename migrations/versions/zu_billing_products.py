"""Add centralized billing products, prices, and promotions tables.

Moves billing configuration from hardcoded Python/TypeScript to database.
Enables admin UI management and provider-agnostic design.

- billing_products: What we sell (subscriptions, bundles)
- billing_prices: Pricing for products (supports multiple currencies/intervals)
- Updates promotions table with provider sync fields

Revision ID: zu_billing_products
Revises: zt_blog_post_ctr_metrics
Create Date: 2025-12-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "zu_billing_products"
down_revision: str | Sequence[str] | None = "zt_blog_post_ctr_metrics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create billing products and prices tables."""
    # Products table - what we sell
    op.create_table(
        "billing_products",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("slug", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("type", sa.String(20), nullable=False),  # 'subscription' or 'one_time'
        # Feature limits (what customer gets)
        sa.Column("meetings_monthly", sa.Integer, default=0),  # -1 = unlimited
        sa.Column("datasets_total", sa.Integer, default=0),
        sa.Column("mentor_daily", sa.Integer, default=0),
        sa.Column("api_daily", sa.Integer, default=0),
        sa.Column("features", JSONB, server_default="{}"),  # Feature flags
        # Display settings
        sa.Column("display_order", sa.Integer, default=0),
        sa.Column("highlighted", sa.Boolean, server_default="false"),
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Check constraint for valid product types
    op.create_check_constraint(
        "ck_billing_products_type",
        "billing_products",
        "type IN ('subscription', 'one_time')",
    )

    # Indexes
    op.create_index("idx_billing_products_slug", "billing_products", ["slug"])
    op.create_index(
        "idx_billing_products_active",
        "billing_products",
        ["active"],
        postgresql_where=sa.text("active = true"),
    )
    op.create_index("idx_billing_products_type", "billing_products", ["type"])

    # Prices table - pricing for products
    op.create_table(
        "billing_prices",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("billing_products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount_cents", sa.Integer, nullable=False),
        sa.Column("currency", sa.String(3), server_default="GBP"),
        sa.Column("interval", sa.String(20)),  # 'month', 'year', NULL for one-time
        sa.Column("interval_count", sa.Integer, server_default="1"),
        # Provider sync - Stripe
        sa.Column("stripe_price_id", sa.String(100)),
        sa.Column("stripe_product_id", sa.String(100)),
        sa.Column("stripe_synced_at", sa.TIMESTAMP(timezone=True)),
        # Future providers (add columns as needed)
        # sa.Column("paddle_price_id", sa.String(100)),
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Check constraint for valid intervals
    op.create_check_constraint(
        "ck_billing_prices_interval",
        "billing_prices",
        "interval IS NULL OR interval IN ('month', 'year')",
    )

    # Indexes
    op.create_index("idx_billing_prices_product", "billing_prices", ["product_id"])
    op.create_index("idx_billing_prices_stripe", "billing_prices", ["stripe_price_id"])
    op.create_index(
        "idx_billing_prices_active",
        "billing_prices",
        ["active"],
        postgresql_where=sa.text("active = true"),
    )

    # Add provider sync columns to existing promotions table
    op.add_column("promotions", sa.Column("stripe_coupon_id", sa.String(100)))
    op.add_column("promotions", sa.Column("stripe_synced_at", sa.TIMESTAMP(timezone=True)))

    # Index for stripe coupon lookup
    op.create_index("idx_promotions_stripe_coupon", "promotions", ["stripe_coupon_id"])


def downgrade() -> None:
    """Drop billing tables and promotion columns."""
    # Remove promotion columns
    op.drop_index("idx_promotions_stripe_coupon", table_name="promotions")
    op.drop_column("promotions", "stripe_synced_at")
    op.drop_column("promotions", "stripe_coupon_id")

    # Drop prices table
    op.drop_index("idx_billing_prices_active", table_name="billing_prices")
    op.drop_index("idx_billing_prices_stripe", table_name="billing_prices")
    op.drop_index("idx_billing_prices_product", table_name="billing_prices")
    op.drop_constraint("ck_billing_prices_interval", "billing_prices", type_="check")
    op.drop_table("billing_prices")

    # Drop products table
    op.drop_index("idx_billing_products_type", table_name="billing_products")
    op.drop_index("idx_billing_products_active", table_name="billing_products")
    op.drop_index("idx_billing_products_slug", table_name="billing_products")
    op.drop_constraint("ck_billing_products_type", "billing_products", type_="check")
    op.drop_table("billing_products")
