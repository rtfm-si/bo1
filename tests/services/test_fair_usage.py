"""Tests for FairUsageService."""

from unittest.mock import patch

import pytest

from backend.services.fair_usage import (
    FairUsageService,
    UsageStatus,
    get_fair_usage_service,
)


class TestFairUsageService:
    """Tests for FairUsageService."""

    def test_check_fair_usage_unlimited_tier(self) -> None:
        """Enterprise tier has unlimited fair usage."""
        result = FairUsageService.check_fair_usage(
            user_id="test_user",
            feature="mentor_chat",
            tier="enterprise",
        )
        assert result.status == UsageStatus.ALLOWED
        assert result.daily_limit < 0  # Unlimited
        assert result.remaining < 0  # Unlimited

    def test_check_fair_usage_under_limit(self) -> None:
        """User under daily limit should be allowed."""
        with patch.object(FairUsageService, "get_user_daily_cost", return_value=0.10):
            result = FairUsageService.check_fair_usage(
                user_id="test_user",
                feature="mentor_chat",
                tier="free",  # $0.50 daily limit
            )
            assert result.status == UsageStatus.ALLOWED
            assert result.current_cost == 0.10
            assert result.daily_limit == 0.50
            assert result.percent_used == pytest.approx(0.20, rel=0.01)

    def test_check_fair_usage_soft_warning(self) -> None:
        """User at 85% should get soft warning."""
        with patch.object(FairUsageService, "get_user_daily_cost", return_value=0.425):
            result = FairUsageService.check_fair_usage(
                user_id="test_user",
                feature="mentor_chat",
                tier="free",  # $0.50 daily limit, soft cap at 80%
            )
            assert result.status == UsageStatus.SOFT_WARNING
            assert result.percent_used == pytest.approx(0.85, rel=0.01)
            assert result.message is not None
            assert "Approaching" in result.message

    def test_check_fair_usage_hard_blocked(self) -> None:
        """User at or over 100% should be blocked."""
        with patch.object(FairUsageService, "get_user_daily_cost", return_value=0.50):
            result = FairUsageService.check_fair_usage(
                user_id="test_user",
                feature="mentor_chat",
                tier="free",  # $0.50 daily limit
            )
            assert result.status == UsageStatus.HARD_BLOCKED
            assert result.percent_used >= 1.0
            assert result.remaining == 0.0
            assert result.message is not None
            assert "reached" in result.message.lower()

    def test_check_fair_usage_with_estimated_cost(self) -> None:
        """Estimated cost should be added to current usage."""
        with patch.object(FairUsageService, "get_user_daily_cost", return_value=0.30):
            result = FairUsageService.check_fair_usage(
                user_id="test_user",
                feature="mentor_chat",
                tier="free",  # $0.50 daily limit
                estimated_cost=0.25,  # Total projected: $0.55 (over limit)
            )
            assert result.status == UsageStatus.HARD_BLOCKED
            assert result.current_cost == 0.30

    def test_check_fair_usage_different_features(self) -> None:
        """Different features should have different limits."""
        with patch.object(FairUsageService, "get_user_daily_cost", return_value=0.0):
            mentor_result = FairUsageService.check_fair_usage(
                user_id="test_user",
                feature="mentor_chat",
                tier="free",
            )
            dataset_result = FairUsageService.check_fair_usage(
                user_id="test_user",
                feature="dataset_qa",
                tier="free",
            )
            # Free tier: mentor_chat=$0.50, dataset_qa=$0.25
            assert mentor_result.daily_limit == 0.50
            assert dataset_result.daily_limit == 0.25

    def test_check_fair_usage_starter_tier(self) -> None:
        """Starter tier should have higher limits."""
        with patch.object(FairUsageService, "get_user_daily_cost", return_value=0.0):
            result = FairUsageService.check_fair_usage(
                user_id="test_user",
                feature="mentor_chat",
                tier="starter",
            )
            # Starter tier: mentor_chat=$2.00
            assert result.daily_limit == 2.00

    def test_get_fair_usage_service_singleton(self) -> None:
        """Service should be singleton."""
        service1 = get_fair_usage_service()
        service2 = get_fair_usage_service()
        assert service1 is service2


class TestFairUsageIntegration:
    """Integration tests requiring database (mark with pytest.mark.integration)."""

    @pytest.mark.integration
    def test_get_user_daily_cost_no_data(self) -> None:
        """User with no cost records should return 0."""
        # This test requires a real DB connection
        cost = FairUsageService.get_user_daily_cost(
            user_id="nonexistent_user",
            feature="mentor_chat",
        )
        assert cost == 0.0

    @pytest.mark.integration
    def test_get_user_usage_summary_no_data(self) -> None:
        """User with no cost records should return empty dict."""
        summary = FairUsageService.get_user_usage_summary(
            user_id="nonexistent_user",
        )
        assert summary == {}
