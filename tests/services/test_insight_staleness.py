"""Tests for insight staleness detection service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from backend.services.insight_staleness import (
    StaleInsight,
    format_insights_for_context,
    get_stale_insights,
)


class TestGetStaleInsights:
    """Tests for get_stale_insights function."""

    def test_no_context_returns_empty(self):
        """When user has no context, returns empty result."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = None

            result = get_stale_insights("user_123")

            assert result.has_stale_insights is False
            assert result.stale_insights == []
            assert result.total_insights == 0
            assert result.fresh_insights_count == 0

    def test_no_clarifications_returns_empty(self):
        """When user has context but no clarifications, returns empty result."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {"business_model": "SaaS"}

            result = get_stale_insights("user_123")

            assert result.has_stale_insights is False
            assert result.stale_insights == []
            assert result.total_insights == 0

    def test_fresh_insights_not_stale(self):
        """Insights updated within threshold are not marked stale."""
        yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {
                    "What is your revenue?": {
                        "answer": "$50k MRR",
                        "updated_at": yesterday,
                    }
                }
            }

            result = get_stale_insights("user_123")

            assert result.has_stale_insights is False
            assert len(result.stale_insights) == 0
            assert result.total_insights == 1
            assert result.fresh_insights_count == 1

    def test_boundary_29_days_is_fresh(self):
        """Insight at 29 days is still fresh (threshold is 30)."""
        twenty_nine_days_ago = (datetime.now(UTC) - timedelta(days=29)).isoformat()
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {"Q1": {"answer": "A1", "updated_at": twenty_nine_days_ago}}
            }

            result = get_stale_insights("user_123", threshold_days=30)

            assert result.has_stale_insights is False
            assert result.fresh_insights_count == 1

    def test_boundary_30_days_is_stale(self):
        """Insight at exactly 30 days is stale."""
        thirty_days_ago = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {"Q1": {"answer": "A1", "updated_at": thirty_days_ago}}
            }

            result = get_stale_insights("user_123", threshold_days=30)

            assert result.has_stale_insights is True
            assert len(result.stale_insights) == 1
            assert result.stale_insights[0].days_stale >= 30

    def test_boundary_31_days_is_stale(self):
        """Insight at 31 days is definitely stale."""
        thirty_one_days_ago = (datetime.now(UTC) - timedelta(days=31)).isoformat()
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {"Q1": {"answer": "A1", "updated_at": thirty_one_days_ago}}
            }

            result = get_stale_insights("user_123", threshold_days=30)

            assert result.has_stale_insights is True
            assert len(result.stale_insights) == 1
            assert result.stale_insights[0].days_stale == 31

    def test_null_updated_at_treated_as_stale(self):
        """Insights with null updated_at are treated as stale."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {"Q1": {"answer": "A1", "updated_at": None}}
            }

            result = get_stale_insights("user_123")

            assert result.has_stale_insights is True
            assert len(result.stale_insights) == 1

    def test_legacy_string_format_treated_as_stale(self):
        """Legacy format (string value only) is treated as stale."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {
                    "Q1": "A1"  # Legacy string format
                }
            }

            result = get_stale_insights("user_123")

            assert result.has_stale_insights is True
            assert len(result.stale_insights) == 1
            assert result.stale_insights[0].answer == "A1"

    def test_mixed_fresh_and_stale(self):
        """Correctly identifies mix of fresh and stale insights."""
        yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        old = (datetime.now(UTC) - timedelta(days=60)).isoformat()

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {
                    "Fresh Q": {"answer": "A1", "updated_at": yesterday},
                    "Stale Q": {"answer": "A2", "updated_at": old},
                }
            }

            result = get_stale_insights("user_123")

            assert result.has_stale_insights is True
            assert result.total_insights == 2
            assert result.fresh_insights_count == 1
            assert len(result.stale_insights) == 1
            assert result.stale_insights[0].question == "Stale Q"

    def test_custom_threshold(self):
        """Custom threshold is respected."""
        five_days_ago = (datetime.now(UTC) - timedelta(days=5)).isoformat()

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {"Q1": {"answer": "A1", "updated_at": five_days_ago}}
            }

            # 7 day threshold - 5 days old is fresh
            result = get_stale_insights("user_123", threshold_days=7)
            assert result.has_stale_insights is False

            # 3 day threshold - 5 days old is stale
            result = get_stale_insights("user_123", threshold_days=3)
            assert result.has_stale_insights is True

    def test_answered_at_fallback(self):
        """Falls back to answered_at if updated_at not present."""
        yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {"Q1": {"answer": "A1", "answered_at": yesterday}}
            }

            result = get_stale_insights("user_123")

            assert result.has_stale_insights is False
            assert result.fresh_insights_count == 1


class TestFormatInsightsForContext:
    """Tests for format_insights_for_context function."""

    def test_no_context_returns_none(self):
        """When user has no context, returns None."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = None

            result = format_insights_for_context("user_123")

            assert result is None

    def test_no_clarifications_returns_none(self):
        """When no clarifications, returns None."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {"business_model": "SaaS"}

            result = format_insights_for_context("user_123")

            assert result is None

    def test_formats_insight_with_freshness(self):
        """Formats insight with freshness indicator."""
        yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {
                    "What is your revenue?": {
                        "answer": "$50k MRR",
                        "updated_at": yesterday,
                    }
                }
            }

            result = format_insights_for_context("user_123")

            assert result is not None
            assert "What is your revenue?" in result
            assert "$50k MRR" in result
            assert "yesterday" in result

    def test_today_freshness_indicator(self):
        """Shows 'today' for today's updates."""
        today = datetime.now(UTC).isoformat()
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {"Q1": {"answer": "A1", "updated_at": today}}
            }

            result = format_insights_for_context("user_123")

            assert "(today)" in result

    def test_weeks_freshness_indicator(self):
        """Shows weeks for older updates."""
        two_weeks_ago = (datetime.now(UTC) - timedelta(days=14)).isoformat()
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {"Q1": {"answer": "A1", "updated_at": two_weeks_ago}}
            }

            result = format_insights_for_context("user_123")

            assert "2 weeks ago" in result

    def test_months_freshness_indicator(self):
        """Shows months for old updates."""
        two_months_ago = (datetime.now(UTC) - timedelta(days=60)).isoformat()
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {"Q1": {"answer": "A1", "updated_at": two_months_ago}}
            }

            result = format_insights_for_context("user_123")

            assert "2 months ago" in result

    def test_over_year_freshness_indicator(self):
        """Shows 'over a year ago' for very old updates."""
        old = (datetime.now(UTC) - timedelta(days=400)).isoformat()
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {"Q1": {"answer": "A1", "updated_at": old}}
            }

            result = format_insights_for_context("user_123")

            assert "over a year ago" in result
            assert "may be outdated" in result

    def test_respects_max_insights(self):
        """Limits output to max_insights."""
        yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        clarifications = {f"Q{i}": {"answer": f"A{i}", "updated_at": yesterday} for i in range(10)}

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {"clarifications": clarifications}

            result = format_insights_for_context("user_123", max_insights=3)

            # Count bullet points
            bullet_count = result.count("• Q")
            assert bullet_count == 3

    def test_without_freshness_indicators(self):
        """Can disable freshness indicators."""
        yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "clarifications": {"Q1": {"answer": "A1", "updated_at": yesterday}}
            }

            result = format_insights_for_context("user_123", include_freshness=False)

            assert "yesterday" not in result
            assert "Q1" in result
            assert "A1" in result


class TestStaleInsightModel:
    """Tests for StaleInsight pydantic model."""

    def test_creation(self):
        """Can create StaleInsight with required fields."""
        si = StaleInsight(
            question="What is your revenue?",
            answer="$50k MRR",
            updated_at=datetime.now(UTC),
            days_stale=35,
        )

        assert si.question == "What is your revenue?"
        assert si.answer == "$50k MRR"
        assert si.days_stale == 35

    def test_optional_session_id(self):
        """session_id is optional."""
        si = StaleInsight(
            question="Q",
            answer="A",
            updated_at=None,
            days_stale=31,
        )

        assert si.session_id is None

        si_with_session = StaleInsight(
            question="Q",
            answer="A",
            updated_at=None,
            days_stale=31,
            session_id="bo1_abc123",
        )

        assert si_with_session.session_id == "bo1_abc123"
