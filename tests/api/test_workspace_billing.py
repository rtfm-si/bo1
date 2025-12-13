"""Unit tests for workspace billing functionality."""

import uuid
from unittest.mock import MagicMock, patch

import pytest


class TestTierResolution:
    """Tests for workspace tier resolution in tier limits middleware."""

    def test_tier_priority_ordering(self):
        """Tier priorities should be correctly ordered."""
        from backend.api.middleware.tier_limits import TIER_PRIORITY

        assert TIER_PRIORITY["free"] < TIER_PRIORITY["starter"]
        assert TIER_PRIORITY["starter"] < TIER_PRIORITY["pro"]
        assert TIER_PRIORITY["pro"] < TIER_PRIORITY["enterprise"]

    def test_workspace_tier_overrides_user_tier(self):
        """Workspace tier should override user tier when higher."""
        from backend.api.middleware.tier_limits import TIER_PRIORITY

        # User on free tier, workspace on pro tier
        # Workspace tier should be used
        assert TIER_PRIORITY["pro"] > TIER_PRIORITY["free"]
        assert TIER_PRIORITY["starter"] > TIER_PRIORITY["free"]

    def test_user_tier_used_when_higher(self):
        """User tier should be used when higher than workspace."""
        from backend.api.middleware.tier_limits import TIER_PRIORITY

        # User on pro tier keeps pro even if workspace is starter
        assert TIER_PRIORITY["pro"] > TIER_PRIORITY["starter"]

    def test_workspace_tier_lookup_success(self):
        """Should look up workspace tier by header when user is member."""
        from backend.api.middleware.tier_limits import _get_workspace_tier

        with patch("bo1.state.repositories.workspace_repository.workspace_repository") as mock_repo:
            workspace_id = str(uuid.uuid4())
            mock_repo.is_member.return_value = True
            mock_repo.get_workspace_tier.return_value = "pro"

            tier = _get_workspace_tier(workspace_id, "test-user-123")

            assert tier == "pro"
            mock_repo.is_member.assert_called_once()
            mock_repo.get_workspace_tier.assert_called_once()

    def test_workspace_tier_non_member(self):
        """Should return None if user is not workspace member."""
        from backend.api.middleware.tier_limits import _get_workspace_tier

        with patch("bo1.state.repositories.workspace_repository.workspace_repository") as mock_repo:
            workspace_id = str(uuid.uuid4())
            mock_repo.is_member.return_value = False

            tier = _get_workspace_tier(workspace_id, "test-user-123")

            assert tier is None
            mock_repo.get_workspace_tier.assert_not_called()

    def test_workspace_tier_invalid_uuid(self):
        """Should return None for invalid UUID."""
        from backend.api.middleware.tier_limits import _get_workspace_tier

        tier = _get_workspace_tier("invalid-uuid", "test-user-123")

        assert tier is None

    def test_workspace_tier_none_id(self):
        """Should return None when no workspace ID provided."""
        from backend.api.middleware.tier_limits import _get_workspace_tier

        tier = _get_workspace_tier(None, "test-user-123")

        assert tier is None

    def test_get_user_tier_with_workspace_header(self):
        """Should use workspace tier when provided and higher."""
        from backend.api.middleware.tier_limits import _get_user_tier

        mock_request = MagicMock()
        mock_request.headers.get.return_value = str(uuid.uuid4())

        user_data = {
            "user_id": "test-user-123",
            "subscription_tier": "free",
        }

        with (
            patch("backend.api.middleware.tier_limits.get_effective_tier") as mock_effective,
            patch("backend.api.middleware.tier_limits._get_workspace_tier") as mock_ws_tier,
        ):
            mock_effective.return_value = "free"
            mock_ws_tier.return_value = "pro"

            user_id, tier = _get_user_tier(user_data, mock_request)

            assert user_id == "test-user-123"
            assert tier == "pro"  # Workspace tier used because it's higher

    def test_get_user_tier_without_workspace_header(self):
        """Should use user tier when no workspace header."""
        from backend.api.middleware.tier_limits import _get_user_tier

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        user_data = {
            "user_id": "test-user-123",
            "subscription_tier": "starter",
        }

        with patch("backend.api.middleware.tier_limits.get_effective_tier") as mock_effective:
            mock_effective.return_value = "starter"

            user_id, tier = _get_user_tier(user_data, mock_request)

            assert user_id == "test-user-123"
            assert tier == "starter"


class TestWebhookHandlers:
    """Tests for webhook handlers with workspace billing support."""

    @pytest.mark.asyncio
    async def test_checkout_completed_for_workspace(self):
        """Should update workspace tier on checkout.session.completed."""
        from backend.api.billing import _handle_checkout_completed

        workspace_id = uuid.uuid4()

        # Mock session object
        mock_session = MagicMock()
        mock_session.customer = "cus_workspace_123"
        mock_session.subscription = "sub_test123"

        # Mock subscription
        mock_subscription = MagicMock()
        mock_subscription.items.data = [MagicMock()]
        mock_subscription.items.data[0].price.id = "price_starter"

        with (
            patch(
                "bo1.state.repositories.workspace_repository.workspace_repository"
            ) as mock_workspace_repo,
            patch("backend.api.billing.user_repository") as mock_user_repo,
            patch("backend.services.stripe_service.stripe_service") as mock_stripe,
        ):
            # Workspace customer found
            mock_workspace_repo.get_workspace_by_stripe_customer.return_value = {
                "id": workspace_id,
                "name": "Test Workspace",
            }

            # Set up stripe service mock as async
            async def mock_get_sub(sub_id):
                return mock_subscription

            mock_stripe.get_subscription = mock_get_sub
            mock_stripe.get_tier_for_price.return_value = "starter"

            await _handle_checkout_completed(mock_session)

            # Should update workspace, not user
            mock_workspace_repo.set_subscription.assert_called_once_with(
                workspace_id, "sub_test123", "starter"
            )
            mock_user_repo.save_stripe_subscription.assert_not_called()

    @pytest.mark.asyncio
    async def test_checkout_completed_for_user(self):
        """Should update user tier when not a workspace customer."""
        from backend.api.billing import _handle_checkout_completed

        mock_session = MagicMock()
        mock_session.customer = "cus_user_123"
        mock_session.subscription = "sub_test123"

        mock_subscription = MagicMock()
        mock_subscription.items.data = [MagicMock()]
        mock_subscription.items.data[0].price.id = "price_starter"

        with (
            patch(
                "bo1.state.repositories.workspace_repository.workspace_repository"
            ) as mock_workspace_repo,
            patch("backend.api.billing.user_repository") as mock_user_repo,
            patch("backend.services.stripe_service.stripe_service") as mock_stripe,
        ):
            # No workspace customer
            mock_workspace_repo.get_workspace_by_stripe_customer.return_value = None
            # User customer found
            mock_user_repo.get_user_by_stripe_customer.return_value = {
                "id": "user_123",
            }

            async def mock_get_sub(sub_id):
                return mock_subscription

            mock_stripe.get_subscription = mock_get_sub
            mock_stripe.get_tier_for_price.return_value = "starter"

            await _handle_checkout_completed(mock_session)

            # Should update user, not workspace
            mock_user_repo.save_stripe_subscription.assert_called_once_with(
                "user_123", "sub_test123", "starter"
            )
            mock_workspace_repo.set_subscription.assert_not_called()

    @pytest.mark.asyncio
    async def test_subscription_deleted_for_workspace(self):
        """Should clear workspace subscription on deletion."""
        from backend.api.billing import _handle_subscription_deleted

        workspace_id = uuid.uuid4()

        mock_subscription = MagicMock()
        mock_subscription.customer = "cus_workspace_123"

        with (
            patch(
                "bo1.state.repositories.workspace_repository.workspace_repository"
            ) as mock_workspace_repo,
            patch("backend.api.billing.user_repository") as mock_user_repo,
        ):
            mock_workspace_repo.get_workspace_by_stripe_customer.return_value = {
                "id": workspace_id,
            }

            await _handle_subscription_deleted(mock_subscription)

            mock_workspace_repo.clear_subscription.assert_called_once_with(workspace_id)
            mock_user_repo.clear_stripe_subscription.assert_not_called()

    @pytest.mark.asyncio
    async def test_subscription_updated_for_workspace(self):
        """Should update workspace tier on subscription update."""
        from backend.api.billing import _handle_subscription_updated

        workspace_id = uuid.uuid4()

        mock_subscription = MagicMock()
        mock_subscription.customer = "cus_workspace_123"
        mock_subscription.id = "sub_test123"
        mock_subscription.status = "active"
        mock_subscription.items.data = [MagicMock()]
        mock_subscription.items.data[0].price.id = "price_pro"

        with (
            patch(
                "bo1.state.repositories.workspace_repository.workspace_repository"
            ) as mock_workspace_repo,
            patch("backend.api.billing.user_repository") as mock_user_repo,
            patch("backend.services.stripe_service.stripe_service") as mock_stripe,
        ):
            mock_workspace_repo.get_workspace_by_stripe_customer.return_value = {
                "id": workspace_id,
            }
            mock_stripe.get_tier_for_price.return_value = "pro"

            await _handle_subscription_updated(mock_subscription)

            mock_workspace_repo.set_subscription.assert_called_once_with(
                workspace_id, "sub_test123", "pro"
            )
            mock_user_repo.save_stripe_subscription.assert_not_called()


class TestWorkspaceBillingService:
    """Tests for workspace billing service."""

    def test_get_billing_info_success(self):
        """Should return billing info for workspace."""
        from backend.services.workspace_billing import workspace_billing_service

        workspace_id = uuid.uuid4()
        user_id = "test-user-123"

        with patch("backend.services.workspace_billing.workspace_repository") as mock_repo:
            mock_repo.get_billing_info.return_value = {
                "workspace_id": workspace_id,
                "name": "Test Workspace",
                "stripe_customer_id": "cus_test123",
                "stripe_subscription_id": "sub_test123",
                "billing_email": "billing@test.com",
                "tier": "starter",
                "billing_owner_id": user_id,
                "owner_id": user_id,
            }

            info = workspace_billing_service.get_billing_info(workspace_id, user_id)

            assert info.workspace_name == "Test Workspace"
            assert info.tier == "starter"
            assert info.is_billing_owner is True

    def test_get_billing_info_not_billing_owner(self):
        """Should correctly identify non-billing owner."""
        from backend.services.workspace_billing import workspace_billing_service

        workspace_id = uuid.uuid4()
        user_id = "test-user-123"
        other_user = "other-user-456"

        with patch("backend.services.workspace_billing.workspace_repository") as mock_repo:
            mock_repo.get_billing_info.return_value = {
                "workspace_id": workspace_id,
                "name": "Test Workspace",
                "stripe_customer_id": "cus_test123",
                "stripe_subscription_id": "sub_test123",
                "billing_email": "billing@test.com",
                "tier": "starter",
                "billing_owner_id": other_user,
                "owner_id": other_user,
            }

            info = workspace_billing_service.get_billing_info(workspace_id, user_id)

            assert info.is_billing_owner is False

    def test_get_workspace_tier(self):
        """Should return workspace tier."""
        from backend.services.workspace_billing import workspace_billing_service

        workspace_id = uuid.uuid4()

        with patch("backend.services.workspace_billing.workspace_repository") as mock_repo:
            mock_repo.get_workspace_tier.return_value = "pro"

            tier = workspace_billing_service.get_workspace_tier(workspace_id)

            assert tier == "pro"
            mock_repo.get_workspace_tier.assert_called_once_with(workspace_id)
