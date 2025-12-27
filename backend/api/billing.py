"""Billing API endpoints with Stripe integration.

Provides:
- GET /api/v1/billing/usage - Get usage statistics
- GET /api/v1/billing/plan - Get current plan details
- POST /api/v1/billing/checkout - Create Stripe checkout session
- POST /api/v1/billing/portal - Create Stripe billing portal session
- POST /api/v1/billing/webhook - Handle Stripe webhooks
"""

import hashlib
import logging
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from stripe import SignatureVerificationError

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_email, extract_user_id
from backend.api.utils.db_helpers import get_single_value
from backend.api.utils.errors import handle_api_errors
from bo1.billing import PlanConfig
from bo1.config import get_settings
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.database import db_session
from bo1.state.repositories.user_repository import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])

# Replay attack prevention: reject events older than 5 minutes
WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300


# =============================================================================
# Models
# =============================================================================


class PlanDetails(BaseModel):
    """Current subscription plan details."""

    tier: str = Field(..., description="Subscription tier: free, starter, pro, enterprise")
    name: str = Field(..., description="Display name of the plan")
    price_monthly: int = Field(..., description="Monthly price in cents (0 for free)")
    meetings_limit: int | None = Field(
        None, description="Max meetings per month (null = unlimited)"
    )
    features: list[str] = Field(default_factory=list, description="List of included features")
    billing_cycle_start: datetime | None = Field(None, description="Start of current billing cycle")
    billing_cycle_end: datetime | None = Field(None, description="End of current billing cycle")


class UsageStats(BaseModel):
    """Usage statistics for current billing period."""

    meetings_used: int = Field(0, description="Meetings created this period")
    meetings_limit: int | None = Field(None, description="Max meetings (null = unlimited)")
    meetings_remaining: int | None = Field(
        None, description="Remaining meetings (null = unlimited)"
    )
    api_calls_used: int = Field(0, description="API calls this period")
    total_cost_cents: int = Field(0, description="Total cost incurred in cents")
    period_start: datetime | None = Field(None, description="Start of usage period")
    period_end: datetime | None = Field(None, description="End of usage period")


class BillingPortalResponse(BaseModel):
    """Response from billing portal creation."""

    url: str | None = Field(None, description="Stripe billing portal URL")
    message: str = Field(..., description="Status message")
    available: bool = Field(False, description="Whether billing portal is available")


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""

    price_id: str = Field(..., description="Stripe price ID (price_...)")


class CheckoutResponse(BaseModel):
    """Response from checkout session creation."""

    session_id: str = Field(..., description="Stripe checkout session ID")
    url: str = Field(..., description="Checkout URL to redirect user to")


# =============================================================================
# Plan Configuration (from centralized bo1.billing.config)
# =============================================================================

# Use centralized config - get_plan_config() returns compatible format
PLAN_CONFIG = PlanConfig.get_plan_config()


# =============================================================================
# Helper Functions
# =============================================================================


def _is_event_processed(event_id: str) -> bool:
    """Check if a Stripe event has already been processed (idempotency)."""
    result = get_single_value(
        "SELECT 1 FROM stripe_events WHERE event_id = %s",
        (event_id,),
        column="?column?",
        default=None,
    )
    return result is not None


def _record_event(
    event_id: str,
    event_type: str,
    customer_id: str | None,
    subscription_id: str | None,
    payload: bytes,
) -> None:
    """Record a processed Stripe event for idempotency."""
    payload_hash = hashlib.sha256(payload).hexdigest()
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO stripe_events (event_id, event_type, customer_id, subscription_id, payload_hash)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    (event_id, event_type, customer_id, subscription_id, payload_hash),
                )
    except Exception as e:
        log_error(
            logger,
            ErrorCode.EXT_STRIPE_ERROR,
            f"Failed to record Stripe event {event_id}: {e}",
            event_id=event_id,
        )


def _validate_webhook_timestamp(signature_header: str) -> None:
    """Validate webhook timestamp to prevent replay attacks.

    Raises:
        HTTPException: If timestamp is too old
    """
    # Extract timestamp from Stripe signature header (format: t=timestamp,v1=signature)
    parts = dict(part.split("=", 1) for part in signature_header.split(",") if "=" in part)
    timestamp_str = parts.get("t")

    if not timestamp_str:
        raise HTTPException(status_code=400, detail="Missing timestamp in webhook signature")

    try:
        timestamp = int(timestamp_str)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid timestamp in webhook signature"
        ) from None

    # Check if event is too old (replay attack prevention)
    current_time = int(time.time())
    if current_time - timestamp > WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS:
        logger.warning(
            f"Rejected old webhook event (timestamp: {timestamp}, age: {current_time - timestamp}s)"
        )
        raise HTTPException(status_code=400, detail="Webhook timestamp too old")


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/v1/billing/plan",
    response_model=PlanDetails,
    summary="Get current plan details",
    description="Returns details about the user's current subscription plan.",
)
@handle_api_errors("get billing plan")
async def get_plan(user: dict[str, Any] = Depends(get_current_user)) -> PlanDetails:
    """Get user's current plan details."""
    user_id = extract_user_id(user)

    # Get user's subscription tier from database
    tier = get_single_value(
        "SELECT subscription_tier FROM users WHERE id = %s",
        (user_id,),
        column="subscription_tier",
        default="free",
    )
    config = PLAN_CONFIG.get(tier, PLAN_CONFIG["free"])

    return PlanDetails(
        tier=tier,
        name=config["name"],
        price_monthly=config["price_monthly"],
        meetings_limit=config["meetings_limit"],
        features=config["features"],
        billing_cycle_start=None,  # TODO: Get from Stripe subscription
        billing_cycle_end=None,
    )


@router.get(
    "/v1/billing/usage",
    response_model=UsageStats,
    summary="Get usage statistics",
    description="Returns usage statistics for the current billing period.",
)
@handle_api_errors("get billing usage")
async def get_usage(user: dict[str, Any] = Depends(get_current_user)) -> UsageStats:
    """Get user's usage statistics."""
    user_id = extract_user_id(user)

    # Get meeting count for current month
    meetings_used = get_single_value(
        """
        SELECT COUNT(*) as meeting_count
        FROM sessions
        WHERE user_id = %s
        AND created_at >= date_trunc('month', CURRENT_DATE)
        """,
        (user_id,),
        column="meeting_count",
        default=0,
    )

    # Get user's tier for limit
    tier = get_single_value(
        "SELECT subscription_tier FROM users WHERE id = %s",
        (user_id,),
        column="subscription_tier",
        default="free",
    )

    # Get total cost this month (from api_costs if available)
    total_cost = get_single_value(
        """
        SELECT COALESCE(SUM(total_cost), 0) as total_cost
        FROM api_costs
        WHERE user_id = %s
        AND created_at >= date_trunc('month', CURRENT_DATE)
        """,
        (user_id,),
        column="total_cost",
        default=0.0,
    )

    config = PLAN_CONFIG.get(tier, PLAN_CONFIG["free"])
    meetings_limit = config["meetings_limit"]

    return UsageStats(
        meetings_used=meetings_used,
        meetings_limit=meetings_limit,
        meetings_remaining=(meetings_limit - meetings_used) if meetings_limit else None,
        api_calls_used=0,  # TODO: Track API calls
        total_cost_cents=int(total_cost * 100),  # Convert to cents
        period_start=None,  # TODO: Get from billing cycle
        period_end=None,
    )


@router.post(
    "/v1/billing/checkout",
    response_model=CheckoutResponse,
    summary="Create checkout session",
    description="Creates a Stripe checkout session for subscription upgrade.",
)
@handle_api_errors("create checkout session")
async def create_checkout_session(
    request: CheckoutRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> CheckoutResponse:
    """Create a Stripe checkout session for subscription."""
    from backend.services.stripe_service import stripe_service

    settings = get_settings()
    user_id = extract_user_id(user)
    email = extract_user_email(user)

    # Get existing customer ID if any
    existing_customer_id = user_repository.get_stripe_customer_id(user_id)

    # Get or create Stripe customer
    customer = await stripe_service.get_or_create_customer(
        user_id=user_id,
        email=email,
        existing_customer_id=existing_customer_id,
    )

    # Save customer ID if newly created
    if not existing_customer_id:
        user_repository.save_stripe_customer_id(user_id, customer.id)

    # Build success/cancel URLs
    base_url = settings.frontend_url.rstrip("/")
    success_url = f"{base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/billing/cancel"

    # Create checkout session
    result = await stripe_service.create_checkout_session(
        customer_id=customer.id,
        price_id=request.price_id,
        success_url=success_url,
        cancel_url=cancel_url,
    )

    logger.info(f"Created checkout session {result.session_id} for user {user_id}")

    return CheckoutResponse(
        session_id=result.session_id,
        url=result.url,
    )


@router.post(
    "/v1/billing/portal",
    response_model=BillingPortalResponse,
    summary="Create billing portal session",
    description="Creates a Stripe billing portal session for subscription management.",
)
@handle_api_errors("create billing portal session")
async def create_portal_session(
    user: dict[str, Any] = Depends(get_current_user),
) -> BillingPortalResponse:
    """Create Stripe billing portal session."""
    from backend.services.stripe_service import stripe_service

    settings = get_settings()
    user_id = extract_user_id(user)

    # Get customer ID
    customer_id = user_repository.get_stripe_customer_id(user_id)

    if not customer_id:
        return BillingPortalResponse(
            url=None,
            message="No billing account found. Subscribe to a plan first.",
            available=False,
        )

    # Build return URL
    return_url = f"{settings.frontend_url.rstrip('/')}/settings/billing"

    try:
        result = await stripe_service.create_portal_session(
            customer_id=customer_id,
            return_url=return_url,
        )
        logger.info(f"Created billing portal session for user {user_id}")
        return BillingPortalResponse(
            url=result.url,
            message="Portal session created",
            available=True,
        )
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_BILLING_ERROR,
            f"Failed to create billing portal: {e}",
            user_id=user_id,
        )
        return BillingPortalResponse(
            url=None,
            message="Failed to create billing portal. Please contact support.",
            available=False,
        )


@router.post(
    "/v1/billing/webhook",
    summary="Handle Stripe webhooks",
    description="Receives and processes Stripe webhook events.",
    include_in_schema=False,  # Don't expose in API docs
)
async def handle_stripe_webhook(request: Request) -> dict[str, str]:
    """Handle incoming Stripe webhook events."""
    from backend.services.stripe_service import stripe_service

    # Get raw body for signature verification
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature", "")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    # Validate timestamp to prevent replay attacks
    _validate_webhook_timestamp(signature)

    # Verify signature and construct event
    try:
        event = stripe_service.construct_webhook_event(payload, signature)
    except SignatureVerificationError as e:
        logger.warning(f"Invalid webhook signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature") from None
    except Exception as e:
        log_error(
            logger,
            ErrorCode.EXT_STRIPE_ERROR,
            f"Failed to construct webhook event: {e}",
        )
        raise HTTPException(status_code=400, detail="Invalid payload") from None

    # Idempotency check - skip if already processed
    if _is_event_processed(event.id):
        logger.info(f"Skipping duplicate event {event.id}")
        return {"status": "already_processed"}

    # Extract common fields for event recording
    customer_id: str | None = None
    subscription_id: str | None = None
    event_data = event.data.object

    if hasattr(event_data, "customer"):
        customer_id = event_data.customer
    if hasattr(event_data, "subscription"):
        subscription_id = event_data.subscription
    elif hasattr(event_data, "id") and event.type.startswith("customer.subscription"):
        subscription_id = event_data.id

    # Process event based on type
    try:
        if event.type == "checkout.session.completed":
            await _handle_checkout_completed(event_data)
        elif event.type == "customer.subscription.updated":
            await _handle_subscription_updated(event_data)
        elif event.type == "customer.subscription.deleted":
            await _handle_subscription_deleted(event_data)
        elif event.type == "invoice.created":
            await _handle_invoice_created(event_data)
        elif event.type == "invoice.payment_failed":
            await _handle_payment_failed(event_data)
        else:
            logger.debug(f"Unhandled webhook event type: {event.type}")

        # Record event for idempotency
        _record_event(event.id, event.type, customer_id, subscription_id, payload)

        return {"status": "success"}

    except Exception as e:
        log_error(
            logger,
            ErrorCode.EXT_STRIPE_ERROR,
            f"Failed to process webhook event {event.id}: {e}",
            event_id=event.id,
            event_type=event.type,
        )
        # Don't record failed events - they'll be retried by Stripe
        raise HTTPException(status_code=500, detail="Event processing failed") from None


# =============================================================================
# Webhook Event Handlers
# =============================================================================


async def _handle_checkout_completed(session: Any) -> None:
    """Handle checkout.session.completed event.

    Updates user or workspace tier and subscription ID on successful checkout.
    Checks for workspace customer first, then falls back to user customer.
    """
    from backend.services.stripe_service import stripe_service
    from bo1.state.repositories.workspace_repository import workspace_repository

    customer_id = session.customer
    subscription_id = session.subscription

    if not customer_id:
        logger.warning("Checkout completed without customer ID")
        return

    # Check if this is a workspace customer
    workspace = workspace_repository.get_workspace_by_stripe_customer(customer_id)
    if workspace:
        # Handle workspace subscription
        workspace_id = workspace["id"]
        if subscription_id:
            subscription = await stripe_service.get_subscription(subscription_id)
            if subscription and subscription.items.data:
                price_id = subscription.items.data[0].price.id
                tier = stripe_service.get_tier_for_price(price_id) or "starter"
                workspace_repository.set_subscription(workspace_id, subscription_id, tier)
                logger.info(f"Workspace {workspace_id} upgraded to {tier} via checkout")
        else:
            logger.info(f"One-time payment completed for workspace {workspace_id}")
        return

    # Fall back to user customer
    user = user_repository.get_user_by_stripe_customer(customer_id)
    if not user:
        logger.warning(f"No user or workspace found for Stripe customer {customer_id}")
        return

    user_id = user["id"]

    # Get subscription to determine tier
    if subscription_id:
        subscription = await stripe_service.get_subscription(subscription_id)
        if subscription and subscription.items.data:
            price_id = subscription.items.data[0].price.id
            tier = stripe_service.get_tier_for_price(price_id) or "starter"

            # Update user subscription
            user_repository.save_stripe_subscription(user_id, subscription_id, tier)
            logger.info(f"User {user_id} upgraded to {tier} via checkout")
    else:
        # One-time payment - just log for now
        logger.info(f"One-time payment completed for user {user_id}")


async def _handle_subscription_updated(subscription: Any) -> None:
    """Handle customer.subscription.updated event.

    Updates user or workspace tier when subscription changes (upgrade/downgrade).
    """
    from backend.services.stripe_service import stripe_service
    from bo1.state.repositories.workspace_repository import workspace_repository

    customer_id = subscription.customer
    subscription_id = subscription.id

    # Check if this is a workspace customer
    workspace = workspace_repository.get_workspace_by_stripe_customer(customer_id)
    if workspace:
        workspace_id = workspace["id"]
        if subscription.items.data:
            price_id = subscription.items.data[0].price.id
            tier = stripe_service.get_tier_for_price(price_id) or "starter"
            if subscription.status in ("active", "trialing"):
                workspace_repository.set_subscription(workspace_id, subscription_id, tier)
                logger.info(f"Workspace {workspace_id} subscription updated to {tier}")
            elif subscription.status in ("past_due", "unpaid"):
                logger.warning(f"Workspace {workspace_id} subscription is {subscription.status}")
        return

    # Fall back to user customer
    user = user_repository.get_user_by_stripe_customer(customer_id)
    if not user:
        logger.warning(f"No user or workspace found for Stripe customer {customer_id}")
        return

    user_id = user["id"]

    # Get new tier from subscription items
    if subscription.items.data:
        price_id = subscription.items.data[0].price.id
        tier = stripe_service.get_tier_for_price(price_id) or "starter"

        # Check subscription status
        if subscription.status in ("active", "trialing"):
            user_repository.save_stripe_subscription(user_id, subscription_id, tier)
            logger.info(f"User {user_id} subscription updated to {tier}")
        elif subscription.status in ("past_due", "unpaid"):
            logger.warning(f"User {user_id} subscription is {subscription.status}")
            # Keep current tier but log for follow-up


async def _handle_subscription_deleted(subscription: Any) -> None:
    """Handle customer.subscription.deleted event.

    Downgrades user or workspace to free tier when subscription is cancelled.
    """
    from bo1.state.repositories.workspace_repository import workspace_repository

    customer_id = subscription.customer

    # Check if this is a workspace customer
    workspace = workspace_repository.get_workspace_by_stripe_customer(customer_id)
    if workspace:
        workspace_id = workspace["id"]
        workspace_repository.clear_subscription(workspace_id)
        logger.info(f"Workspace {workspace_id} subscription cancelled, downgraded to free")
        return

    # Fall back to user customer
    user = user_repository.get_user_by_stripe_customer(customer_id)
    if not user:
        logger.warning(f"No user or workspace found for Stripe customer {customer_id}")
        return

    user_id = user["id"]

    # Downgrade to free tier
    user_repository.clear_stripe_subscription(user_id)
    logger.info(f"User {user_id} subscription cancelled, downgraded to free")


async def _handle_invoice_created(invoice: Any) -> None:
    """Handle invoice.created event.

    Applies internal promotions as discount line items before invoice finalizes.
    Only applies to subscription invoices (not metered billing adjustments).
    """
    from backend.services.promotion_service import apply_promotions_to_stripe_invoice

    customer_id = invoice.customer
    invoice_id = invoice.id
    billing_reason = getattr(invoice, "billing_reason", None)

    # Only apply promos to subscription-related invoices
    # Skip metered billing, manual invoices, etc.
    if billing_reason and not billing_reason.startswith("subscription"):
        logger.debug(
            f"Skipping promo application for non-subscription invoice {invoice_id} "
            f"(billing_reason={billing_reason})"
        )
        return

    # Only apply to draft invoices (before auto-finalization)
    if invoice.status != "draft":
        logger.debug(
            f"Skipping promo application for non-draft invoice {invoice_id} "
            f"(status={invoice.status})"
        )
        return

    # Find user by customer ID
    user = user_repository.get_user_by_stripe_customer(customer_id)
    if not user:
        logger.warning(f"No user found for Stripe customer {customer_id}")
        return

    user_id = user["id"]

    # Get invoice subtotal (before discounts)
    subtotal_cents = invoice.subtotal or 0
    if subtotal_cents <= 0:
        logger.debug(f"Invoice {invoice_id} has non-positive subtotal, skipping promos")
        return

    # Apply promotions
    try:
        result = await apply_promotions_to_stripe_invoice(
            user_id=user_id,
            stripe_customer_id=customer_id,
            stripe_invoice_id=invoice_id,
            subtotal_cents=subtotal_cents,
        )

        if result.applied_items:
            logger.info(
                f"Applied {len(result.applied_items)} promo discount(s) to invoice {invoice_id}: "
                f"total_discount=${result.total_discount_cents / 100:.2f}"
            )
        else:
            logger.debug(f"No promos applied to invoice {invoice_id}")

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_BILLING_ERROR,
            f"Failed to apply promos to invoice {invoice_id}: {e}",
            user_id=user_id,
            invoice_id=invoice_id,
        )
        # Don't fail the webhook - invoice will proceed without promo discounts


async def _handle_payment_failed(invoice: Any) -> None:
    """Handle invoice.payment_failed event.

    Logs warning and optionally sends notification email.
    """
    customer_id = invoice.customer
    subscription_id = invoice.subscription

    # Find user by customer ID
    user = user_repository.get_user_by_stripe_customer(customer_id)
    if not user:
        logger.warning(f"Payment failed for unknown customer {customer_id}")
        return

    user_id = user["id"]
    _email = user.get("email")  # TODO: use for payment failed notification

    logger.warning(
        f"Payment failed for user {user_id} "
        f"(subscription: {subscription_id}, amount: {invoice.amount_due})"
    )

    # TODO: Send payment failed notification email
    # This would integrate with the email service:
    # await email_service.send_payment_failed_email(email, invoice.hosted_invoice_url)
