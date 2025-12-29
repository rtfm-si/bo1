"""Billing sync service for Stripe integration.

Syncs local billing_products and billing_prices to Stripe.
Provider-agnostic design - can add other providers later.
"""

import logging
import os
from dataclasses import dataclass

import stripe

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    synced_products: int = 0
    synced_prices: int = 0
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        """Initialize errors list if not provided."""
        if self.errors is None:
            self.errors = []


class BillingSyncService:
    """Service for syncing billing products/prices to payment providers."""

    def __init__(self) -> None:
        """Initialize with Stripe API key."""
        self.stripe_api_key = os.environ.get("STRIPE_SECRET_KEY")
        if self.stripe_api_key:
            stripe.api_key = self.stripe_api_key

    def _ensure_stripe_configured(self) -> None:
        """Raise error if Stripe is not configured."""
        if not self.stripe_api_key:
            raise ValueError("STRIPE_SECRET_KEY not configured")

    def sync_all_to_stripe(self) -> SyncResult:
        """Sync all products and prices to Stripe.

        For each product:
        1. Create or update Stripe product
        2. For each price, create new Stripe price (prices are immutable in Stripe)
        3. Archive old Stripe prices
        4. Update local DB with Stripe IDs
        """
        self._ensure_stripe_configured()

        result = SyncResult(success=True)

        # Load all products and prices
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, slug, name, description, type, active
                    FROM billing_products
                    WHERE active = TRUE
                    ORDER BY display_order
                """)
                products = cur.fetchall()

        for product in products:
            try:
                self._sync_product_to_stripe(product, result)
            except Exception as e:
                logger.exception(f"Failed to sync product {product['slug']}")
                result.errors.append(f"Product {product['slug']}: {e}")
                result.success = False

        return result

    def _sync_product_to_stripe(self, product: dict, result: SyncResult) -> None:
        """Sync a single product and its prices to Stripe."""
        product_id = product["id"]
        slug = product["slug"]

        # Load prices for this product
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, amount_cents, currency, interval,
                           stripe_price_id, stripe_product_id
                    FROM billing_prices
                    WHERE product_id = %s AND active = TRUE
                """,
                    (str(product_id),),
                )
                prices = cur.fetchall()

        if not prices:
            logger.info(f"No active prices for product {slug}, skipping")
            return

        # Check if Stripe product exists
        existing_stripe_product_id = None
        for p in prices:
            if p["stripe_product_id"]:
                existing_stripe_product_id = p["stripe_product_id"]
                break

        # Create or update Stripe product
        stripe_product = self._ensure_stripe_product(
            existing_stripe_product_id,
            name=product["name"],
            description=product["description"],
            metadata={"bo1_product_id": str(product_id), "bo1_slug": slug},
        )
        result.synced_products += 1

        # Sync each price
        for price in prices:
            self._sync_price_to_stripe(price, stripe_product.id, result)

    def _ensure_stripe_product(
        self,
        existing_id: str | None,
        name: str,
        description: str | None,
        metadata: dict,
    ) -> stripe.Product:
        """Create or update a Stripe product."""
        if existing_id:
            try:
                # Update existing product
                product = stripe.Product.modify(
                    existing_id,
                    name=name,
                    description=description or "",
                    metadata=metadata,
                )
                logger.info(f"Updated Stripe product: {existing_id}")
                return product
            except stripe.error.InvalidRequestError:
                # Product doesn't exist, create new
                pass

        # Create new product
        product = stripe.Product.create(
            name=name,
            description=description or "",
            metadata=metadata,
        )
        logger.info(f"Created Stripe product: {product.id}")
        return product

    def _sync_price_to_stripe(
        self,
        price: dict,
        stripe_product_id: str,
        result: SyncResult,
    ) -> None:
        """Sync a single price to Stripe.

        Stripe prices are immutable, so we:
        1. Check if existing price matches
        2. If not, create new price and archive old one
        3. Update local DB
        """
        price_id = price["id"]
        amount = price["amount_cents"]
        currency = price["currency"].lower()
        interval = price["interval"]
        existing_stripe_price_id = price["stripe_price_id"]

        # Check if existing Stripe price matches
        if existing_stripe_price_id:
            try:
                existing_price = stripe.Price.retrieve(existing_stripe_price_id)
                matches = (
                    existing_price.unit_amount == amount
                    and existing_price.currency == currency
                    and (
                        (interval is None and existing_price.type == "one_time")
                        or (
                            interval
                            and existing_price.recurring
                            and existing_price.recurring.interval == interval
                        )
                    )
                )
                if matches and existing_price.active:
                    # Price matches and is active, just update sync time
                    self._update_price_sync(price_id, existing_stripe_price_id, stripe_product_id)
                    result.synced_prices += 1
                    return

                # Price doesn't match or is inactive, archive it
                if existing_price.active:
                    stripe.Price.modify(existing_stripe_price_id, active=False)
                    logger.info(f"Archived old Stripe price: {existing_stripe_price_id}")

            except stripe.error.InvalidRequestError:
                # Price doesn't exist in Stripe
                pass

        # Create new Stripe price
        price_data = {
            "product": stripe_product_id,
            "unit_amount": amount,
            "currency": currency,
            "metadata": {"bo1_price_id": str(price_id)},
        }

        if interval:
            price_data["recurring"] = {"interval": interval}

        new_stripe_price = stripe.Price.create(**price_data)
        logger.info(f"Created Stripe price: {new_stripe_price.id}")

        # Update local DB
        self._update_price_sync(price_id, new_stripe_price.id, stripe_product_id)
        result.synced_prices += 1

    def _update_price_sync(
        self,
        price_id: str,
        stripe_price_id: str,
        stripe_product_id: str,
    ) -> None:
        """Update local price record with Stripe IDs."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE billing_prices
                    SET stripe_price_id = %s,
                        stripe_product_id = %s,
                        stripe_synced_at = NOW()
                    WHERE id = %s
                """,
                    (stripe_price_id, stripe_product_id, str(price_id)),
                )
                conn.commit()

    def sync_promotion_to_stripe(self, promotion_id: str) -> str | None:
        """Sync a promotion to Stripe as a coupon.

        Returns the Stripe coupon ID or None if sync failed.
        """
        self._ensure_stripe_configured()

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, code, name, type, discount_percent, discount_fixed,
                           max_uses, expires_at, stripe_coupon_id
                    FROM promotions
                    WHERE id = %s
                """,
                    (promotion_id,),
                )
                promo = cur.fetchone()

        if not promo:
            return None

        # Check if coupon already exists
        if promo["stripe_coupon_id"]:
            try:
                stripe.Coupon.retrieve(promo["stripe_coupon_id"])
                return promo["stripe_coupon_id"]
            except stripe.error.InvalidRequestError:
                pass  # Coupon doesn't exist, create new

        # Create Stripe coupon
        coupon_data = {
            "id": promo["code"],  # Use promo code as coupon ID
            "name": promo["name"] or promo["code"],
            "metadata": {"bo1_promotion_id": str(promo["id"])},
        }

        if promo["type"] == "percent" and promo["discount_percent"]:
            coupon_data["percent_off"] = float(promo["discount_percent"])
        elif promo["type"] == "fixed" and promo["discount_fixed"]:
            coupon_data["amount_off"] = int(promo["discount_fixed"])
            coupon_data["currency"] = "gbp"

        if promo["max_uses"]:
            coupon_data["max_redemptions"] = promo["max_uses"]

        if promo["expires_at"]:
            coupon_data["redeem_by"] = int(promo["expires_at"].timestamp())

        try:
            coupon = stripe.Coupon.create(**coupon_data)
            logger.info(f"Created Stripe coupon: {coupon.id}")

            # Update local record
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE promotions
                        SET stripe_coupon_id = %s, stripe_synced_at = NOW()
                        WHERE id = %s
                    """,
                        (coupon.id, promotion_id),
                    )
                    conn.commit()

            return coupon.id

        except stripe.error.InvalidRequestError as e:
            logger.error(f"Failed to create Stripe coupon: {e}")
            return None

    def get_stripe_products(self) -> list[dict]:
        """Fetch all products from Stripe for comparison."""
        self._ensure_stripe_configured()

        products = []
        for product in stripe.Product.list(active=True, limit=100).auto_paging_iter():
            prices = list(stripe.Price.list(product=product.id, active=True, limit=100))
            products.append(
                {
                    "stripe_id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "metadata": product.metadata,
                    "prices": [
                        {
                            "stripe_id": p.id,
                            "amount_cents": p.unit_amount,
                            "currency": p.currency,
                            "interval": p.recurring.interval if p.recurring else None,
                        }
                        for p in prices
                    ],
                }
            )
        return products
