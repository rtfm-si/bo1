"""Integration tests for billing webhook promo application.

Tests for invoice.created webhook handler with promotion application.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_invoice():
    """Create a mock Stripe invoice object."""
    invoice = MagicMock()
    invoice.id = "in_test_123"
    invoice.customer = "cus_test_456"
    invoice.status = "draft"
    invoice.subtotal = 2900  # $29.00
    invoice.billing_reason = "subscription_create"
    return invoice


@pytest.fixture
def mock_user():
    """Create a mock user dict."""
    return {
        "id": "user-test-789",
        "email": "test@example.com",
        "subscription_tier": "starter",
    }


class TestInvoiceCreatedHandler:
    """Tests for _handle_invoice_created webhook handler."""

    @pytest.mark.asyncio
    async def test_invoice_webhook_applies_promo(self, mock_invoice, mock_user):
        """Test that invoice.created webhook applies promos."""
        from backend.api.billing import _handle_invoice_created

        with (
            patch("backend.api.billing.user_repository") as mock_user_repo,
            patch(
                "backend.services.promotion_service.apply_promotions_to_stripe_invoice"
            ) as mock_apply,
        ):
            mock_user_repo.get_user_by_stripe_customer.return_value = mock_user
            mock_apply.return_value = MagicMock(
                applied_items=["ii_123"],
                total_discount_cents=500,
            )

            await _handle_invoice_created(mock_invoice)

            mock_apply.assert_called_once_with(
                user_id=mock_user["id"],
                stripe_customer_id=mock_invoice.customer,
                stripe_invoice_id=mock_invoice.id,
                subtotal_cents=mock_invoice.subtotal,
            )

    @pytest.mark.asyncio
    async def test_invoice_webhook_idempotent(self, mock_invoice, mock_user):
        """Test that invoice webhook handles already-applied promos gracefully."""
        from backend.api.billing import _handle_invoice_created

        with (
            patch("backend.api.billing.user_repository") as mock_user_repo,
            patch(
                "backend.services.promotion_service.apply_promotions_to_stripe_invoice"
            ) as mock_apply,
        ):
            mock_user_repo.get_user_by_stripe_customer.return_value = mock_user
            mock_apply.return_value = MagicMock(
                applied_items=[],  # Empty = already applied
                total_discount_cents=0,
            )

            # Should not raise, just log and continue
            await _handle_invoice_created(mock_invoice)

            mock_apply.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_promo_available_skips_gracefully(self, mock_invoice, mock_user):
        """Test graceful handling when no promos available."""
        from backend.api.billing import _handle_invoice_created

        with (
            patch("backend.api.billing.user_repository") as mock_user_repo,
            patch(
                "backend.services.promotion_service.apply_promotions_to_stripe_invoice"
            ) as mock_apply,
        ):
            mock_user_repo.get_user_by_stripe_customer.return_value = mock_user
            mock_apply.return_value = MagicMock(
                applied_items=[],
                total_discount_cents=0,
            )

            # Should complete without error
            await _handle_invoice_created(mock_invoice)

    @pytest.mark.asyncio
    async def test_skip_non_subscription_invoice(self, mock_invoice, mock_user):
        """Test that non-subscription invoices are skipped."""
        from backend.api.billing import _handle_invoice_created

        mock_invoice.billing_reason = "manual"  # Not a subscription invoice

        with (
            patch("backend.api.billing.user_repository") as mock_user_repo,
            patch(
                "backend.services.promotion_service.apply_promotions_to_stripe_invoice"
            ) as mock_apply,
        ):
            await _handle_invoice_created(mock_invoice)

            # Should not apply promos
            mock_user_repo.get_user_by_stripe_customer.assert_not_called()
            mock_apply.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_non_draft_invoice(self, mock_invoice, mock_user):
        """Test that finalized invoices are skipped."""
        from backend.api.billing import _handle_invoice_created

        mock_invoice.status = "open"  # Already finalized

        with (
            patch("backend.api.billing.user_repository") as mock_user_repo,
            patch(
                "backend.services.promotion_service.apply_promotions_to_stripe_invoice"
            ) as mock_apply,
        ):
            await _handle_invoice_created(mock_invoice)

            # Should not apply promos
            mock_user_repo.get_user_by_stripe_customer.assert_not_called()
            mock_apply.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_unknown_customer(self, mock_invoice):
        """Test graceful handling of unknown customer."""
        from backend.api.billing import _handle_invoice_created

        with (
            patch("backend.api.billing.user_repository") as mock_user_repo,
            patch(
                "backend.services.promotion_service.apply_promotions_to_stripe_invoice"
            ) as mock_apply,
        ):
            mock_user_repo.get_user_by_stripe_customer.return_value = None

            await _handle_invoice_created(mock_invoice)

            mock_apply.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_zero_subtotal_invoice(self, mock_invoice, mock_user):
        """Test that zero subtotal invoices are skipped."""
        from backend.api.billing import _handle_invoice_created

        mock_invoice.subtotal = 0

        with (
            patch("backend.api.billing.user_repository") as mock_user_repo,
            patch(
                "backend.services.promotion_service.apply_promotions_to_stripe_invoice"
            ) as mock_apply,
        ):
            mock_user_repo.get_user_by_stripe_customer.return_value = mock_user

            await _handle_invoice_created(mock_invoice)

            mock_apply.assert_not_called()

    @pytest.mark.asyncio
    async def test_promo_error_does_not_fail_webhook(self, mock_invoice, mock_user):
        """Test that promo application errors don't fail the webhook."""
        from backend.api.billing import _handle_invoice_created

        with (
            patch("backend.api.billing.user_repository") as mock_user_repo,
            patch(
                "backend.services.promotion_service.apply_promotions_to_stripe_invoice"
            ) as mock_apply,
        ):
            mock_user_repo.get_user_by_stripe_customer.return_value = mock_user
            mock_apply.side_effect = Exception("Promo service error")

            # Should not raise - just log error
            await _handle_invoice_created(mock_invoice)

    @pytest.mark.asyncio
    async def test_handles_subscription_update_billing_reason(self, mock_invoice, mock_user):
        """Test subscription_update billing reason is handled."""
        from backend.api.billing import _handle_invoice_created

        mock_invoice.billing_reason = "subscription_update"

        with (
            patch("backend.api.billing.user_repository") as mock_user_repo,
            patch(
                "backend.services.promotion_service.apply_promotions_to_stripe_invoice"
            ) as mock_apply,
        ):
            mock_user_repo.get_user_by_stripe_customer.return_value = mock_user
            mock_apply.return_value = MagicMock(
                applied_items=["ii_123"],
                total_discount_cents=500,
            )

            await _handle_invoice_created(mock_invoice)

            # Should apply promos for subscription_update
            mock_apply.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_subscription_cycle_billing_reason(self, mock_invoice, mock_user):
        """Test subscription_cycle billing reason is handled."""
        from backend.api.billing import _handle_invoice_created

        mock_invoice.billing_reason = "subscription_cycle"

        with (
            patch("backend.api.billing.user_repository") as mock_user_repo,
            patch(
                "backend.services.promotion_service.apply_promotions_to_stripe_invoice"
            ) as mock_apply,
        ):
            mock_user_repo.get_user_by_stripe_customer.return_value = mock_user
            mock_apply.return_value = MagicMock(
                applied_items=["ii_123"],
                total_discount_cents=500,
            )

            await _handle_invoice_created(mock_invoice)

            # Should apply promos for recurring subscriptions
            mock_apply.assert_called_once()
