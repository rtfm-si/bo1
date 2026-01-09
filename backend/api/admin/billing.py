"""Admin billing management endpoints.

CRUD operations for billing products, prices, and Stripe sync.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.api.middleware.auth import require_admin
from backend.api.utils.errors import http_error
from bo1.logging import ErrorCode
from bo1.state.database import db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["admin-billing"])


# =============================================================================
# Models
# =============================================================================


class ProductFeatures(BaseModel):
    """Feature flags for a product."""

    meetings: bool = True
    datasets: bool = True
    mentor: bool = True
    api_access: bool = False
    priority_support: bool = False
    advanced_analytics: bool = False
    custom_personas: bool = False
    session_export: bool = True
    session_sharing: bool = True
    seo_tools: bool = True
    peer_benchmarks: bool = True


class BillingPrice(BaseModel):
    """Price for a product."""

    id: UUID
    product_id: UUID
    amount_cents: int
    currency: str = "GBP"
    interval: str | None = None  # 'month', 'year', or None for one-time
    stripe_price_id: str | None = None
    stripe_product_id: str | None = None
    stripe_synced_at: datetime | None = None
    active: bool = True


class BillingProduct(BaseModel):
    """Product definition."""

    id: UUID
    slug: str
    name: str
    description: str | None = None
    type: str  # 'subscription' or 'one_time'
    meetings_monthly: int = 0
    datasets_total: int = 0
    mentor_daily: int = 0
    api_daily: int = 0
    features: dict[str, Any] = Field(default_factory=dict)
    display_order: int = 0
    highlighted: bool = False
    active: bool = True
    prices: list[BillingPrice] = Field(default_factory=list)
    sync_status: str = "unknown"  # 'synced', 'out_of_sync', 'not_synced'


class ProductCreate(BaseModel):
    """Create a new product."""

    slug: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    type: str = Field(..., pattern="^(subscription|one_time)$")
    meetings_monthly: int = 0
    datasets_total: int = 0
    mentor_daily: int = 0
    api_daily: int = 0
    features: dict[str, Any] = Field(default_factory=dict)
    display_order: int = 0
    highlighted: bool = False


class ProductUpdate(BaseModel):
    """Update an existing product."""

    name: str | None = None
    description: str | None = None
    meetings_monthly: int | None = None
    datasets_total: int | None = None
    mentor_daily: int | None = None
    api_daily: int | None = None
    features: dict[str, Any] | None = None
    display_order: int | None = None
    highlighted: bool | None = None
    active: bool | None = None


class PriceCreate(BaseModel):
    """Create a new price for a product."""

    product_id: UUID
    amount_cents: int = Field(..., ge=0)
    currency: str = "GBP"
    interval: str | None = Field(None, pattern="^(month|year)$")


class PriceUpdate(BaseModel):
    """Update a price."""

    amount_cents: int | None = Field(None, ge=0)
    active: bool | None = None


class SyncResult(BaseModel):
    """Result of a Stripe sync operation."""

    success: bool
    synced_products: int = 0
    synced_prices: int = 0
    errors: list[str] = Field(default_factory=list)


class BillingConfigResponse(BaseModel):
    """Full billing configuration."""

    products: list[BillingProduct]
    last_sync: datetime | None = None


# =============================================================================
# Helper Functions
# =============================================================================


def _get_sync_status(price: dict) -> str:
    """Determine sync status for a price."""
    if not price.get("stripe_price_id"):
        return "not_synced"
    if price.get("stripe_synced_at"):
        # Could check if local updated_at > stripe_synced_at
        return "synced"
    return "out_of_sync"


def _load_products_with_prices() -> list[BillingProduct]:
    """Load all products with their prices."""
    with db_session() as conn:
        with conn.cursor() as cur:
            # Get all products
            cur.execute("""
                SELECT id, slug, name, description, type,
                       meetings_monthly, datasets_total, mentor_daily, api_daily,
                       features, display_order, highlighted, active, updated_at
                FROM billing_products
                ORDER BY display_order, name
            """)
            products_rows = cur.fetchall()

            # Get all prices
            cur.execute("""
                SELECT id, product_id, amount_cents, currency, interval,
                       stripe_price_id, stripe_product_id, stripe_synced_at, active
                FROM billing_prices
                ORDER BY product_id, created_at
            """)
            prices_rows = cur.fetchall()

            # Group prices by product
            prices_by_product: dict[str, list[dict]] = {}
            for p in prices_rows:
                pid = str(p["product_id"])
                if pid not in prices_by_product:
                    prices_by_product[pid] = []
                prices_by_product[pid].append(dict(p))

            # Build response
            products = []
            for row in products_rows:
                pid = str(row["id"])
                product_prices = prices_by_product.get(pid, [])

                # Determine overall sync status
                if not product_prices:
                    sync_status = "not_synced"
                elif all(
                    p.get("stripe_price_id") and p.get("stripe_synced_at") for p in product_prices
                ):
                    sync_status = "synced"
                elif any(p.get("stripe_price_id") for p in product_prices):
                    sync_status = "out_of_sync"
                else:
                    sync_status = "not_synced"

                products.append(
                    BillingProduct(
                        id=row["id"],
                        slug=row["slug"],
                        name=row["name"],
                        description=row["description"],
                        type=row["type"],
                        meetings_monthly=row["meetings_monthly"] or 0,
                        datasets_total=row["datasets_total"] or 0,
                        mentor_daily=row["mentor_daily"] or 0,
                        api_daily=row["api_daily"] or 0,
                        features=row["features"] or {},
                        display_order=row["display_order"] or 0,
                        highlighted=row["highlighted"] or False,
                        active=row["active"],
                        prices=[BillingPrice(**p) for p in product_prices],
                        sync_status=sync_status,
                    )
                )

            return products


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/products",
    response_model=BillingConfigResponse,
    summary="List all billing products",
)
async def list_products(
    _user: dict = Depends(require_admin),
) -> BillingConfigResponse:
    """Get all billing products with prices and sync status."""
    products = _load_products_with_prices()

    # Get last sync time
    last_sync = None
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(stripe_synced_at) FROM billing_prices")
            result = cur.fetchone()
            if result:
                last_sync = result["max"]

    return BillingConfigResponse(products=products, last_sync=last_sync)


@router.post(
    "/products",
    response_model=BillingProduct,
    summary="Create a billing product",
)
async def create_product(
    data: ProductCreate,
    _user: dict = Depends(require_admin),
) -> BillingProduct:
    """Create a new billing product."""
    import json

    with db_session() as conn:
        with conn.cursor() as cur:
            # Check slug uniqueness
            cur.execute("SELECT id FROM billing_products WHERE slug = %s", (data.slug,))
            if cur.fetchone():
                raise http_error(
                    ErrorCode.VALIDATION_ERROR,
                    f"Product with slug '{data.slug}' already exists",
                    status=400,
                )

            # Insert product
            cur.execute(
                """
                INSERT INTO billing_products
                    (slug, name, description, type, meetings_monthly, datasets_total,
                     mentor_daily, api_daily, features, display_order, highlighted)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, slug, name, description, type, meetings_monthly, datasets_total,
                          mentor_daily, api_daily, features, display_order, highlighted, active
            """,
                (
                    data.slug,
                    data.name,
                    data.description,
                    data.type,
                    data.meetings_monthly,
                    data.datasets_total,
                    data.mentor_daily,
                    data.api_daily,
                    json.dumps(data.features),
                    data.display_order,
                    data.highlighted,
                ),
            )
            row = cur.fetchone()
            conn.commit()

            logger.info(f"Created billing product: {data.slug}")

            return BillingProduct(
                id=row["id"],
                slug=row["slug"],
                name=row["name"],
                description=row["description"],
                type=row["type"],
                meetings_monthly=row["meetings_monthly"] or 0,
                datasets_total=row["datasets_total"] or 0,
                mentor_daily=row["mentor_daily"] or 0,
                api_daily=row["api_daily"] or 0,
                features=row["features"] or {},
                display_order=row["display_order"] or 0,
                highlighted=row["highlighted"] or False,
                active=row["active"],
                prices=[],
                sync_status="not_synced",
            )


@router.put(
    "/products/{product_id}",
    response_model=BillingProduct,
    summary="Update a billing product",
)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    _user: dict = Depends(require_admin),
) -> BillingProduct:
    """Update an existing billing product."""
    import json

    with db_session() as conn:
        with conn.cursor() as cur:
            # Check exists
            cur.execute("SELECT id FROM billing_products WHERE id = %s", (str(product_id),))
            if not cur.fetchone():
                raise http_error(ErrorCode.API_NOT_FOUND, "Product not found", status=404)

            # Build update
            updates = []
            values = []
            if data.name is not None:
                updates.append("name = %s")
                values.append(data.name)
            if data.description is not None:
                updates.append("description = %s")
                values.append(data.description)
            if data.meetings_monthly is not None:
                updates.append("meetings_monthly = %s")
                values.append(data.meetings_monthly)
            if data.datasets_total is not None:
                updates.append("datasets_total = %s")
                values.append(data.datasets_total)
            if data.mentor_daily is not None:
                updates.append("mentor_daily = %s")
                values.append(data.mentor_daily)
            if data.api_daily is not None:
                updates.append("api_daily = %s")
                values.append(data.api_daily)
            if data.features is not None:
                updates.append("features = %s")
                values.append(json.dumps(data.features))
            if data.display_order is not None:
                updates.append("display_order = %s")
                values.append(data.display_order)
            if data.highlighted is not None:
                updates.append("highlighted = %s")
                values.append(data.highlighted)
            if data.active is not None:
                updates.append("active = %s")
                values.append(data.active)

            if updates:
                updates.append("updated_at = NOW()")
                values.append(str(product_id))
                cur.execute(
                    f"""
                    UPDATE billing_products
                    SET {", ".join(updates)}
                    WHERE id = %s
                """,  # nosec B608 - updates built from hardcoded column names
                    values,
                )
                conn.commit()

            logger.info(f"Updated billing product: {product_id}")

    # Return updated product
    products = _load_products_with_prices()
    for p in products:
        if p.id == product_id:
            return p

    raise http_error(ErrorCode.API_NOT_FOUND, "Product not found after update", status=404)


@router.delete(
    "/products/{product_id}",
    summary="Delete a billing product",
)
async def delete_product(
    product_id: UUID,
    _user: dict = Depends(require_admin),
) -> dict:
    """Soft-delete a billing product."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE billing_products SET active = FALSE, updated_at = NOW()
                WHERE id = %s
                RETURNING slug
            """,
                (str(product_id),),
            )
            result = cur.fetchone()
            conn.commit()

            if not result:
                raise http_error(ErrorCode.API_NOT_FOUND, "Product not found", status=404)

            logger.info(f"Deleted billing product: {result['slug']}")
            return {"success": True, "slug": result["slug"]}


@router.post(
    "/prices",
    response_model=BillingPrice,
    summary="Create a price for a product",
)
async def create_price(
    data: PriceCreate,
    _user: dict = Depends(require_admin),
) -> BillingPrice:
    """Create a new price for a product."""
    with db_session() as conn:
        with conn.cursor() as cur:
            # Check product exists
            cur.execute("SELECT id FROM billing_products WHERE id = %s", (str(data.product_id),))
            if not cur.fetchone():
                raise http_error(ErrorCode.API_NOT_FOUND, "Product not found", status=404)

            cur.execute(
                """
                INSERT INTO billing_prices (product_id, amount_cents, currency, interval)
                VALUES (%s, %s, %s, %s)
                RETURNING id, product_id, amount_cents, currency, interval,
                          stripe_price_id, stripe_product_id, stripe_synced_at, active
            """,
                (str(data.product_id), data.amount_cents, data.currency, data.interval),
            )
            row = cur.fetchone()
            conn.commit()

            logger.info(
                f"Created price for product {data.product_id}: {data.amount_cents} {data.currency}"
            )

            return BillingPrice(**row)


@router.put(
    "/prices/{price_id}",
    response_model=BillingPrice,
    summary="Update a price",
)
async def update_price(
    price_id: UUID,
    data: PriceUpdate,
    _user: dict = Depends(require_admin),
) -> BillingPrice:
    """Update a price. Note: Stripe prices are immutable, so changing amount requires new Stripe price."""
    with db_session() as conn:
        with conn.cursor() as cur:
            updates = []
            values = []

            if data.amount_cents is not None:
                updates.append("amount_cents = %s")
                values.append(data.amount_cents)
                # Clear Stripe sync since price changed
                updates.append("stripe_synced_at = NULL")

            if data.active is not None:
                updates.append("active = %s")
                values.append(data.active)

            if updates:
                values.append(str(price_id))
                cur.execute(
                    f"""
                    UPDATE billing_prices
                    SET {", ".join(updates)}
                    WHERE id = %s
                    RETURNING id, product_id, amount_cents, currency, interval,
                              stripe_price_id, stripe_product_id, stripe_synced_at, active
                """,  # nosec B608 - updates built from hardcoded column names
                    values,
                )
                row = cur.fetchone()
                conn.commit()

                if not row:
                    raise http_error(ErrorCode.API_NOT_FOUND, "Price not found", status=404)

                return BillingPrice(**row)

            raise http_error(ErrorCode.VALIDATION_ERROR, "No updates provided", status=400)


class StripeConfigStatusResponse(BaseModel):
    """Stripe configuration status."""

    configured: bool
    mode: str | None = None  # 'test', 'live', or None
    error: str | None = None


@router.get(
    "/stripe/status",
    response_model=StripeConfigStatusResponse,
    summary="Check Stripe API key configuration",
)
async def get_stripe_config_status(
    _user: dict = Depends(require_admin),
) -> StripeConfigStatusResponse:
    """Check if Stripe API key is configured and valid."""
    from backend.services.billing_sync import BillingSyncService

    sync_service = BillingSyncService()
    status = sync_service.validate_stripe_key()
    return StripeConfigStatusResponse(**status.to_dict())


@router.post(
    "/sync/stripe",
    response_model=SyncResult,
    summary="Sync all products/prices to Stripe",
)
async def sync_to_stripe(
    _user: dict = Depends(require_admin),
) -> SyncResult:
    """Sync all billing products and prices to Stripe."""
    import stripe as stripe_lib

    from backend.services.billing_sync import BillingSyncService

    try:
        sync_service = BillingSyncService()
        result = sync_service.sync_all_to_stripe()
        return result
    except ValueError as e:
        # Missing config
        logger.warning(f"Stripe sync failed: {e}")
        return SyncResult(
            success=False,
            errors=[f"STRIPE_NOT_CONFIGURED: {e}. Set STRIPE_SECRET_KEY environment variable."],
        )
    except stripe_lib.error.AuthenticationError as e:
        # Invalid API key (401)
        logger.warning(f"Stripe authentication failed: {e}")
        return SyncResult(
            success=False,
            errors=[
                "STRIPE_AUTH_FAILED: Invalid Stripe API key. "
                "Check that STRIPE_SECRET_KEY is correct and not expired."
            ],
        )
    except stripe_lib.error.APIConnectionError as e:
        logger.error(f"Stripe connection failed: {e}")
        return SyncResult(
            success=False,
            errors=[f"STRIPE_CONNECTION_ERROR: Cannot reach Stripe API. {e}"],
        )
    except Exception as e:
        logger.exception("Stripe sync failed")
        return SyncResult(success=False, errors=[str(e)])


@router.get(
    "/sync/status",
    summary="Get sync status",
)
async def get_sync_status(
    _user: dict = Depends(require_admin),
) -> dict:
    """Get current sync status between local DB and Stripe."""
    products = _load_products_with_prices()

    synced = sum(1 for p in products if p.sync_status == "synced")
    out_of_sync = sum(1 for p in products if p.sync_status == "out_of_sync")
    not_synced = sum(1 for p in products if p.sync_status == "not_synced")

    return {
        "total_products": len(products),
        "synced": synced,
        "out_of_sync": out_of_sync,
        "not_synced": not_synced,
        "all_synced": synced == len(products) and len(products) > 0,
    }


# =============================================================================
# Public endpoint for frontend pricing display
# =============================================================================


@router.get(
    "/public/products",
    response_model=list[BillingProduct],
    summary="Get active products for public display",
)
async def get_public_products() -> list[BillingProduct]:
    """Get active billing products for frontend pricing display. No auth required."""
    products = _load_products_with_prices()
    # Filter to only active products with active prices
    return [p for p in products if p.active and any(pr.active for pr in p.prices)]
