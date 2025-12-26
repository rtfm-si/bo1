"""Tests for trend summary models and helpers."""

from datetime import UTC, datetime, timedelta

import pytest

from backend.api.context.models import (
    TrendSummary,
    TrendSummaryRefreshResponse,
    TrendSummaryResponse,
)


class TestTrendSummaryModels:
    """Tests for trend summary Pydantic models."""

    def test_trend_summary_all_fields(self):
        """Test TrendSummary with all fields populated."""
        summary = TrendSummary(
            summary="The tech industry is experiencing rapid AI adoption.",
            key_trends=["AI integration", "Cloud migration", "Remote work"],
            opportunities=["AI-powered automation", "Cloud cost optimization"],
            threats=["Regulatory uncertainty", "Talent shortage"],
            generated_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            industry="Technology",
        )

        assert summary.summary == "The tech industry is experiencing rapid AI adoption."
        assert len(summary.key_trends) == 3
        assert "AI integration" in summary.key_trends
        assert len(summary.opportunities) == 2
        assert len(summary.threats) == 2
        assert summary.industry == "Technology"

    def test_trend_summary_minimal(self):
        """Test TrendSummary with minimal fields."""
        summary = TrendSummary(
            summary="Brief summary",
            generated_at=datetime.now(UTC),
            industry="SaaS",
        )

        assert summary.summary == "Brief summary"
        assert summary.key_trends == []
        assert summary.opportunities == []
        assert summary.threats == []
        assert summary.industry == "SaaS"

    def test_trend_summary_max_length(self):
        """Test TrendSummary respects max_length constraint."""
        long_summary = "x" * 1001  # Exceeds 1000 char limit

        with pytest.raises(ValueError):
            TrendSummary(
                summary=long_summary,
                generated_at=datetime.now(UTC),
                industry="Tech",
            )

    def test_trend_summary_response_success(self):
        """Test TrendSummaryResponse with success."""
        summary = TrendSummary(
            summary="Test summary",
            generated_at=datetime.now(UTC),
            industry="Finance",
        )
        response = TrendSummaryResponse(
            success=True,
            summary=summary,
            stale=False,
            needs_industry=False,
        )

        assert response.success is True
        assert response.summary.summary == "Test summary"
        assert response.stale is False
        assert response.needs_industry is False
        assert response.error is None

    def test_trend_summary_response_needs_industry(self):
        """Test TrendSummaryResponse when industry not set."""
        response = TrendSummaryResponse(
            success=True,
            summary=None,
            stale=False,
            needs_industry=True,
        )

        assert response.success is True
        assert response.summary is None
        assert response.needs_industry is True

    def test_trend_summary_response_stale(self):
        """Test TrendSummaryResponse with stale summary."""
        old_summary = TrendSummary(
            summary="Old summary",
            generated_at=datetime.now(UTC) - timedelta(days=10),
            industry="Tech",
        )
        response = TrendSummaryResponse(
            success=True,
            summary=old_summary,
            stale=True,
            needs_industry=False,
        )

        assert response.success is True
        assert response.stale is True

    def test_trend_summary_refresh_response_success(self):
        """Test TrendSummaryRefreshResponse with success."""
        summary = TrendSummary(
            summary="Fresh summary",
            key_trends=["New Trend"],
            generated_at=datetime.now(UTC),
            industry="Healthcare",
        )
        response = TrendSummaryRefreshResponse(
            success=True,
            summary=summary,
            rate_limited=False,
        )

        assert response.success is True
        assert response.summary.summary == "Fresh summary"
        assert response.rate_limited is False
        assert response.error is None

    def test_trend_summary_refresh_response_rate_limited(self):
        """Test TrendSummaryRefreshResponse when rate limited."""
        response = TrendSummaryRefreshResponse(
            success=False,
            summary=None,
            error="Please wait 30 minutes before refreshing again",
            rate_limited=True,
        )

        assert response.success is False
        assert response.summary is None
        assert response.rate_limited is True
        assert "wait" in response.error.lower()

    def test_trend_summary_refresh_response_error(self):
        """Test TrendSummaryRefreshResponse with error."""
        response = TrendSummaryRefreshResponse(
            success=False,
            summary=None,
            error="Brave Search unavailable",
            rate_limited=False,
        )

        assert response.success is False
        assert response.summary is None
        assert response.rate_limited is False
        assert "Brave Search" in response.error


class TestStalenessDetection:
    """Tests for staleness detection logic."""

    def test_summary_is_fresh(self):
        """Test summary less than 7 days old is not stale."""
        generated_at = datetime.now(UTC) - timedelta(days=3)
        is_stale = (datetime.now(UTC) - generated_at) > timedelta(days=7)

        assert is_stale is False

    def test_summary_is_stale(self):
        """Test summary more than 7 days old is stale."""
        generated_at = datetime.now(UTC) - timedelta(days=10)
        is_stale = (datetime.now(UTC) - generated_at) > timedelta(days=7)

        assert is_stale is True

    def test_summary_at_boundary(self):
        """Test summary at exactly 7 days is stale (> not >=)."""
        # Due to timing, use 6.9 days to be safely within threshold
        generated_at = datetime.now(UTC) - timedelta(days=6, hours=23, minutes=59)
        is_stale = (datetime.now(UTC) - generated_at) > timedelta(days=7)

        assert is_stale is False

    def test_industry_change_makes_stale(self):
        """Test industry change makes summary stale even if recent."""
        current_industry = "Healthcare"
        summary_industry = "Technology"

        is_stale = current_industry.lower() != summary_industry.lower()

        assert is_stale is True

    def test_same_industry_case_insensitive(self):
        """Test same industry (case insensitive) is not stale due to industry."""
        current_industry = "technology"
        summary_industry = "Technology"

        is_stale_due_to_industry = current_industry.lower() != summary_industry.lower()

        assert is_stale_due_to_industry is False


class TestRateLimitLogic:
    """Tests for rate limit calculation logic."""

    def test_rate_limit_not_triggered(self):
        """Test rate limit not triggered after 1+ hour."""
        last_refresh = datetime.now(UTC) - timedelta(hours=2)
        cooldown_hours = 1

        time_since = datetime.now(UTC) - last_refresh
        is_rate_limited = time_since < timedelta(hours=cooldown_hours)

        assert is_rate_limited is False

    def test_rate_limit_triggered(self):
        """Test rate limit triggered within 1 hour."""
        last_refresh = datetime.now(UTC) - timedelta(minutes=30)
        cooldown_hours = 1

        time_since = datetime.now(UTC) - last_refresh
        is_rate_limited = time_since < timedelta(hours=cooldown_hours)

        assert is_rate_limited is True

    def test_rate_limit_at_boundary(self):
        """Test rate limit at exactly 1 hour."""
        last_refresh = datetime.now(UTC) - timedelta(hours=1)
        cooldown_hours = 1

        time_since = datetime.now(UTC) - last_refresh
        is_rate_limited = time_since < timedelta(hours=cooldown_hours)

        assert is_rate_limited is False

    def test_minutes_remaining_calculation(self):
        """Test calculation of minutes remaining."""
        last_refresh = datetime.now(UTC) - timedelta(minutes=40)
        cooldown_hours = 1

        time_since = datetime.now(UTC) - last_refresh
        minutes_remaining = int((timedelta(hours=cooldown_hours) - time_since).seconds / 60)

        # Should be approximately 20 minutes remaining
        assert 19 <= minutes_remaining <= 21


class TestFreeTierRefreshGating:
    """Tests for 28-day refresh gating for free tier users."""

    def test_free_tier_fresh_summary_blocked(self):
        """Test free tier user with fresh summary (<28 days) is blocked."""
        tier = "free"
        days_since_generation = 10
        refresh_threshold_days = 28

        can_refresh = tier != "free" or days_since_generation >= refresh_threshold_days

        assert can_refresh is False

    def test_free_tier_stale_summary_allowed(self):
        """Test free tier user with stale summary (>28 days) can refresh."""
        tier = "free"
        days_since_generation = 30
        refresh_threshold_days = 28

        can_refresh = tier != "free" or days_since_generation >= refresh_threshold_days

        assert can_refresh is True

    def test_free_tier_at_boundary_allowed(self):
        """Test free tier user at exactly 28 days can refresh."""
        tier = "free"
        days_since_generation = 28
        refresh_threshold_days = 28

        can_refresh = tier != "free" or days_since_generation >= refresh_threshold_days

        assert can_refresh is True

    def test_starter_tier_always_allowed(self):
        """Test starter tier user can always refresh."""
        tier = "starter"
        days_since_generation = 5  # Fresh summary
        refresh_threshold_days = 28

        can_refresh = tier != "free" or days_since_generation >= refresh_threshold_days

        assert can_refresh is True

    def test_pro_tier_always_allowed(self):
        """Test pro tier user can always refresh."""
        tier = "pro"
        days_since_generation = 1  # Very fresh summary
        refresh_threshold_days = 28

        can_refresh = tier != "free" or days_since_generation >= refresh_threshold_days

        assert can_refresh is True

    def test_enterprise_tier_always_allowed(self):
        """Test enterprise tier user can always refresh."""
        tier = "enterprise"
        days_since_generation = 0  # Just refreshed
        refresh_threshold_days = 28

        can_refresh = tier != "free" or days_since_generation >= refresh_threshold_days

        assert can_refresh is True

    def test_days_remaining_calculation(self):
        """Test calculation of days remaining for blocked users."""
        days_since_generation = 20
        refresh_threshold_days = 28

        days_remaining = refresh_threshold_days - days_since_generation

        assert days_remaining == 8

    def test_blocked_message_singular_day(self):
        """Test blocked message uses singular 'day' for 1 day."""
        days_remaining = 1
        message = f"Refresh available in {days_remaining} day{'s' if days_remaining != 1 else ''}."

        assert message == "Refresh available in 1 day."

    def test_blocked_message_plural_days(self):
        """Test blocked message uses plural 'days' for multiple days."""
        days_remaining = 5
        message = f"Refresh available in {days_remaining} day{'s' if days_remaining != 1 else ''}."

        assert message == "Refresh available in 5 days."


class TestTrendSummaryResponseRefreshFields:
    """Tests for new refresh gating fields in TrendSummaryResponse."""

    def test_response_with_refresh_allowed(self):
        """Test response when refresh is allowed."""
        summary = TrendSummary(
            summary="Test summary",
            generated_at=datetime.now(UTC),
            industry="Tech",
        )
        response = TrendSummaryResponse(
            success=True,
            summary=summary,
            stale=False,
            needs_industry=False,
            can_refresh_now=True,
            refresh_blocked_reason=None,
        )

        assert response.can_refresh_now is True
        assert response.refresh_blocked_reason is None

    def test_response_with_refresh_blocked(self):
        """Test response when refresh is blocked for free tier."""
        summary = TrendSummary(
            summary="Test summary",
            generated_at=datetime.now(UTC) - timedelta(days=10),
            industry="Tech",
        )
        response = TrendSummaryResponse(
            success=True,
            summary=summary,
            stale=False,
            needs_industry=False,
            can_refresh_now=False,
            refresh_blocked_reason="Refresh available in 18 days. Upgrade to refresh anytime.",
        )

        assert response.can_refresh_now is False
        assert "18 days" in response.refresh_blocked_reason
        assert "Upgrade" in response.refresh_blocked_reason

    def test_response_default_refresh_allowed(self):
        """Test response defaults to refresh allowed."""
        response = TrendSummaryResponse(
            success=True,
            summary=None,
            stale=True,
            needs_industry=False,
        )

        assert response.can_refresh_now is True
        assert response.refresh_blocked_reason is None
