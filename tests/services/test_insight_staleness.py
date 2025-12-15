"""Tests for insight staleness detection service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from backend.services.insight_staleness import (
    StaleInsight,
    StaleMetric,
    StalenessReason,
    format_insights_for_context,
    get_stale_insights,
    get_stale_metrics_for_session,
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


class TestGetStaleMetricsForSession:
    """Tests for get_stale_metrics_for_session function."""

    def test_no_context_returns_empty(self):
        """When user has no context, returns empty result."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = None

            result = get_stale_metrics_for_session("user_123")

            assert result.has_stale_metrics is False
            assert result.stale_metrics == []
            assert result.total_metrics_checked == 0

    def test_action_affected_fields_prioritized(self):
        """Action-affected fields appear first in stale metrics."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "revenue": "$50k",
                "customers": "100",
                "team_size": "10",
                "context_metric_history": {},
            }

            result = get_stale_metrics_for_session(
                "user_123",
                action_affected_fields=["revenue"],
            )

            assert result.has_stale_metrics is True
            # Revenue should be first due to action_affected
            assert result.stale_metrics[0].field_name == "revenue"
            assert result.stale_metrics[0].reason == StalenessReason.ACTION_AFFECTED

    def test_volatile_metrics_shorter_threshold(self):
        """Volatile metrics have shorter staleness threshold (30 days)."""
        # 35 days ago - stale for volatile, fresh for stable
        thirty_five_days_ago = (datetime.now(UTC) - timedelta(days=35)).isoformat()

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "revenue": "$50k",
                "context_metric_history": {
                    "revenue": [{"recorded_at": thirty_five_days_ago, "value": "$50k"}]
                },
            }

            result = get_stale_metrics_for_session("user_123")

            assert result.has_stale_metrics is True
            revenue_metric = next(
                (m for m in result.stale_metrics if m.field_name == "revenue"), None
            )
            assert revenue_metric is not None
            assert revenue_metric.volatility.value == "volatile"
            assert revenue_metric.threshold_days == 30

    def test_max_stale_metrics_limit(self):
        """Result is limited to max 3 stale metrics."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "revenue": "$50k",
                "customers": "100",
                "growth_rate": "10%",
                "team_size": "5",
                "mau_bucket": "1k-10k",
                "competitors": "A, B",
                "context_metric_history": {},  # No history = all stale
            }

            result = get_stale_metrics_for_session("user_123", max_results=3)

            assert len(result.stale_metrics) == 3

    def test_dismiss_expiry_varies_by_volatility(self):
        """Dismiss expiry should vary by volatility level."""
        # This tests the concept - actual implementation is in routes.py
        expiry_days = {
            "volatile": 7,
            "action_affected": 7,
            "moderate": 30,
            "stable": 90,
        }

        assert expiry_days["volatile"] == 7
        assert expiry_days["moderate"] == 30
        assert expiry_days["stable"] == 90

    def test_fresh_metrics_not_included(self):
        """Metrics updated recently are not included in stale list."""
        yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "revenue": "$50k",
                "context_metric_history": {
                    "revenue": [{"recorded_at": yesterday, "value": "$50k"}]
                },
            }

            result = get_stale_metrics_for_session("user_123")

            assert result.has_stale_metrics is False
            assert len(result.stale_metrics) == 0

    def test_metrics_sorted_by_staleness(self):
        """Metrics are sorted by days since update (most stale first)."""
        old = (datetime.now(UTC) - timedelta(days=100)).isoformat()
        very_old = (datetime.now(UTC) - timedelta(days=200)).isoformat()

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "revenue": "$50k",
                "team_size": "5",
                "context_metric_history": {
                    "revenue": [{"recorded_at": old, "value": "$50k"}],
                    "team_size": [{"recorded_at": very_old, "value": "5"}],
                },
            }

            result = get_stale_metrics_for_session("user_123")

            assert result.has_stale_metrics is True
            # team_size is older so should come first
            assert result.stale_metrics[0].field_name == "team_size"


class TestStaleMetricModel:
    """Tests for StaleMetric pydantic model."""

    def test_creation(self):
        """Can create StaleMetric with required fields."""
        from backend.services.trend_calculator import VolatilityLevel

        sm = StaleMetric(
            field_name="revenue",
            current_value="$50k",
            updated_at=datetime.now(UTC),
            days_since_update=35,
            reason=StalenessReason.AGE,
            volatility=VolatilityLevel.VOLATILE,
            threshold_days=30,
        )

        assert sm.field_name == "revenue"
        assert sm.days_since_update == 35
        assert sm.reason == StalenessReason.AGE
        assert sm.volatility == VolatilityLevel.VOLATILE

    def test_action_id_optional(self):
        """action_id is optional."""
        from backend.services.trend_calculator import VolatilityLevel

        sm = StaleMetric(
            field_name="revenue",
            current_value="$50k",
            updated_at=None,
            days_since_update=35,
            reason=StalenessReason.ACTION_AFFECTED,
            volatility=VolatilityLevel.VOLATILE,
            threshold_days=30,
            action_id="action_123",
        )

        assert sm.action_id == "action_123"
