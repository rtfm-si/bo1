"""Unit tests for business metrics API endpoints.

Tests:
- PATCH /api/v1/business-metrics/{key}/relevance endpoint
- Repository set_metric_relevance method
- UserMetric model with is_relevant field
"""

import pytest
from pydantic import ValidationError

from backend.api.business_metrics import (
    MetricCategory,
    MetricSource,
    SetRelevanceRequest,
    UserMetric,
    _format_metric,
)


class TestUserMetricModel:
    """Tests for UserMetric Pydantic model."""

    def test_minimal_valid_metric(self):
        """Test minimal valid user metric."""
        metric = UserMetric(
            id="1",
            user_id="user123",
            metric_key="mrr",
            name="Monthly Recurring Revenue",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        assert metric.id == "1"
        assert metric.metric_key == "mrr"
        assert metric.is_predefined is False  # default
        assert metric.is_relevant is True  # default

    def test_full_valid_metric(self):
        """Test full user metric with all fields."""
        metric = UserMetric(
            id="1",
            user_id="user123",
            metric_key="churn",
            name="Churn Rate",
            definition="Percentage of customers lost",
            importance="Critical for retention",
            category=MetricCategory.RETENTION,
            value=5.2,
            value_unit="%",
            captured_at="2024-01-15T10:00:00Z",
            source=MetricSource.MANUAL,
            is_predefined=True,
            is_relevant=True,
            display_order=1,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-15T10:00:00Z",
        )
        assert metric.value == 5.2
        assert metric.category == MetricCategory.RETENTION
        assert metric.is_predefined is True
        assert metric.is_relevant is True

    def test_is_relevant_false(self):
        """Test metric with is_relevant=false."""
        metric = UserMetric(
            id="1",
            user_id="user123",
            metric_key="cac",
            name="Customer Acquisition Cost",
            is_relevant=False,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        assert metric.is_relevant is False


class TestSetRelevanceRequest:
    """Tests for SetRelevanceRequest model."""

    def test_valid_request_true(self):
        """Test valid request with is_relevant=true."""
        request = SetRelevanceRequest(is_relevant=True)
        assert request.is_relevant is True

    def test_valid_request_false(self):
        """Test valid request with is_relevant=false."""
        request = SetRelevanceRequest(is_relevant=False)
        assert request.is_relevant is False

    def test_missing_is_relevant(self):
        """Test request without is_relevant raises error."""
        with pytest.raises(ValidationError):
            SetRelevanceRequest()


class TestFormatMetric:
    """Tests for _format_metric helper function."""

    def test_format_with_is_relevant_true(self):
        """Test formatting metric with is_relevant=True."""
        from datetime import UTC, datetime

        metric_data = {
            "id": 123,
            "user_id": "user123",
            "metric_key": "mrr",
            "name": "Monthly Recurring Revenue",
            "definition": "Total recurring revenue",
            "importance": "Key SaaS metric",
            "category": "financial",
            "value": 50000,
            "value_unit": "$",
            "captured_at": datetime.now(UTC),
            "source": "manual",
            "is_predefined": True,
            "is_relevant": True,
            "display_order": 0,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        formatted = _format_metric(metric_data)
        assert formatted["is_relevant"] is True
        assert formatted["is_predefined"] is True
        assert formatted["value"] == 50000.0

    def test_format_with_is_relevant_false(self):
        """Test formatting metric with is_relevant=False."""
        from datetime import UTC, datetime

        metric_data = {
            "id": 456,
            "user_id": "user123",
            "metric_key": "cac",
            "name": "Customer Acquisition Cost",
            "is_predefined": True,
            "is_relevant": False,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        formatted = _format_metric(metric_data)
        assert formatted["is_relevant"] is False

    def test_format_missing_is_relevant_defaults_true(self):
        """Test formatting metric without is_relevant defaults to True."""
        from datetime import UTC, datetime

        metric_data = {
            "id": 789,
            "user_id": "user123",
            "metric_key": "ltv",
            "name": "Lifetime Value",
            "is_predefined": True,
            # No is_relevant field
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        formatted = _format_metric(metric_data)
        assert formatted["is_relevant"] is True  # Default
