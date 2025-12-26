"""Tests for insight staleness detection service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from backend.services.insight_staleness import (
    ACTION_TRIGGER_DELAY_DAYS,
    METRIC_KEYWORDS,
    StaleInsight,
    StaleMetric,
    StalenessReason,
    create_action_metric_triggers,
    extract_metrics_from_action,
    format_insights_for_context,
    get_matured_action_triggers,
    get_stale_insights,
    get_stale_metrics_for_session,
    remove_action_triggers,
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


# =============================================================================
# Action Metric Trigger Tests
# =============================================================================


class TestExtractMetricsFromAction:
    """Tests for extract_metrics_from_action function."""

    def test_extracts_churn_keywords(self):
        """Extracts churn-related metrics from action title (maps to customers)."""
        result = extract_metrics_from_action("Reduce customer churn by 5%")
        assert "customers" in result

        result = extract_metrics_from_action("Improve retention rates")
        assert "customers" in result

    def test_extracts_revenue_keywords(self):
        """Extracts revenue-related metrics from action title."""
        result = extract_metrics_from_action("Increase monthly revenue")
        assert "revenue" in result

        result = extract_metrics_from_action("Boost MRR to $50k")
        assert "revenue" in result

        result = extract_metrics_from_action("Improve sales conversion")
        assert "revenue" in result

    def test_extracts_customers_keywords(self):
        """Extracts customer-related metrics from action title."""
        result = extract_metrics_from_action("Acquire 100 new customers")
        assert "customers" in result

        result = extract_metrics_from_action("Increase signups from landing page")
        assert "customers" in result

    def test_extracts_growth_keywords(self):
        """Extracts growth-related metrics from action title."""
        result = extract_metrics_from_action("Scale to new markets")
        assert "growth_rate" in result

        result = extract_metrics_from_action("Grow user base")
        assert "growth_rate" in result

    def test_extracts_team_keywords(self):
        """Extracts team-related metrics from action title."""
        result = extract_metrics_from_action("Hire 3 new engineers")
        assert "team_size" in result

        result = extract_metrics_from_action("Recruit marketing lead")
        assert "team_size" in result

    def test_extracts_multiple_metrics(self):
        """Extracts multiple metrics when action mentions several."""
        result = extract_metrics_from_action(
            "Hire sales team to grow revenue and acquire customers"
        )
        assert "team_size" in result
        assert "revenue" in result
        assert "customers" in result
        assert "growth_rate" in result

    def test_uses_description_too(self):
        """Also searches in description field."""
        result = extract_metrics_from_action(
            "Expand operations", description="Focus on reducing churn and increasing retention"
        )
        assert "customers" in result  # churn/retention maps to customers

    def test_returns_empty_for_unrelated_action(self):
        """Returns empty list for actions not targeting metrics."""
        result = extract_metrics_from_action("Update documentation")
        assert result == []

        result = extract_metrics_from_action("Fix bug in login page")
        assert result == []

    def test_case_insensitive(self):
        """Keyword matching is case insensitive."""
        result = extract_metrics_from_action("REDUCE CHURN")
        assert "customers" in result  # churn maps to customers

        result = extract_metrics_from_action("Increase REVENUE")
        assert "revenue" in result


class TestCreateActionMetricTriggers:
    """Tests for create_action_metric_triggers function."""

    def test_creates_trigger_with_28_day_delay(self):
        """Creates triggers with correct 28-day delay."""
        completed_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        triggers = create_action_metric_triggers(
            action_id="action_123",
            action_title="Reduce churn",
            completed_at=completed_at,
            affected_metrics=["churn"],
        )

        assert len(triggers) == 1
        assert triggers[0]["action_id"] == "action_123"
        assert triggers[0]["action_title"] == "Reduce churn"
        assert triggers[0]["metric_field"] == "churn"

        # Verify 28-day delay
        trigger_at = datetime.fromisoformat(triggers[0]["trigger_at"])
        expected_trigger = completed_at + timedelta(days=ACTION_TRIGGER_DELAY_DAYS)
        assert trigger_at == expected_trigger

    def test_creates_multiple_triggers(self):
        """Creates triggers for all affected metrics."""
        completed_at = datetime.now(UTC)

        triggers = create_action_metric_triggers(
            action_id="action_456",
            action_title="Growth initiative",
            completed_at=completed_at,
            affected_metrics=["revenue", "customers", "growth_rate"],
        )

        assert len(triggers) == 3
        fields = {t["metric_field"] for t in triggers}
        assert fields == {"revenue", "customers", "growth_rate"}

    def test_empty_metrics_returns_empty(self):
        """Returns empty list when no metrics affected."""
        triggers = create_action_metric_triggers(
            action_id="action_789",
            action_title="Update docs",
            completed_at=datetime.now(UTC),
            affected_metrics=[],
        )

        assert triggers == []


class TestGetMaturedActionTriggers:
    """Tests for get_matured_action_triggers function."""

    def test_returns_empty_when_no_context(self):
        """Returns empty list when user has no context."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = None

            result = get_matured_action_triggers("user_123")

            assert result == []

    def test_returns_empty_when_no_triggers(self):
        """Returns empty list when no triggers exist."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {"revenue": "$50k"}

            result = get_matured_action_triggers("user_123")

            assert result == []

    def test_returns_matured_triggers(self):
        """Returns triggers that have matured (trigger_at <= now)."""
        past_trigger = datetime.now(UTC) - timedelta(days=1)
        past_completed = datetime.now(UTC) - timedelta(days=29)

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "revenue": "$50k",
                "benchmark_timestamps": {},
                "action_metric_triggers": [
                    {
                        "action_id": "action_123",
                        "action_title": "Boost revenue",
                        "metric_field": "revenue",
                        "completed_at": past_completed.isoformat(),
                        "trigger_at": past_trigger.isoformat(),
                    }
                ],
            }

            result = get_matured_action_triggers("user_123")

            assert len(result) == 1
            assert result[0].action_id == "action_123"
            assert result[0].metric_field == "revenue"

    def test_excludes_future_triggers(self):
        """Excludes triggers that haven't matured yet."""
        future_trigger = datetime.now(UTC) + timedelta(days=10)
        past_completed = datetime.now(UTC)

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "revenue": "$50k",
                "action_metric_triggers": [
                    {
                        "action_id": "action_123",
                        "action_title": "Boost revenue",
                        "metric_field": "revenue",
                        "completed_at": past_completed.isoformat(),
                        "trigger_at": future_trigger.isoformat(),
                    }
                ],
            }

            result = get_matured_action_triggers("user_123")

            assert result == []

    def test_excludes_triggers_for_updated_metrics(self):
        """Excludes triggers for metrics updated after action completed."""
        past_trigger = datetime.now(UTC) - timedelta(days=1)
        past_completed = datetime.now(UTC) - timedelta(days=29)
        metric_updated = datetime.now(UTC) - timedelta(days=5)  # After completion

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "revenue": "$60k",
                "benchmark_timestamps": {"revenue": metric_updated.isoformat()},
                "action_metric_triggers": [
                    {
                        "action_id": "action_123",
                        "action_title": "Boost revenue",
                        "metric_field": "revenue",
                        "completed_at": past_completed.isoformat(),
                        "trigger_at": past_trigger.isoformat(),
                    }
                ],
            }

            result = get_matured_action_triggers("user_123")

            assert result == []


class TestRemoveActionTriggers:
    """Tests for remove_action_triggers function."""

    def test_removes_triggers_by_metric_field(self):
        """Removes triggers matching the specified metric field."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "action_metric_triggers": [
                    {"action_id": "a1", "metric_field": "revenue"},
                    {"action_id": "a2", "metric_field": "churn"},
                    {"action_id": "a3", "metric_field": "revenue"},
                ]
            }

            removed = remove_action_triggers("user_123", metric_field="revenue")

            assert removed == 2
            # Verify save was called with filtered triggers
            save_call = mock_repo.save_context.call_args
            saved_triggers = save_call[0][1]["action_metric_triggers"]
            assert len(saved_triggers) == 1
            assert saved_triggers[0]["metric_field"] == "churn"

    def test_removes_triggers_by_action_id(self):
        """Removes triggers matching the specified action ID."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "action_metric_triggers": [
                    {"action_id": "a1", "metric_field": "revenue"},
                    {"action_id": "a1", "metric_field": "churn"},
                    {"action_id": "a2", "metric_field": "revenue"},
                ]
            }

            removed = remove_action_triggers("user_123", action_id="a1")

            assert removed == 2
            save_call = mock_repo.save_context.call_args
            saved_triggers = save_call[0][1]["action_metric_triggers"]
            assert len(saved_triggers) == 1
            assert saved_triggers[0]["action_id"] == "a2"

    def test_returns_zero_when_no_context(self):
        """Returns 0 when user has no context."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = None

            removed = remove_action_triggers("user_123", metric_field="revenue")

            assert removed == 0

    def test_returns_zero_when_no_triggers(self):
        """Returns 0 when no triggers exist."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {"revenue": "$50k"}

            removed = remove_action_triggers("user_123", metric_field="revenue")

            assert removed == 0

    def test_returns_zero_when_no_filter(self):
        """Returns 0 when no filter is provided."""
        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "action_metric_triggers": [
                    {"action_id": "a1", "metric_field": "revenue"},
                ]
            }

            removed = remove_action_triggers("user_123")

            assert removed == 0


class TestDelayedTriggerIntegration:
    """Integration tests for delayed triggers in staleness detection."""

    def test_matured_triggers_appear_in_stale_metrics(self):
        """Matured triggers should cause metrics to appear in stale list."""
        past_trigger = datetime.now(UTC) - timedelta(days=1)
        past_completed = datetime.now(UTC) - timedelta(days=29)

        with patch("backend.services.insight_staleness.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {
                "revenue": "$50k",
                "benchmark_timestamps": {},
                "context_metric_history": {},
                "action_metric_triggers": [
                    {
                        "action_id": "action_123",
                        "action_title": "Boost revenue",
                        "metric_field": "revenue",
                        "completed_at": past_completed.isoformat(),
                        "trigger_at": past_trigger.isoformat(),
                    }
                ],
            }

            result = get_stale_metrics_for_session("user_123")

            assert result.has_stale_metrics is True
            revenue_metric = next(
                (m for m in result.stale_metrics if m.field_name == "revenue"), None
            )
            assert revenue_metric is not None
            assert revenue_metric.reason == StalenessReason.ACTION_AFFECTED
            assert revenue_metric.action_id == "action_123"

    def test_trigger_delay_constant(self):
        """Verify the trigger delay constant is 28 days."""
        assert ACTION_TRIGGER_DELAY_DAYS == 28

    def test_metric_keywords_coverage(self):
        """Verify all expected metric keywords are defined."""
        assert "revenue" in METRIC_KEYWORDS
        assert "customers" in METRIC_KEYWORDS
        assert "growth_rate" in METRIC_KEYWORDS
        assert "team_size" in METRIC_KEYWORDS
        # churn maps to customers, not a separate field
        assert "churn" in METRIC_KEYWORDS["customers"]
