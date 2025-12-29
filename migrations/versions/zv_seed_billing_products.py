"""Seed billing tables from existing PlanConfig.

Migrates data from hardcoded bo1/billing/config.py to database.

Revision ID: zv_seed_billing_products
Revises: zu_billing_products
Create Date: 2025-12-29
"""

import os
from collections.abc import Sequence

from alembic import op

revision: str = "zv_seed_billing_products"
down_revision: str | Sequence[str] | None = "zu_billing_products"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Seed billing products and prices from existing config."""
    # Subscription products (from PlanConfig.TIERS)
    products = [
        {
            "slug": "free",
            "name": "Free",
            "description": "Perfect for trying out Board of One",
            "type": "subscription",
            "meetings_monthly": 3,
            "datasets_total": 5,
            "mentor_daily": 10,
            "api_daily": 0,
            "features": '{"meetings": true, "datasets": true, "mentor": true, "api_access": false, "priority_support": false, "advanced_analytics": false, "custom_personas": false, "session_export": true, "session_sharing": true, "seo_tools": true, "peer_benchmarks": true}',
            "display_order": 1,
            "highlighted": False,
            "price_cents": 0,
            "interval": "month",
        },
        {
            "slug": "starter",
            "name": "Starter",
            "description": "For growing businesses making regular decisions",
            "type": "subscription",
            "meetings_monthly": 20,
            "datasets_total": 25,
            "mentor_daily": 50,
            "api_daily": 100,
            "features": '{"meetings": true, "datasets": true, "mentor": true, "api_access": true, "priority_support": false, "advanced_analytics": true, "custom_personas": false, "session_export": true, "session_sharing": true, "seo_tools": true, "peer_benchmarks": true}',
            "display_order": 2,
            "highlighted": True,
            "price_cents": 2900,  # £29
            "interval": "month",
        },
        {
            "slug": "pro",
            "name": "Pro",
            "description": "For power users and teams requiring unlimited access",
            "type": "subscription",
            "meetings_monthly": -1,  # Unlimited
            "datasets_total": 100,
            "mentor_daily": -1,  # Unlimited
            "api_daily": 1000,
            "features": '{"meetings": true, "datasets": true, "mentor": true, "api_access": true, "priority_support": true, "advanced_analytics": true, "custom_personas": true, "session_export": true, "session_sharing": true, "seo_tools": true, "peer_benchmarks": true}',
            "display_order": 3,
            "highlighted": False,
            "price_cents": 9900,  # £99
            "interval": "month",
        },
        {
            "slug": "enterprise",
            "name": "Enterprise",
            "description": "Custom solutions for large organizations",
            "type": "subscription",
            "meetings_monthly": -1,
            "datasets_total": 100,
            "mentor_daily": -1,
            "api_daily": 1000,
            "features": '{"meetings": true, "datasets": true, "mentor": true, "api_access": true, "priority_support": true, "advanced_analytics": true, "custom_personas": true, "session_export": true, "session_sharing": true, "seo_tools": true, "peer_benchmarks": true}',
            "display_order": 4,
            "highlighted": False,
            "price_cents": 0,  # Custom pricing
            "interval": "month",
        },
    ]

    # Meeting bundles (from PlanConfig.MEETING_BUNDLES)
    bundles = [
        {
            "slug": "bundle-1",
            "name": "1 Meeting",
            "description": "Try a single meeting",
            "meetings": 1,
            "price_cents": 1000,
            "display_order": 10,
        },
        {
            "slug": "bundle-3",
            "name": "3 Meetings",
            "description": "Perfect for occasional use",
            "meetings": 3,
            "price_cents": 3000,
            "display_order": 11,
        },
        {
            "slug": "bundle-5",
            "name": "5 Meetings",
            "description": "Most popular bundle",
            "meetings": 5,
            "price_cents": 5000,
            "display_order": 12,
        },
        {
            "slug": "bundle-9",
            "name": "9 Meetings",
            "description": "Best value for teams",
            "meetings": 9,
            "price_cents": 9000,
            "display_order": 13,
        },
    ]

    # Get Stripe price IDs from environment (will be NULL if not set)
    stripe_price_starter = os.environ.get("STRIPE_PRICE_STARTER")
    stripe_price_pro = os.environ.get("STRIPE_PRICE_PRO")
    stripe_bundle_1 = os.environ.get("STRIPE_PRICE_BUNDLE_1")
    stripe_bundle_3 = os.environ.get("STRIPE_PRICE_BUNDLE_3")
    stripe_bundle_5 = os.environ.get("STRIPE_PRICE_BUNDLE_5")
    stripe_bundle_9 = os.environ.get("STRIPE_PRICE_BUNDLE_9")

    stripe_prices = {
        "starter": stripe_price_starter,
        "pro": stripe_price_pro,
        "bundle-1": stripe_bundle_1,
        "bundle-3": stripe_bundle_3,
        "bundle-5": stripe_bundle_5,
        "bundle-9": stripe_bundle_9,
    }

    # Insert subscription products
    for p in products:
        stripe_price_id = stripe_prices.get(p["slug"])

        op.execute(f"""
            INSERT INTO billing_products (slug, name, description, type, meetings_monthly, datasets_total, mentor_daily, api_daily, features, display_order, highlighted)
            VALUES ('{p["slug"]}', '{p["name"]}', '{p["description"]}', '{p["type"]}', {p["meetings_monthly"]}, {p["datasets_total"]}, {p["mentor_daily"]}, {p["api_daily"]}, '{p["features"]}'::jsonb, {p["display_order"]}, {str(p["highlighted"]).lower()})
        """)

        # Insert price for this product
        stripe_clause = f"'{stripe_price_id}'" if stripe_price_id else "NULL"
        synced_clause = "NOW()" if stripe_price_id else "NULL"

        op.execute(f"""
            INSERT INTO billing_prices (product_id, amount_cents, currency, interval, stripe_price_id, stripe_synced_at)
            SELECT id, {p["price_cents"]}, 'GBP', '{p["interval"]}', {stripe_clause}, {synced_clause}
            FROM billing_products WHERE slug = '{p["slug"]}'
        """)

    # Insert bundle products
    for b in bundles:
        stripe_price_id = stripe_prices.get(b["slug"])
        stripe_clause = f"'{stripe_price_id}'" if stripe_price_id else "NULL"
        synced_clause = "NOW()" if stripe_price_id else "NULL"

        # Bundle features - just the meeting credits
        features = f'{{"meetings_credits": {b["meetings"]}}}'

        op.execute(f"""
            INSERT INTO billing_products (slug, name, description, type, meetings_monthly, features, display_order)
            VALUES ('{b["slug"]}', '{b["name"]}', '{b["description"]}', 'one_time', {b["meetings"]}, '{features}'::jsonb, {b["display_order"]})
        """)

        op.execute(f"""
            INSERT INTO billing_prices (product_id, amount_cents, currency, interval, stripe_price_id, stripe_synced_at)
            SELECT id, {b["price_cents"]}, 'GBP', NULL, {stripe_clause}, {synced_clause}
            FROM billing_products WHERE slug = '{b["slug"]}'
        """)


def downgrade() -> None:
    """Remove seeded data."""
    op.execute("DELETE FROM billing_prices")
    op.execute("DELETE FROM billing_products")
