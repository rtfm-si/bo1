"""Stripe service for billing operations.

Provides a thin wrapper around the Stripe SDK with:
- Lazy client initialization
- Customer creation/retrieval
- Checkout session creation
- Billing portal session creation
- Subscription management helpers

Usage:
    from backend.services.stripe_service import stripe_service

    # Create checkout session
    url = await stripe_service.create_checkout_session(
        user_id="user_123",
        email="user@example.com",
        price_id="price_abc",
        success_url="https://app.com/billing/success",
        cancel_url="https://app.com/billing/cancel",
    )
"""

import logging
from dataclasses import dataclass
from typing import Literal

import stripe
from stripe import StripeError

from bo1.config import get_settings

logger = logging.getLogger(__name__)

# Price ID to tier mapping
PRICE_TO_TIER: dict[str, str] = {}  # Populated on init from settings


@dataclass
class StripeCustomer:
    """Stripe customer info."""

    id: str
    email: str | None


@dataclass
class CheckoutResult:
    """Result from checkout session creation."""

    session_id: str
    url: str


@dataclass
class PortalResult:
    """Result from billing portal session creation."""

    url: str


@dataclass
class InvoiceItemResult:
    """Result from invoice item creation."""

    id: str
    invoice_id: str
    amount: int  # in cents (negative for discounts)
    description: str


class StripeService:
    """Service for Stripe billing operations."""

    _initialized: bool = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization of Stripe client."""
        if self._initialized:
            return

        settings = get_settings()
        if not settings.stripe_secret_key:
            raise RuntimeError("STRIPE_SECRET_KEY not configured")

        stripe.api_key = settings.stripe_secret_key

        # Build price-to-tier mapping
        global PRICE_TO_TIER
        PRICE_TO_TIER = {}
        if settings.stripe_price_starter:
            PRICE_TO_TIER[settings.stripe_price_starter] = "starter"
        if settings.stripe_price_pro:
            PRICE_TO_TIER[settings.stripe_price_pro] = "pro"

        self._initialized = True
        logger.info("Stripe service initialized")

    def get_tier_for_price(self, price_id: str) -> str | None:
        """Get subscription tier for a price ID.

        Args:
            price_id: Stripe price ID

        Returns:
            Tier name (starter, pro) or None if unknown
        """
        self._ensure_initialized()
        return PRICE_TO_TIER.get(price_id)

    async def get_or_create_customer(
        self,
        user_id: str,
        email: str,
        existing_customer_id: str | None = None,
    ) -> StripeCustomer:
        """Get existing customer or create new one.

        Args:
            user_id: Internal user ID (stored as metadata)
            email: Customer email
            existing_customer_id: Existing Stripe customer ID if known

        Returns:
            StripeCustomer with ID and email
        """
        self._ensure_initialized()

        # If we have an existing customer ID, verify it's valid
        if existing_customer_id:
            try:
                customer = stripe.Customer.retrieve(existing_customer_id)
                if not customer.get("deleted"):
                    return StripeCustomer(id=customer.id, email=customer.get("email"))
            except StripeError as e:
                logger.warning(f"Failed to retrieve customer {existing_customer_id}: {e}")

        # Create new customer
        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={"user_id": user_id},
            )
            logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
            return StripeCustomer(id=customer.id, email=customer.get("email"))
        except StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise

    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        mode: Literal["subscription", "payment"] = "subscription",
        allow_promotion_codes: bool = True,
    ) -> CheckoutResult:
        """Create a Stripe Checkout session.

        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID for the product
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            mode: Checkout mode (subscription or payment)
            allow_promotion_codes: Allow Stripe promo codes

        Returns:
            CheckoutResult with session ID and redirect URL
        """
        self._ensure_initialized()

        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode=mode,
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                allow_promotion_codes=allow_promotion_codes,
                # Collect billing address for tax compliance
                billing_address_collection="required",
            )
            logger.info(f"Created checkout session {session.id} for customer {customer_id}")
            return CheckoutResult(session_id=session.id, url=session.url or "")
        except StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise

    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> PortalResult:
        """Create a Stripe Billing Portal session.

        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal

        Returns:
            PortalResult with portal URL
        """
        self._ensure_initialized()

        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            logger.info(f"Created portal session for customer {customer_id}")
            return PortalResult(url=session.url)
        except StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            raise

    def construct_webhook_event(
        self,
        payload: bytes,
        signature: str,
    ) -> stripe.Event:
        """Construct and validate a webhook event.

        Args:
            payload: Raw request body
            signature: Stripe-Signature header value

        Returns:
            Validated Stripe event

        Raises:
            stripe.SignatureVerificationError: If signature is invalid
        """
        self._ensure_initialized()

        settings = get_settings()
        if not settings.stripe_webhook_secret:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET not configured")

        return stripe.Webhook.construct_event(
            payload,
            signature,
            settings.stripe_webhook_secret,
        )

    async def get_subscription(self, subscription_id: str) -> stripe.Subscription | None:
        """Get subscription details.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Subscription object or None if not found
        """
        self._ensure_initialized()

        try:
            return stripe.Subscription.retrieve(subscription_id)
        except StripeError as e:
            logger.warning(f"Failed to retrieve subscription {subscription_id}: {e}")
            return None

    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True,
    ) -> bool:
        """Cancel a subscription.

        Args:
            subscription_id: Stripe subscription ID
            at_period_end: If True, cancel at end of billing period

        Returns:
            True if successful
        """
        self._ensure_initialized()

        try:
            if at_period_end:
                stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )
            else:
                stripe.Subscription.cancel(subscription_id)

            logger.info(f"Cancelled subscription {subscription_id}")
            return True
        except StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return False

    async def create_invoice_item(
        self,
        customer_id: str,
        invoice_id: str,
        amount_cents: int,
        description: str,
    ) -> InvoiceItemResult:
        """Create an invoice item (line item) on a draft invoice.

        Use negative amounts for discounts.

        Args:
            customer_id: Stripe customer ID
            invoice_id: Stripe invoice ID (must be draft status)
            amount_cents: Amount in cents (negative for discounts)
            description: Description shown on invoice

        Returns:
            InvoiceItemResult with created item details

        Raises:
            StripeError: If item creation fails
        """
        self._ensure_initialized()

        try:
            item = stripe.InvoiceItem.create(
                customer=customer_id,
                invoice=invoice_id,
                amount=amount_cents,
                currency="usd",
                description=description,
            )
            logger.info(
                f"Created invoice item {item.id} on invoice {invoice_id}: "
                f"${amount_cents / 100:.2f} ({description})"
            )
            return InvoiceItemResult(
                id=item.id,
                invoice_id=invoice_id,
                amount=amount_cents,
                description=description,
            )
        except StripeError as e:
            logger.error(f"Failed to create invoice item: {e}")
            raise

    async def get_invoice(self, invoice_id: str) -> stripe.Invoice | None:
        """Get invoice details.

        Args:
            invoice_id: Stripe invoice ID

        Returns:
            Invoice object or None if not found
        """
        self._ensure_initialized()

        try:
            return stripe.Invoice.retrieve(invoice_id)
        except StripeError as e:
            logger.warning(f"Failed to retrieve invoice {invoice_id}: {e}")
            return None


# Singleton instance
stripe_service = StripeService()
