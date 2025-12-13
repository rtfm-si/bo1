"""Unit tests for trend calculator service."""

from datetime import UTC, datetime, timedelta

from backend.api.context.models import TrendDirection
from backend.services.trend_calculator import (
    POSITIVE_DIRECTION_FIELDS,
    calculate_all_trends,
    calculate_trend,
    extract_numeric_value,
)


class TestExtractNumericValue:
    """Test numeric value extraction from various formats."""

    def test_plain_integer(self):
        """Test extracting plain integer."""
        assert extract_numeric_value(50000) == 50000.0

    def test_plain_float(self):
        """Test extracting plain float."""
        assert extract_numeric_value(50.5) == 50.5

    def test_currency_no_suffix(self):
        """Test currency without K/M suffix."""
        assert extract_numeric_value("$50,000") == 50000.0

    def test_currency_k_suffix(self):
        """Test currency with K suffix."""
        assert extract_numeric_value("$50K") == 50000.0
        assert extract_numeric_value("$50k") == 50000.0

    def test_currency_m_suffix(self):
        """Test currency with M suffix."""
        assert extract_numeric_value("$1.5M") == 1500000.0
        assert extract_numeric_value("$1.5m") == 1500000.0

    def test_percentage(self):
        """Test percentage extraction."""
        assert extract_numeric_value("15%") == 15.0
        assert extract_numeric_value("15.5%") == 15.5

    def test_plain_number_string(self):
        """Test plain number as string."""
        assert extract_numeric_value("1000") == 1000.0
        assert extract_numeric_value("1,000") == 1000.0

    def test_team_size_buckets(self):
        """Test team size bucket extraction."""
        assert extract_numeric_value("solo") == 1.0
        assert extract_numeric_value("small (2-5)") == 3.5
        assert extract_numeric_value("medium (6-20)") == 13.0
        assert extract_numeric_value("large (20+)") == 50.0

    def test_none_input(self):
        """Test None input returns None."""
        assert extract_numeric_value(None) is None

    def test_non_numeric_text(self):
        """Test non-numeric text returns None."""
        assert extract_numeric_value("hello world") is None
        assert extract_numeric_value("no numbers here") is None


class TestCalculateTrend:
    """Test trend calculation for individual metrics."""

    def test_insufficient_data_empty_history(self):
        """Test with empty history."""
        trend = calculate_trend("revenue", [])
        assert trend.direction == TrendDirection.INSUFFICIENT_DATA

    def test_insufficient_data_single_entry(self):
        """Test with single history entry."""
        history = [
            {
                "value": "$50K",
                "recorded_at": datetime.now(UTC).isoformat(),
            }
        ]
        trend = calculate_trend("revenue", history)
        assert trend.direction == TrendDirection.INSUFFICIENT_DATA

    def test_improving_positive_field(self):
        """Test improving trend for positive direction field (revenue)."""
        now = datetime.now(UTC)
        history = [
            {
                "value": "$60K",
                "recorded_at": now.isoformat(),
            },
            {
                "value": "$50K",
                "recorded_at": (now - timedelta(days=30)).isoformat(),
            },
        ]
        trend = calculate_trend("revenue", history)
        assert trend.direction == TrendDirection.IMPROVING
        assert trend.change_percent is not None
        assert trend.change_percent > 0

    def test_worsening_positive_field(self):
        """Test worsening trend for positive direction field."""
        now = datetime.now(UTC)
        history = [
            {
                "value": "$40K",
                "recorded_at": now.isoformat(),
            },
            {
                "value": "$50K",
                "recorded_at": (now - timedelta(days=30)).isoformat(),
            },
        ]
        trend = calculate_trend("revenue", history)
        assert trend.direction == TrendDirection.WORSENING
        assert trend.change_percent is not None
        assert trend.change_percent < 0

    def test_stable_small_change(self):
        """Test stable when change is small (<5%)."""
        now = datetime.now(UTC)
        history = [
            {
                "value": "102",
                "recorded_at": now.isoformat(),
            },
            {
                "value": "100",
                "recorded_at": (now - timedelta(days=30)).isoformat(),
            },
        ]
        trend = calculate_trend("customers", history)
        assert trend.direction == TrendDirection.STABLE

    def test_period_description_days(self):
        """Test period description for days."""
        now = datetime.now(UTC)
        history = [
            {
                "value": "100",
                "recorded_at": now.isoformat(),
            },
            {
                "value": "50",
                "recorded_at": (now - timedelta(days=3)).isoformat(),
            },
        ]
        trend = calculate_trend("customers", history)
        assert trend.period_description is not None
        assert "days" in trend.period_description

    def test_period_description_weeks(self):
        """Test period description for weeks."""
        now = datetime.now(UTC)
        history = [
            {
                "value": "100",
                "recorded_at": now.isoformat(),
            },
            {
                "value": "50",
                "recorded_at": (now - timedelta(days=14)).isoformat(),
            },
        ]
        trend = calculate_trend("customers", history)
        assert trend.period_description is not None
        assert "week" in trend.period_description

    def test_text_value_comparison(self):
        """Test trend with non-numeric text values."""
        now = datetime.now(UTC)
        history = [
            {
                "value": "growing",
                "recorded_at": now.isoformat(),
            },
            {
                "value": "early",
                "recorded_at": (now - timedelta(days=30)).isoformat(),
            },
        ]
        trend = calculate_trend("business_stage", history)
        # Can't determine direction numerically, but should not crash
        assert trend.current_value == "growing"
        assert trend.previous_value == "early"


class TestCalculateAllTrends:
    """Test calculating trends for all metrics."""

    def test_empty_history(self):
        """Test with no metric history."""
        trends = calculate_all_trends({})
        assert trends == []

    def test_multiple_metrics(self):
        """Test with multiple metrics."""
        now = datetime.now(UTC)
        history = {
            "revenue": [
                {"value": "$60K", "recorded_at": now.isoformat()},
                {"value": "$50K", "recorded_at": (now - timedelta(days=30)).isoformat()},
            ],
            "customers": [
                {"value": "150", "recorded_at": now.isoformat()},
                {"value": "100", "recorded_at": (now - timedelta(days=30)).isoformat()},
            ],
        }
        trends = calculate_all_trends(history)
        assert len(trends) == 2

        revenue_trend = next((t for t in trends if t.field_name == "revenue"), None)
        customer_trend = next((t for t in trends if t.field_name == "customers"), None)

        assert revenue_trend is not None
        assert customer_trend is not None
        assert revenue_trend.direction == TrendDirection.IMPROVING
        assert customer_trend.direction == TrendDirection.IMPROVING

    def test_single_entry_metrics_included(self):
        """Test that metrics with single entry are included."""
        now = datetime.now(UTC)
        history = {
            "revenue": [
                {"value": "$50K", "recorded_at": now.isoformat()},
            ],
        }
        trends = calculate_all_trends(history)
        assert len(trends) == 1
        assert trends[0].direction == TrendDirection.INSUFFICIENT_DATA


class TestPositiveDirectionFields:
    """Test the positive direction field set."""

    def test_expected_fields_present(self):
        """Test expected fields are in POSITIVE_DIRECTION_FIELDS."""
        expected = ["revenue", "customers", "growth_rate", "mau_bucket", "team_size"]
        for field in expected:
            assert field in POSITIVE_DIRECTION_FIELDS
