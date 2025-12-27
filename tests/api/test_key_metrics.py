"""Unit tests for key metrics API endpoints and Pydantic models.

Tests:
- Model validation for KeyMetricConfig, KeyMetricDisplay, KeyMetricsResponse
- Model validation for MetricImportance and MetricSourceCategory enums
- API endpoint behavior (via model validation)
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.api.context.models import (
    KeyMetricConfig,
    KeyMetricConfigUpdate,
    KeyMetricDisplay,
    KeyMetricsResponse,
    KeyMetricsSuggestResponse,
    KeyMetricSuggestion,
    MetricImportance,
    MetricSourceCategory,
    MetricTrendIndicator,
)

# Note: datetime/UTC used in test_full_valid_display


class TestMetricImportanceEnum:
    """Tests for MetricImportance enum."""

    def test_valid_now(self):
        """Test 'now' importance level."""
        assert MetricImportance.NOW == "now"
        assert MetricImportance("now") == MetricImportance.NOW

    def test_valid_later(self):
        """Test 'later' importance level."""
        assert MetricImportance.LATER == "later"
        assert MetricImportance("later") == MetricImportance.LATER

    def test_valid_monitor(self):
        """Test 'monitor' importance level."""
        assert MetricImportance.MONITOR == "monitor"
        assert MetricImportance("monitor") == MetricImportance.MONITOR

    def test_invalid_importance(self):
        """Test invalid importance level raises error."""
        with pytest.raises(ValueError):
            MetricImportance("urgent")


class TestMetricSourceCategoryEnum:
    """Tests for MetricSourceCategory enum."""

    def test_valid_user(self):
        """Test 'user' category."""
        assert MetricSourceCategory.USER == "user"

    def test_valid_competitor(self):
        """Test 'competitor' category."""
        assert MetricSourceCategory.COMPETITOR == "competitor"

    def test_valid_industry(self):
        """Test 'industry' category."""
        assert MetricSourceCategory.INDUSTRY == "industry"

    def test_invalid_category(self):
        """Test invalid category raises error."""
        with pytest.raises(ValueError):
            MetricSourceCategory("external")


class TestMetricTrendIndicatorEnum:
    """Tests for MetricTrendIndicator enum."""

    def test_valid_up(self):
        """Test 'up' trend."""
        assert MetricTrendIndicator.UP == "up"

    def test_valid_down(self):
        """Test 'down' trend."""
        assert MetricTrendIndicator.DOWN == "down"

    def test_valid_stable(self):
        """Test 'stable' trend."""
        assert MetricTrendIndicator.STABLE == "stable"

    def test_valid_unknown(self):
        """Test 'unknown' trend."""
        assert MetricTrendIndicator.UNKNOWN == "unknown"


class TestKeyMetricConfigModel:
    """Tests for KeyMetricConfig Pydantic model."""

    def test_minimal_valid_config(self):
        """Test minimal valid configuration."""
        config = KeyMetricConfig(metric_key="revenue")
        assert config.metric_key == "revenue"
        assert config.importance == MetricImportance.MONITOR  # default
        assert config.category == MetricSourceCategory.USER  # default
        assert config.display_order == 0  # default

    def test_full_valid_config(self):
        """Test full configuration with all fields."""
        config = KeyMetricConfig(
            metric_key="customers",
            importance=MetricImportance.NOW,
            category=MetricSourceCategory.USER,
            display_order=1,
            notes="Track customer growth closely",
        )
        assert config.metric_key == "customers"
        assert config.importance == MetricImportance.NOW
        assert config.notes == "Track customer growth closely"

    def test_metric_key_max_length(self):
        """Test metric_key max length validation."""
        with pytest.raises(ValidationError):
            KeyMetricConfig(metric_key="a" * 51)

    def test_notes_max_length(self):
        """Test notes max length validation."""
        with pytest.raises(ValidationError):
            KeyMetricConfig(metric_key="test", notes="a" * 501)

    def test_display_order_non_negative(self):
        """Test display_order must be non-negative."""
        with pytest.raises(ValidationError):
            KeyMetricConfig(metric_key="test", display_order=-1)


class TestKeyMetricDisplayModel:
    """Tests for KeyMetricDisplay Pydantic model."""

    def test_minimal_valid_display(self):
        """Test minimal valid display model."""
        display = KeyMetricDisplay(
            metric_key="revenue",
            name="Revenue",
            importance=MetricImportance.NOW,
            category=MetricSourceCategory.USER,
        )
        assert display.metric_key == "revenue"
        assert display.name == "Revenue"
        assert display.value is None
        assert display.trend == MetricTrendIndicator.UNKNOWN  # default

    def test_full_valid_display(self):
        """Test full display model with all fields."""
        now = datetime.now(UTC)
        display = KeyMetricDisplay(
            metric_key="customers",
            name="Customers",
            value=150,
            unit="count",
            trend=MetricTrendIndicator.UP,
            trend_change="+15%",
            importance=MetricImportance.NOW,
            category=MetricSourceCategory.USER,
            benchmark_value=100,
            percentile=75,
            notes="Growing fast",
            last_updated=now,
        )
        assert display.value == 150
        assert display.trend == MetricTrendIndicator.UP
        assert display.trend_change == "+15%"
        assert display.percentile == 75

    def test_string_value(self):
        """Test value can be string."""
        display = KeyMetricDisplay(
            metric_key="revenue",
            name="Revenue",
            value="$50K MRR",
            importance=MetricImportance.NOW,
            category=MetricSourceCategory.USER,
        )
        assert display.value == "$50K MRR"

    def test_percentile_bounds(self):
        """Test percentile must be 0-100."""
        with pytest.raises(ValidationError):
            KeyMetricDisplay(
                metric_key="test",
                name="Test",
                importance=MetricImportance.NOW,
                category=MetricSourceCategory.USER,
                percentile=101,
            )

        with pytest.raises(ValidationError):
            KeyMetricDisplay(
                metric_key="test",
                name="Test",
                importance=MetricImportance.NOW,
                category=MetricSourceCategory.USER,
                percentile=-1,
            )


class TestKeyMetricConfigUpdateModel:
    """Tests for KeyMetricConfigUpdate Pydantic model."""

    def test_valid_update(self):
        """Test valid config update with multiple metrics."""
        update = KeyMetricConfigUpdate(
            metrics=[
                KeyMetricConfig(metric_key="revenue", importance=MetricImportance.NOW),
                KeyMetricConfig(metric_key="customers", importance=MetricImportance.LATER),
            ]
        )
        assert len(update.metrics) == 2

    def test_empty_metrics_list(self):
        """Test empty metrics list is valid."""
        update = KeyMetricConfigUpdate(metrics=[])
        assert update.metrics == []

    def test_max_metrics_limit(self):
        """Test max metrics limit (20)."""
        with pytest.raises(ValidationError):
            KeyMetricConfigUpdate(
                metrics=[KeyMetricConfig(metric_key=f"metric_{i}") for i in range(21)]
            )


class TestKeyMetricsResponseModel:
    """Tests for KeyMetricsResponse Pydantic model."""

    def test_success_response(self):
        """Test successful response with metrics."""
        response = KeyMetricsResponse(
            success=True,
            metrics=[
                KeyMetricDisplay(
                    metric_key="revenue",
                    name="Revenue",
                    importance=MetricImportance.NOW,
                    category=MetricSourceCategory.USER,
                )
            ],
            now_count=1,
            later_count=0,
            monitor_count=0,
        )
        assert response.success is True
        assert len(response.metrics) == 1
        assert response.now_count == 1

    def test_error_response(self):
        """Test error response."""
        response = KeyMetricsResponse(
            success=False,
            error="Failed to load metrics",
        )
        assert response.success is False
        assert response.error == "Failed to load metrics"
        assert response.metrics == []

    def test_empty_metrics(self):
        """Test response with no metrics."""
        response = KeyMetricsResponse(success=True)
        assert response.metrics == []
        assert response.now_count == 0


class TestKeyMetricSuggestionModel:
    """Tests for KeyMetricSuggestion Pydantic model."""

    def test_valid_suggestion(self):
        """Test valid metric suggestion."""
        suggestion = KeyMetricSuggestion(
            metric_key="churn",
            name="Churn Rate",
            importance=MetricImportance.NOW,
            category=MetricSourceCategory.USER,
            reasoning="As a SaaS business, churn is critical to monitor",
        )
        assert suggestion.metric_key == "churn"
        assert suggestion.reasoning.startswith("As a SaaS")

    def test_reasoning_max_length(self):
        """Test reasoning max length validation."""
        with pytest.raises(ValidationError):
            KeyMetricSuggestion(
                metric_key="test",
                name="Test",
                importance=MetricImportance.NOW,
                category=MetricSourceCategory.USER,
                reasoning="a" * 301,
            )


class TestKeyMetricsSuggestResponseModel:
    """Tests for KeyMetricsSuggestResponse Pydantic model."""

    def test_success_response(self):
        """Test successful suggestion response."""
        response = KeyMetricsSuggestResponse(
            success=True,
            suggestions=[
                KeyMetricSuggestion(
                    metric_key="revenue",
                    name="Revenue",
                    importance=MetricImportance.NOW,
                    category=MetricSourceCategory.USER,
                    reasoning="Revenue is key for growth",
                )
            ],
        )
        assert response.success is True
        assert len(response.suggestions) == 1

    def test_error_response(self):
        """Test error suggestion response."""
        response = KeyMetricsSuggestResponse(
            success=False,
            error="Insufficient context for suggestions",
        )
        assert response.success is False
        assert response.error is not None
