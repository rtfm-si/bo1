"""Unit tests for insight-to-metric mapping.

Tests CATEGORY_TO_METRIC_KEY mapping and insight_to_business_metric helper.
"""

from datetime import UTC, datetime

from backend.api.context.models import (
    ClarificationStorageEntry,
    InsightCategory,
    InsightMetricResponse,
)
from backend.api.context.services import (
    CATEGORY_TO_METRIC_KEY,
    DEFAULT_CONFIDENCE_THRESHOLD,
    METRIC_DISPLAY_NAMES,
    insight_to_business_metric,
)
from backend.services.insight_parser import InsightCategory as ParserInsightCategory


class TestCategoryToMetricKeyMapping:
    """Test CATEGORY_TO_METRIC_KEY covers all InsightCategory values."""

    def test_all_categories_mapped(self):
        """Every InsightCategory has a mapping."""
        for cat in ParserInsightCategory:
            assert cat.value in CATEGORY_TO_METRIC_KEY, f"Missing mapping for {cat.value}"

    def test_uncategorized_maps_to_none(self):
        """uncategorized maps to None (skip)."""
        assert CATEGORY_TO_METRIC_KEY["uncategorized"] is None

    def test_core_categories_have_metric_keys(self):
        """Core business categories have metric keys."""
        assert CATEGORY_TO_METRIC_KEY["revenue"] == "mrr"
        assert CATEGORY_TO_METRIC_KEY["growth"] == "growth_rate"
        assert CATEGORY_TO_METRIC_KEY["customers"] == "customer_count"
        assert CATEGORY_TO_METRIC_KEY["team"] == "team_size"
        assert CATEGORY_TO_METRIC_KEY["costs"] == "burn_rate"
        assert CATEGORY_TO_METRIC_KEY["funding"] == "runway"

    def test_extended_categories_mapped(self):
        """Extended categories have mappings."""
        assert CATEGORY_TO_METRIC_KEY["operations"] == "ops_metric"
        assert CATEGORY_TO_METRIC_KEY["market"] == "market_size"
        assert CATEGORY_TO_METRIC_KEY["competition"] == "competitive_metric"
        assert CATEGORY_TO_METRIC_KEY["product"] == "product_metric"


class TestInsightToBusinessMetric:
    """Test insight_to_business_metric conversion function."""

    def test_valid_revenue_insight(self):
        """Revenue insight with metric converts correctly."""
        entry = ClarificationStorageEntry(
            answer="Our MRR is $25,000",
            category=InsightCategory.REVENUE,
            confidence_score=0.9,
            metric=InsightMetricResponse(
                value=25000,
                unit="USD",
                metric_type="MRR",
            ),
            parsed_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
        )

        result = insight_to_business_metric(entry, "What is your MRR?")

        assert result is not None
        assert result["metric_key"] == "mrr"
        assert result["value"] == 25000.0
        assert result["value_unit"] == "USD"
        assert result["source"] == "clarification"
        assert result["is_predefined"] is False
        assert result["source_question"] == "What is your MRR?"
        assert result["confidence"] == 0.9

    def test_valid_team_insight(self):
        """Team insight converts correctly."""
        entry = ClarificationStorageEntry(
            answer="We have 10 people",
            category=InsightCategory.TEAM,
            confidence_score=0.85,
            metric=InsightMetricResponse(value=10, unit="count"),
            answered_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
        )

        result = insight_to_business_metric(entry, "Team size?")

        assert result is not None
        assert result["metric_key"] == "team_size"
        assert result["value"] == 10.0
        assert result["name"] == "Team Size"

    def test_low_confidence_returns_none(self):
        """Below-threshold confidence returns None."""
        entry = ClarificationStorageEntry(
            answer="Maybe $5K?",
            category=InsightCategory.REVENUE,
            confidence_score=0.4,  # Below 0.6 threshold
            metric=InsightMetricResponse(value=5000, unit="USD"),
        )

        result = insight_to_business_metric(entry, "Revenue?")
        assert result is None

    def test_no_metric_returns_none(self):
        """Missing metric data returns None."""
        entry = ClarificationStorageEntry(
            answer="We compete with Acme",
            category=InsightCategory.COMPETITION,
            confidence_score=0.8,
            metric=None,
        )

        result = insight_to_business_metric(entry, "Competitors?")
        assert result is None

    def test_metric_without_value_returns_none(self):
        """Metric without value returns None."""
        entry = ClarificationStorageEntry(
            answer="Revenue is good",
            category=InsightCategory.REVENUE,
            confidence_score=0.8,
            metric=InsightMetricResponse(unit="USD", metric_type="MRR"),  # No value
        )

        result = insight_to_business_metric(entry, "Revenue?")
        assert result is None

    def test_uncategorized_returns_none(self):
        """Uncategorized insight returns None."""
        entry = ClarificationStorageEntry(
            answer="The weather is nice",
            category=InsightCategory.UNCATEGORIZED,
            confidence_score=0.9,
            metric=InsightMetricResponse(value=42),
        )

        result = insight_to_business_metric(entry, "What?")
        assert result is None

    def test_unknown_category_returns_none(self):
        """Unknown category returns None."""
        entry = ClarificationStorageEntry(
            answer="Some text",
            category=None,
            confidence_score=0.9,
            metric=InsightMetricResponse(value=100),
        )

        result = insight_to_business_metric(entry, "Question?")
        assert result is None

    def test_uses_parsed_at_for_captured_at(self):
        """Uses parsed_at timestamp when available."""
        entry = ClarificationStorageEntry(
            answer="$50K MRR",
            category=InsightCategory.REVENUE,
            confidence_score=0.9,
            metric=InsightMetricResponse(value=50000, unit="USD"),
            parsed_at=datetime(2025, 1, 10, 8, 0, 0, tzinfo=UTC),
            answered_at=datetime(2025, 1, 10, 7, 0, 0, tzinfo=UTC),
        )

        result = insight_to_business_metric(entry, "MRR?")

        assert result is not None
        # Should use parsed_at, not answered_at
        assert result["captured_at"].hour == 8

    def test_falls_back_to_answered_at(self):
        """Falls back to answered_at when parsed_at missing."""
        entry = ClarificationStorageEntry(
            answer="$50K MRR",
            category=InsightCategory.REVENUE,
            confidence_score=0.9,
            metric=InsightMetricResponse(value=50000, unit="USD"),
            parsed_at=None,
            answered_at=datetime(2025, 1, 10, 14, 30, 0, tzinfo=UTC),
        )

        result = insight_to_business_metric(entry, "MRR?")

        assert result is not None
        assert result["captured_at"].hour == 14

    def test_display_name_from_mapping(self):
        """Uses display name from METRIC_DISPLAY_NAMES."""
        entry = ClarificationStorageEntry(
            answer="150 customers",
            category=InsightCategory.CUSTOMERS,
            confidence_score=0.8,
            metric=InsightMetricResponse(value=150, unit="count"),
        )

        result = insight_to_business_metric(entry, "Customer count?")

        assert result is not None
        # customer_count is in METRIC_DISPLAY_NAMES
        assert "name" in result

    def test_handles_float_value(self):
        """Handles float value correctly."""
        entry = ClarificationStorageEntry(
            answer="25000 dollars",
            category=InsightCategory.REVENUE,
            confidence_score=0.8,
            metric=InsightMetricResponse(value=25000.0, unit="USD"),
        )

        result = insight_to_business_metric(entry, "Revenue?")

        assert result is not None
        assert result["value"] == 25000.0


class TestDefaultConfidenceThreshold:
    """Test DEFAULT_CONFIDENCE_THRESHOLD constant."""

    def test_threshold_is_reasonable(self):
        """Threshold should be between 0.5 and 0.8."""
        assert 0.5 <= DEFAULT_CONFIDENCE_THRESHOLD <= 0.8
        assert DEFAULT_CONFIDENCE_THRESHOLD == 0.6


class TestMetricDisplayNames:
    """Test METRIC_DISPLAY_NAMES mapping."""

    def test_has_display_names_for_core_metrics(self):
        """Core metrics have human-readable names."""
        assert "revenue" in METRIC_DISPLAY_NAMES
        assert "customers" in METRIC_DISPLAY_NAMES
        assert "growth_rate" in METRIC_DISPLAY_NAMES
        assert "team_size" in METRIC_DISPLAY_NAMES

    def test_display_names_are_readable(self):
        """Display names are properly formatted."""
        for _key, name in METRIC_DISPLAY_NAMES.items():
            assert len(name) > 0
            # First letter should be uppercase
            assert name[0].isupper()
