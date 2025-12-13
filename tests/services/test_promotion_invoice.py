"""Tests for promotion invoice application service.

Tests for apply_promotions_to_stripe_invoice and related functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.promotion_service import (
    apply_promotions_to_stripe_invoice,
)
from backend.services.stripe_service import InvoiceItemResult


@pytest.fixture
def mock_promotion_repository():
    """Mock promotion repository."""
    with patch("backend.services.promotion_service.promotion_repository") as mock_repo:
        yield mock_repo


class TestApplyPromotionsToStripeInvoice:
    """Tests for apply_promotions_to_stripe_invoice function."""

    @pytest.mark.asyncio
    async def test_apply_percentage_discount_to_invoice(self, mock_promotion_repository):
        """Test applying a percentage discount to a Stripe invoice."""
        user_id = "user-123"
        customer_id = "cus_abc"
        invoice_id = "in_xyz"
        subtotal_cents = 10000  # $100

        mock_promotion_repository.has_promo_applied_to_invoice.return_value = False
        mock_promotion_repository.get_applicable_invoice_promos.return_value = [
            {
                "id": "up-1",
                "user_id": user_id,
                "promotion_id": "promo-1",
                "status": "active",
                "promotion": {
                    "id": "promo-1",
                    "code": "SAVE10",
                    "type": "percentage_discount",
                    "value": 10.0,
                },
            }
        ]
        mock_promotion_repository.record_promo_invoice_application.return_value = {}

        mock_stripe = MagicMock()
        mock_stripe.create_invoice_item = AsyncMock(
            return_value=InvoiceItemResult(
                id="ii_123",
                invoice_id=invoice_id,
                amount=-1000,
                description="Promo SAVE10: 10.0% discount",
            )
        )

        with patch.dict(
            "sys.modules",
            {"backend.services.stripe_service": MagicMock(stripe_service=mock_stripe)},
        ):
            result = await apply_promotions_to_stripe_invoice(
                user_id=user_id,
                stripe_customer_id=customer_id,
                stripe_invoice_id=invoice_id,
                subtotal_cents=subtotal_cents,
            )

        assert result.subtotal_cents == 10000
        assert result.total_discount_cents == 1000
        assert result.final_amount_cents == 9000
        assert len(result.applied_items) == 1
        assert result.applied_items[0] == "ii_123"
        assert len(result.exhausted_promos) == 0

    @pytest.mark.asyncio
    async def test_apply_flat_discount_to_invoice(self, mock_promotion_repository):
        """Test applying a flat discount to a Stripe invoice."""
        user_id = "user-123"
        customer_id = "cus_abc"
        invoice_id = "in_xyz"
        subtotal_cents = 10000

        mock_promotion_repository.has_promo_applied_to_invoice.return_value = False
        mock_promotion_repository.get_applicable_invoice_promos.return_value = [
            {
                "id": "up-2",
                "user_id": user_id,
                "promotion_id": "promo-2",
                "status": "active",
                "promotion": {
                    "id": "promo-2",
                    "code": "FLAT5",
                    "type": "flat_discount",
                    "value": 5.0,
                },
            }
        ]
        mock_promotion_repository.record_promo_invoice_application.return_value = {}
        mock_promotion_repository.mark_discount_promo_exhausted.return_value = True

        mock_stripe = MagicMock()
        mock_stripe.create_invoice_item = AsyncMock(
            return_value=InvoiceItemResult(
                id="ii_456",
                invoice_id=invoice_id,
                amount=-500,
                description="Promo FLAT5: $5.00 discount",
            )
        )

        with patch.dict(
            "sys.modules",
            {"backend.services.stripe_service": MagicMock(stripe_service=mock_stripe)},
        ):
            result = await apply_promotions_to_stripe_invoice(
                user_id=user_id,
                stripe_customer_id=customer_id,
                stripe_invoice_id=invoice_id,
                subtotal_cents=subtotal_cents,
            )

        assert result.total_discount_cents == 500
        assert result.final_amount_cents == 9500
        assert len(result.exhausted_promos) == 1
        assert "up-2" in result.exhausted_promos

    @pytest.mark.asyncio
    async def test_multiple_discounts_stacked(self, mock_promotion_repository):
        """Test applying multiple discounts (percentage first, then flat)."""
        user_id = "user-123"
        customer_id = "cus_abc"
        invoice_id = "in_xyz"
        subtotal_cents = 10000

        mock_promotion_repository.has_promo_applied_to_invoice.return_value = False
        mock_promotion_repository.get_applicable_invoice_promos.return_value = [
            {
                "id": "up-1",
                "user_id": user_id,
                "promotion_id": "promo-1",
                "status": "active",
                "promotion": {
                    "id": "promo-1",
                    "code": "SAVE10",
                    "type": "percentage_discount",
                    "value": 10.0,
                },
            },
            {
                "id": "up-2",
                "user_id": user_id,
                "promotion_id": "promo-2",
                "status": "active",
                "promotion": {
                    "id": "promo-2",
                    "code": "FLAT5",
                    "type": "flat_discount",
                    "value": 5.0,
                },
            },
        ]
        mock_promotion_repository.record_promo_invoice_application.return_value = {}
        mock_promotion_repository.mark_discount_promo_exhausted.return_value = True

        call_count = [0]

        async def create_item_side_effect(**kwargs):
            call_count[0] += 1
            return InvoiceItemResult(
                id=f"ii_{call_count[0]}",
                invoice_id=invoice_id,
                amount=kwargs["amount_cents"],
                description=kwargs["description"],
            )

        mock_stripe = MagicMock()
        mock_stripe.create_invoice_item = AsyncMock(side_effect=create_item_side_effect)

        with patch.dict(
            "sys.modules",
            {"backend.services.stripe_service": MagicMock(stripe_service=mock_stripe)},
        ):
            result = await apply_promotions_to_stripe_invoice(
                user_id=user_id,
                stripe_customer_id=customer_id,
                stripe_invoice_id=invoice_id,
                subtotal_cents=subtotal_cents,
            )

        # 10% of $100 = $10, then $5 flat = $15 total
        assert result.total_discount_cents == 1500
        assert result.final_amount_cents == 8500
        assert len(result.applied_items) == 2

    @pytest.mark.asyncio
    async def test_discount_does_not_exceed_invoice_total(self, mock_promotion_repository):
        """Test that discount is capped at invoice total."""
        user_id = "user-123"
        customer_id = "cus_abc"
        invoice_id = "in_xyz"
        subtotal_cents = 300  # $3

        mock_promotion_repository.has_promo_applied_to_invoice.return_value = False
        mock_promotion_repository.get_applicable_invoice_promos.return_value = [
            {
                "id": "up-1",
                "user_id": user_id,
                "promotion_id": "promo-1",
                "status": "active",
                "promotion": {
                    "id": "promo-1",
                    "code": "FLAT10",
                    "type": "flat_discount",
                    "value": 10.0,  # $10 > $3 invoice
                },
            }
        ]
        mock_promotion_repository.record_promo_invoice_application.return_value = {}
        mock_promotion_repository.mark_discount_promo_exhausted.return_value = True

        mock_stripe = MagicMock()
        mock_stripe.create_invoice_item = AsyncMock(
            return_value=InvoiceItemResult(
                id="ii_cap",
                invoice_id=invoice_id,
                amount=-300,
                description="Promo FLAT10: $10.00 discount",
            )
        )

        with patch.dict(
            "sys.modules",
            {"backend.services.stripe_service": MagicMock(stripe_service=mock_stripe)},
        ):
            result = await apply_promotions_to_stripe_invoice(
                user_id=user_id,
                stripe_customer_id=customer_id,
                stripe_invoice_id=invoice_id,
                subtotal_cents=subtotal_cents,
            )

        assert result.total_discount_cents == 300
        assert result.final_amount_cents == 0

    @pytest.mark.asyncio
    async def test_skip_already_applied_invoice(self, mock_promotion_repository):
        """Test idempotency - skip if invoice already has promos applied."""
        user_id = "user-123"
        mock_promotion_repository.has_promo_applied_to_invoice.return_value = True

        result = await apply_promotions_to_stripe_invoice(
            user_id=user_id,
            stripe_customer_id="cus_abc",
            stripe_invoice_id="in_xyz",
            subtotal_cents=10000,
        )

        assert result.total_discount_cents == 0
        assert result.applied_items == []

    @pytest.mark.asyncio
    async def test_no_promos_available(self, mock_promotion_repository):
        """Test graceful handling when user has no applicable promos."""
        user_id = "user-123"
        mock_promotion_repository.has_promo_applied_to_invoice.return_value = False
        mock_promotion_repository.get_applicable_invoice_promos.return_value = []

        result = await apply_promotions_to_stripe_invoice(
            user_id=user_id,
            stripe_customer_id="cus_abc",
            stripe_invoice_id="in_xyz",
            subtotal_cents=10000,
        )

        assert result.total_discount_cents == 0
        assert result.applied_items == []

    @pytest.mark.asyncio
    async def test_zero_subtotal_skips_promos(self, mock_promotion_repository):
        """Test that zero/negative subtotals skip promo application."""
        mock_promotion_repository.has_promo_applied_to_invoice.return_value = False

        result = await apply_promotions_to_stripe_invoice(
            user_id="user-123",
            stripe_customer_id="cus_abc",
            stripe_invoice_id="in_xyz",
            subtotal_cents=0,
        )

        assert result.total_discount_cents == 0
        mock_promotion_repository.get_applicable_invoice_promos.assert_not_called()

    @pytest.mark.asyncio
    async def test_stripe_error_continues_with_other_promos(self, mock_promotion_repository):
        """Test that Stripe API errors don't fail entire promo application."""
        user_id = "user-123"
        customer_id = "cus_abc"
        invoice_id = "in_xyz"
        subtotal_cents = 10000

        mock_promotion_repository.has_promo_applied_to_invoice.return_value = False
        mock_promotion_repository.get_applicable_invoice_promos.return_value = [
            {
                "id": "up-1",
                "user_id": user_id,
                "promotion_id": "promo-1",
                "status": "active",
                "promotion": {
                    "id": "promo-1",
                    "code": "FAIL",
                    "type": "percentage_discount",
                    "value": 10.0,
                },
            },
            {
                "id": "up-2",
                "user_id": user_id,
                "promotion_id": "promo-2",
                "status": "active",
                "promotion": {
                    "id": "promo-2",
                    "code": "SUCCESS",
                    "type": "flat_discount",
                    "value": 5.0,
                },
            },
        ]
        mock_promotion_repository.record_promo_invoice_application.return_value = {}
        mock_promotion_repository.mark_discount_promo_exhausted.return_value = True

        call_count = [0]

        async def create_item_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Stripe API error")
            return InvoiceItemResult(
                id="ii_success",
                invoice_id=invoice_id,
                amount=kwargs["amount_cents"],
                description=kwargs["description"],
            )

        mock_stripe = MagicMock()
        mock_stripe.create_invoice_item = AsyncMock(side_effect=create_item_side_effect)

        with patch.dict(
            "sys.modules",
            {"backend.services.stripe_service": MagicMock(stripe_service=mock_stripe)},
        ):
            result = await apply_promotions_to_stripe_invoice(
                user_id=user_id,
                stripe_customer_id=customer_id,
                stripe_invoice_id=invoice_id,
                subtotal_cents=subtotal_cents,
            )

        # Only second promo should succeed
        assert len(result.applied_items) == 1
        assert result.applied_items[0] == "ii_success"
        assert result.total_discount_cents == 500
