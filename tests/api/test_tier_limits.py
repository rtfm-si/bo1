"""Tests for tier limit enforcement middleware.

Validates:
- require_meeting_limit checks and enforces monthly meeting limits
- require_dataset_limit checks and enforces total dataset limits
- require_mentor_limit checks and enforces daily mentor chat limits
- TierLimitError returns 429 with upgrade prompt
- Admin overrides bypass tier limits
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from backend.api.middleware.tier_limits import (
    TierLimitError,
    record_dataset_usage,
    record_meeting_usage,
    record_mentor_usage,
    require_dataset_limit,
    require_meeting_limit,
    require_mentor_limit,
)
from backend.services.usage_tracking import UsageResult


@pytest.mark.unit
class TestTierLimitError:
    """Test TierLimitError exception."""

    def test_tier_limit_error_status_code(self) -> None:
        """TierLimitError should have 429 status code."""
        result = UsageResult(
            allowed=False,
            current=3,
            limit=3,
            remaining=0,
            reset_at=datetime.now(UTC) + timedelta(days=1),
        )
        error = TierLimitError(result, "meetings_monthly")
        assert error.status_code == 429

    def test_tier_limit_error_detail(self) -> None:
        """TierLimitError detail should include usage info."""
        reset_time = datetime.now(UTC) + timedelta(days=1)
        result = UsageResult(
            allowed=False,
            current=3,
            limit=3,
            remaining=0,
            reset_at=reset_time,
        )
        error = TierLimitError(result, "meetings_monthly")

        assert error.detail["error"] == "tier_limit_exceeded"
        assert error.detail["metric"] == "meetings_monthly"
        assert error.detail["current"] == 3
        assert error.detail["limit"] == 3
        assert error.detail["remaining"] == 0
        assert error.detail["upgrade_prompt"] == "Upgrade your plan to increase your limits."

    def test_tier_limit_error_no_reset_time(self) -> None:
        """TierLimitError should handle None reset_at."""
        result = UsageResult(
            allowed=False,
            current=5,
            limit=5,
            remaining=0,
            reset_at=None,
        )
        error = TierLimitError(result, "datasets_total")
        assert error.detail["reset_at"] is None


@pytest.mark.unit
class TestRequireMeetingLimit:
    """Test require_meeting_limit dependency."""

    @pytest.mark.asyncio
    @patch("backend.api.middleware.tier_limits.check_limit")
    @patch("backend.api.middleware.tier_limits.get_effective_tier")
    @patch("backend.api.middleware.tier_limits.extract_user_id")
    async def test_allows_when_under_limit(
        self,
        mock_extract_user: MagicMock,
        mock_get_tier: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Should allow meeting creation when under limit."""
        mock_extract_user.return_value = "user123"
        mock_get_tier.return_value = "free"
        mock_check.return_value = UsageResult(
            allowed=True, current=2, limit=3, remaining=1, reset_at=None
        )

        request = MagicMock()
        user = {"id": "user123", "subscription_tier": "free"}

        result = await require_meeting_limit(request, user)

        assert result.allowed is True
        assert result.remaining == 1

    @pytest.mark.asyncio
    @patch("backend.api.middleware.tier_limits.check_limit")
    @patch("backend.api.middleware.tier_limits.get_effective_tier")
    @patch("backend.api.middleware.tier_limits.extract_user_id")
    async def test_blocks_when_at_limit(
        self,
        mock_extract_user: MagicMock,
        mock_get_tier: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Should raise TierLimitError when at limit."""
        mock_extract_user.return_value = "user123"
        mock_get_tier.return_value = "free"
        mock_check.return_value = UsageResult(
            allowed=False, current=3, limit=3, remaining=0, reset_at=None
        )

        request = MagicMock()
        user = {"id": "user123", "subscription_tier": "free"}

        with pytest.raises(TierLimitError) as exc_info:
            await require_meeting_limit(request, user)

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["metric"] == "meetings_monthly"


@pytest.mark.unit
class TestRequireDatasetLimit:
    """Test require_dataset_limit dependency."""

    @pytest.mark.asyncio
    @patch("backend.api.middleware.tier_limits.check_limit")
    @patch("backend.api.middleware.tier_limits.get_effective_tier")
    @patch("backend.api.middleware.tier_limits.extract_user_id")
    async def test_allows_when_under_limit(
        self,
        mock_extract_user: MagicMock,
        mock_get_tier: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Should allow dataset upload when under limit."""
        mock_extract_user.return_value = "user123"
        mock_get_tier.return_value = "starter"
        mock_check.return_value = UsageResult(
            allowed=True, current=10, limit=25, remaining=15, reset_at=None
        )

        request = MagicMock()
        user = {"id": "user123", "subscription_tier": "starter"}

        result = await require_dataset_limit(request, user)

        assert result.allowed is True
        assert result.remaining == 15

    @pytest.mark.asyncio
    @patch("backend.api.middleware.tier_limits.check_limit")
    @patch("backend.api.middleware.tier_limits.get_effective_tier")
    @patch("backend.api.middleware.tier_limits.extract_user_id")
    async def test_blocks_when_at_limit(
        self,
        mock_extract_user: MagicMock,
        mock_get_tier: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Should raise TierLimitError when at limit."""
        mock_extract_user.return_value = "user123"
        mock_get_tier.return_value = "free"
        mock_check.return_value = UsageResult(
            allowed=False, current=5, limit=5, remaining=0, reset_at=None
        )

        request = MagicMock()
        user = {"id": "user123", "subscription_tier": "free"}

        with pytest.raises(TierLimitError) as exc_info:
            await require_dataset_limit(request, user)

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["metric"] == "datasets_total"


@pytest.mark.unit
class TestRequireMentorLimit:
    """Test require_mentor_limit dependency."""

    @pytest.mark.asyncio
    @patch("backend.api.middleware.tier_limits.check_limit")
    @patch("backend.api.middleware.tier_limits.get_effective_tier")
    @patch("backend.api.middleware.tier_limits.extract_user_id")
    async def test_allows_when_under_limit(
        self,
        mock_extract_user: MagicMock,
        mock_get_tier: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Should allow mentor chat when under limit."""
        mock_extract_user.return_value = "user123"
        mock_get_tier.return_value = "free"
        mock_check.return_value = UsageResult(
            allowed=True, current=5, limit=10, remaining=5, reset_at=None
        )

        request = MagicMock()
        user = {"id": "user123", "subscription_tier": "free"}

        result = await require_mentor_limit(request, user)

        assert result.allowed is True
        assert result.remaining == 5

    @pytest.mark.asyncio
    @patch("backend.api.middleware.tier_limits.check_limit")
    @patch("backend.api.middleware.tier_limits.get_effective_tier")
    @patch("backend.api.middleware.tier_limits.extract_user_id")
    async def test_blocks_when_at_limit(
        self,
        mock_extract_user: MagicMock,
        mock_get_tier: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Should raise TierLimitError when at daily limit."""
        mock_extract_user.return_value = "user123"
        mock_get_tier.return_value = "free"
        mock_check.return_value = UsageResult(
            allowed=False, current=10, limit=10, remaining=0, reset_at=None
        )

        request = MagicMock()
        user = {"id": "user123", "subscription_tier": "free"}

        with pytest.raises(TierLimitError) as exc_info:
            await require_mentor_limit(request, user)

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["metric"] == "mentor_daily"

    @pytest.mark.asyncio
    @patch("backend.api.middleware.tier_limits.check_limit")
    @patch("backend.api.middleware.tier_limits.get_effective_tier")
    @patch("backend.api.middleware.tier_limits.extract_user_id")
    async def test_pro_unlimited_always_allows(
        self,
        mock_extract_user: MagicMock,
        mock_get_tier: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Pro tier should have unlimited mentor chats."""
        mock_extract_user.return_value = "user123"
        mock_get_tier.return_value = "pro"
        mock_check.return_value = UsageResult(
            allowed=True, current=1000, limit=-1, remaining=-1, reset_at=None
        )

        request = MagicMock()
        user = {"id": "user123", "subscription_tier": "pro"}

        result = await require_mentor_limit(request, user)

        assert result.allowed is True
        assert result.limit == -1


@pytest.mark.unit
class TestRecordUsage:
    """Test usage recording functions."""

    @patch("backend.api.middleware.tier_limits.increment_usage")
    def test_record_meeting_usage(self, mock_increment: MagicMock) -> None:
        """record_meeting_usage should increment meetings_created."""
        mock_increment.return_value = 5

        result = record_meeting_usage("user123")

        assert result == 5
        mock_increment.assert_called_once_with("user123", "meetings_created")

    @patch("backend.api.middleware.tier_limits.increment_usage")
    def test_record_dataset_usage(self, mock_increment: MagicMock) -> None:
        """record_dataset_usage should increment datasets_uploaded."""
        mock_increment.return_value = 10

        result = record_dataset_usage("user123")

        assert result == 10
        mock_increment.assert_called_once_with("user123", "datasets_uploaded")

    @patch("backend.api.middleware.tier_limits.increment_usage")
    def test_record_mentor_usage(self, mock_increment: MagicMock) -> None:
        """record_mentor_usage should increment mentor_chats."""
        mock_increment.return_value = 3

        result = record_mentor_usage("user123")

        assert result == 3
        mock_increment.assert_called_once_with("user123", "mentor_chats")


@pytest.mark.unit
class TestTierOverrideIntegration:
    """Test tier override affects limit checks."""

    @pytest.mark.asyncio
    @patch("backend.api.middleware.tier_limits.check_limit")
    @patch("backend.api.middleware.tier_limits.get_effective_tier")
    @patch("backend.api.middleware.tier_limits.extract_user_id")
    async def test_override_elevates_tier(
        self,
        mock_extract_user: MagicMock,
        mock_get_tier: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Admin override should elevate user to higher tier limits."""
        mock_extract_user.return_value = "user123"
        # get_effective_tier returns "pro" because of admin override
        mock_get_tier.return_value = "pro"
        mock_check.return_value = UsageResult(
            allowed=True, current=50, limit=-1, remaining=-1, reset_at=None
        )

        request = MagicMock()
        user = {"id": "user123", "subscription_tier": "free"}

        result = await require_meeting_limit(request, user)

        assert result.allowed is True
        assert result.limit == -1  # Unlimited due to pro tier override
