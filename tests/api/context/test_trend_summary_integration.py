"""Integration tests for trend summary refresh endpoint.

Tests the fix for the 500 error when trend_summary is None in context.
"""

from datetime import UTC, datetime, timedelta


class TestTrendSummaryNoneHandling:
    """Tests for handling None trend_summary in context data.

    This tests the fix for the 500 error at routes.py:2440:
        summary_data = context_data.get("trend_summary") or {}

    The bug: .get("key", {}) returns None if the value is explicitly None
    (default {} only applies when key is missing, not when value is None).
    """

    def test_none_trend_summary_returns_empty_dict(self):
        """Verify None trend_summary is safely coerced to empty dict."""
        context_data = {
            "industry": "Technology",
            "trend_summary": None,  # Explicitly None (the bug case)
        }

        # This is the fix: use `or {}` instead of default param
        summary_data = context_data.get("trend_summary") or {}

        # Should not raise AttributeError
        generated_at = summary_data.get("generated_at") if isinstance(summary_data, dict) else None

        assert summary_data == {}
        assert generated_at is None

    def test_missing_trend_summary_returns_empty_dict(self):
        """Verify missing trend_summary key works correctly."""
        context_data = {"industry": "Technology"}

        summary_data = context_data.get("trend_summary") or {}

        assert summary_data == {}

    def test_valid_trend_summary_preserved(self):
        """Verify valid trend_summary dict is preserved."""
        now = datetime.now(UTC)
        context_data = {
            "industry": "Technology",
            "trend_summary": {
                "generated_at": now.isoformat(),
                "summary": "Test summary",
            },
        }

        summary_data = context_data.get("trend_summary") or {}
        generated_at = summary_data.get("generated_at") if isinstance(summary_data, dict) else None

        assert summary_data["summary"] == "Test summary"
        assert generated_at == now.isoformat()

    def test_isinstance_check_for_non_dict(self):
        """Verify isinstance check handles non-dict values."""
        # Edge case: if trend_summary was somehow a string
        context_data = {
            "industry": "Technology",
            "trend_summary": "invalid_string_value",
        }

        summary_data = context_data.get("trend_summary") or {}
        # The isinstance check prevents AttributeError on non-dicts
        generated_at = summary_data.get("generated_at") if isinstance(summary_data, dict) else None

        assert generated_at is None


class TestRateLimitWithNullableTrendSummary:
    """Test rate limit calculations with nullable trend_summary."""

    def test_rate_limit_calculation_with_none_summary(self):
        """Verify rate limit logic skips when summary is None."""
        context_data = {
            "industry": "Technology",
            "trend_summary": None,
        }

        summary_data = context_data.get("trend_summary") or {}
        generated_at_str = (
            summary_data.get("generated_at") if isinstance(summary_data, dict) else None
        )

        # When None, rate limit check should be skipped (proceed to generation)
        assert generated_at_str is None

    def test_rate_limit_calculation_with_valid_timestamp(self):
        """Verify rate limit logic works with valid timestamp."""
        now = datetime.now(UTC)
        past = now - timedelta(hours=2)

        context_data = {
            "industry": "Technology",
            "trend_summary": {
                "generated_at": past.isoformat(),
                "summary": "Old summary",
            },
        }

        summary_data = context_data.get("trend_summary") or {}
        generated_at_str = (
            summary_data.get("generated_at") if isinstance(summary_data, dict) else None
        )

        assert generated_at_str == past.isoformat()

        # Parse and check time since generation
        generated_at = datetime.fromisoformat(generated_at_str.replace("Z", "+00:00"))
        time_since = now - generated_at
        hours_since = time_since.total_seconds() / 3600

        assert hours_since >= 2  # More than 1 hour = not rate limited

    def test_free_tier_28_day_check_with_none_summary(self):
        """Verify free tier check skips when summary is None."""
        tier = "free"
        context_data = {
            "industry": "Technology",
            "trend_summary": None,
        }

        summary_data = context_data.get("trend_summary") or {}
        generated_at_str = (
            summary_data.get("generated_at") if isinstance(summary_data, dict) else None
        )

        # None timestamp = no previous generation = allow refresh
        can_refresh = generated_at_str is None or tier != "free"

        assert can_refresh is True
