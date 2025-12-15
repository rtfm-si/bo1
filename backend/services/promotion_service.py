"""Promotion service for managing promo codes and deliberation credits.

Provides:
- check_deliberation_allowance: Get total remaining credits across active promos
- consume_promo_deliberation: Decrement oldest active promo credit
- apply_promotions_to_invoice: Apply percentage/flat discounts to invoice
- apply_promotions_to_stripe_invoice: Apply promos to Stripe invoice as line items
- validate_and_apply_code: Validate and apply promo code to user
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from bo1.state.database import db_session
from bo1.state.repositories.promotion_repository import promotion_repository

logger = logging.getLogger(__name__)


@dataclass
class AllowanceResult:
    """Result of checking deliberation allowance.

    Attributes:
        total_remaining: Total deliberation credits remaining across all active promos
        active_promos: List of active user_promotion IDs (oldest first)
        has_credits: Whether user has any promo credits available
    """

    total_remaining: int
    active_promos: list[str]
    has_credits: bool


@dataclass
class InvoiceResult:
    """Result of applying promotions to an invoice.

    Attributes:
        base_amount: Original invoice amount
        final_amount: Amount after all discounts
        total_discount: Total discount applied
        applied_promotions: List of (promo_id, discount_amount) tuples
    """

    base_amount: float
    final_amount: float
    total_discount: float
    applied_promotions: list[tuple[str, float]]


@dataclass
class StripeInvoicePromoResult:
    """Result of applying promotions to a Stripe invoice.

    Attributes:
        subtotal_cents: Original invoice subtotal in cents
        total_discount_cents: Total discount applied in cents
        final_amount_cents: Final amount after discounts in cents
        applied_items: List of created Stripe invoice item IDs
        exhausted_promos: List of user_promotion IDs marked exhausted
    """

    subtotal_cents: int
    total_discount_cents: int
    final_amount_cents: int
    applied_items: list[str]
    exhausted_promos: list[str]


class PromoValidationError(Exception):
    """Raised when promo code validation fails."""

    def __init__(self, message: str, code: str = "validation_error") -> None:
        """Initialize promo validation error."""
        self.message = message
        self.code = code
        super().__init__(message)


def check_deliberation_allowance(user_id: str) -> AllowanceResult:
    """Check user's total remaining deliberation credits across active promos.

    Returns credits from promos with type 'extra_deliberations' or 'goodwill_credits'
    that have deliberations_remaining > 0.

    Args:
        user_id: The user ID to check

    Returns:
        AllowanceResult with total remaining credits and active promo IDs
    """
    # Get user's active promotions with deliberation credits
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT up.id, up.deliberations_remaining
                FROM user_promotions up
                JOIN promotions p ON up.promotion_id = p.id
                WHERE up.user_id = %s
                  AND up.status = 'active'
                  AND up.deliberations_remaining > 0
                  AND p.type IN ('extra_deliberations', 'goodwill_credits')
                ORDER BY up.applied_at ASC
                """,
                (user_id,),
            )
            rows = cur.fetchall()

    total = sum(row["deliberations_remaining"] for row in rows)
    promo_ids = [row["id"] for row in rows]

    return AllowanceResult(
        total_remaining=total,
        active_promos=promo_ids,
        has_credits=total > 0,
    )


def consume_promo_deliberation(user_id: str) -> bool:
    """Consume one deliberation credit from user's oldest active promo.

    Uses FIFO ordering (oldest applied_at first) to consume credits.

    Args:
        user_id: The user ID

    Returns:
        True if credit was consumed, False if no credits available
    """
    allowance = check_deliberation_allowance(user_id)
    if not allowance.has_credits:
        logger.debug(f"User {user_id} has no promo credits to consume")
        return False

    # Get oldest active promo with credits
    oldest_promo_id = allowance.active_promos[0]

    # Decrement using repository (handles exhausted status)
    remaining = promotion_repository.decrement_deliberations(oldest_promo_id, user_id)

    if remaining is not None:
        logger.info(
            f"Consumed promo credit for user {user_id}, "
            f"promo={oldest_promo_id}, remaining={remaining}"
        )
        return True

    logger.warning(f"Failed to consume promo credit for user {user_id}")
    return False


def apply_promotions_to_invoice(user_id: str, base_amount: float) -> InvoiceResult:
    """Apply all applicable promotions to an invoice amount.

    Order of application:
    1. Percentage discounts (applied to remaining amount)
    2. Flat discounts (applied after percentages)

    Args:
        user_id: The user ID
        base_amount: Original invoice amount

    Returns:
        InvoiceResult with final amount and applied discounts
    """
    if base_amount <= 0:
        return InvoiceResult(
            base_amount=base_amount,
            final_amount=0.0,
            total_discount=0.0,
            applied_promotions=[],
        )

    # Get user's active discount promotions
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT up.id, up.promotion_id, p.type, p.value
                FROM user_promotions up
                JOIN promotions p ON up.promotion_id = p.id
                WHERE up.user_id = %s
                  AND up.status = 'active'
                  AND p.type IN ('percentage_discount', 'flat_discount')
                ORDER BY
                    CASE p.type
                        WHEN 'percentage_discount' THEN 1
                        WHEN 'flat_discount' THEN 2
                    END,
                    up.applied_at ASC
                """,
                (user_id,),
            )
            promos = cur.fetchall()

    current_amount = base_amount
    total_discount = 0.0
    applied: list[tuple[str, float]] = []

    for promo in promos:
        if current_amount <= 0:
            break

        promo_type = promo["type"]
        value = float(promo["value"])

        if promo_type == "percentage_discount":
            discount = current_amount * (value / 100.0)
        else:  # flat_discount
            discount = min(value, current_amount)

        current_amount -= discount
        total_discount += discount
        applied.append((promo["promotion_id"], discount))

        logger.debug(
            f"Applied {promo_type} promo {promo['promotion_id']}: "
            f"${discount:.2f} discount, remaining=${current_amount:.2f}"
        )

    return InvoiceResult(
        base_amount=base_amount,
        final_amount=max(0.0, current_amount),
        total_discount=total_discount,
        applied_promotions=applied,
    )


def validate_and_apply_code(user_id: str, code: str) -> dict:
    """Validate and apply a promo code to a user.

    Validation checks:
    1. Code exists and is active
    2. Code not expired
    3. Code under max_uses limit
    4. User hasn't already applied this code

    Args:
        user_id: The user ID
        code: The promo code to apply

    Returns:
        The created user_promotion dict

    Raises:
        PromoValidationError: If validation fails
    """
    code = code.strip().upper()

    # Get the promotion
    promo = promotion_repository.get_promotion_by_code(code)

    if promo is None:
        raise PromoValidationError("Promo code not found", "not_found")

    if promo["deleted_at"] is not None:
        raise PromoValidationError("This promo code is no longer active", "inactive")

    # Check expiration
    if promo["expires_at"] and promo["expires_at"] < datetime.now(UTC):
        raise PromoValidationError("This promo code has expired", "expired")

    # Check max uses
    if promo["max_uses"] and promo["uses_count"] >= promo["max_uses"]:
        raise PromoValidationError(
            "This promo code has reached its maximum uses", "max_uses_reached"
        )

    # Check if user already has this promotion
    existing = promotion_repository.get_user_promotion(user_id, promo["id"])
    if existing:
        raise PromoValidationError("You have already applied this promo code", "already_applied")

    # Determine initial values based on promo type
    deliberations_remaining = None
    discount_applied = None

    if promo["type"] in ("extra_deliberations", "goodwill_credits"):
        deliberations_remaining = int(promo["value"])
    elif promo["type"] in ("percentage_discount", "flat_discount"):
        discount_applied = float(promo["value"])

    # Apply the promotion (within a transaction for atomicity)
    with db_session() as conn:
        with conn.cursor():
            # Increment promotion uses (with race condition protection)
            if not promotion_repository.increment_promotion_uses(promo["id"]):
                raise PromoValidationError(
                    "This promo code has reached its maximum uses", "max_uses_reached"
                )

            # Apply to user
            promotion_repository.apply_promotion(
                user_id=user_id,
                promotion_id=promo["id"],
                deliberations_remaining=deliberations_remaining,
                discount_applied=discount_applied,
            )

    logger.info(
        f"Applied promo {code} to user {user_id}: type={promo['type']}, value={promo['value']}"
    )

    # Return full user_promotion with nested promotion
    return promotion_repository.get_user_promotion(user_id, promo["id"])


async def apply_promotions_to_stripe_invoice(
    user_id: str,
    stripe_customer_id: str,
    stripe_invoice_id: str,
    subtotal_cents: int,
) -> StripeInvoicePromoResult:
    """Apply internal promotions to a Stripe invoice as discount line items.

    Creates negative invoice items for each applicable discount and records
    applications for tracking. One-time discounts are marked exhausted.

    Args:
        user_id: The user ID
        stripe_customer_id: Stripe customer ID
        stripe_invoice_id: Stripe invoice ID (must be draft status)
        subtotal_cents: Invoice subtotal in cents

    Returns:
        StripeInvoicePromoResult with discount details and created items
    """
    from backend.services.stripe_service import stripe_service

    # Idempotency check - skip if already applied
    if promotion_repository.has_promo_applied_to_invoice(stripe_invoice_id):
        logger.info(f"Invoice {stripe_invoice_id} already has promo discounts applied")
        return StripeInvoicePromoResult(
            subtotal_cents=subtotal_cents,
            total_discount_cents=0,
            final_amount_cents=subtotal_cents,
            applied_items=[],
            exhausted_promos=[],
        )

    if subtotal_cents <= 0:
        logger.debug(f"Invoice {stripe_invoice_id} has non-positive subtotal, skipping promos")
        return StripeInvoicePromoResult(
            subtotal_cents=subtotal_cents,
            total_discount_cents=0,
            final_amount_cents=subtotal_cents,
            applied_items=[],
            exhausted_promos=[],
        )

    # Get applicable discount promos
    promos = promotion_repository.get_applicable_invoice_promos(user_id)

    if not promos:
        logger.debug(f"No applicable promos for user {user_id} on invoice {stripe_invoice_id}")
        return StripeInvoicePromoResult(
            subtotal_cents=subtotal_cents,
            total_discount_cents=0,
            final_amount_cents=subtotal_cents,
            applied_items=[],
            exhausted_promos=[],
        )

    current_amount_cents = subtotal_cents
    total_discount_cents = 0
    applied_items: list[str] = []
    exhausted_promos: list[str] = []

    for user_promo in promos:
        if current_amount_cents <= 0:
            break

        promo = user_promo["promotion"]
        promo_type = promo["type"]
        promo_value = promo["value"]
        promo_code = promo["code"]

        # Calculate discount in cents
        if promo_type == "percentage_discount":
            discount_cents = int(current_amount_cents * (promo_value / 100.0))
            description = f"Promo {promo_code}: {promo_value}% discount"
        else:  # flat_discount - value is in dollars
            discount_cents = min(int(promo_value * 100), current_amount_cents)
            description = f"Promo {promo_code}: ${promo_value:.2f} discount"

        if discount_cents <= 0:
            continue

        try:
            # Create negative invoice item in Stripe
            item = await stripe_service.create_invoice_item(
                customer_id=stripe_customer_id,
                invoice_id=stripe_invoice_id,
                amount_cents=-discount_cents,  # Negative for discount
                description=description,
            )

            # Record application in tracking table
            promotion_repository.record_promo_invoice_application(
                user_promotion_id=user_promo["id"],
                stripe_invoice_id=stripe_invoice_id,
                stripe_invoice_item_id=item.id,
                discount_amount_cents=discount_cents,
            )

            applied_items.append(item.id)
            current_amount_cents -= discount_cents
            total_discount_cents += discount_cents

            logger.info(
                f"Applied promo {promo_code} to invoice {stripe_invoice_id}: "
                f"-${discount_cents / 100:.2f}"
            )

            # Mark one-time discounts as exhausted (flat discounts are typically one-time)
            if promo_type == "flat_discount":
                promotion_repository.mark_discount_promo_exhausted(user_promo["id"], user_id)
                exhausted_promos.append(user_promo["id"])
                logger.info(f"Marked flat discount promo {user_promo['id']} as exhausted")

        except Exception as e:
            logger.error(f"Failed to apply promo {promo_code} to invoice {stripe_invoice_id}: {e}")
            # Continue with other promos rather than failing entirely
            continue

    return StripeInvoicePromoResult(
        subtotal_cents=subtotal_cents,
        total_discount_cents=total_discount_cents,
        final_amount_cents=max(0, subtotal_cents - total_discount_cents),
        applied_items=applied_items,
        exhausted_promos=exhausted_promos,
    )
