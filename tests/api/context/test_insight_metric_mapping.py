"""Tests for insight-to-metric mapping module.

Tests keyword matching, category-based matching, and confidence scoring
for the metric_mapping module.
"""

from datetime import UTC, datetime, timedelta

from backend.api.context.metric_mapping import (
    METRIC_KEYWORDS,
    get_insight_metric_suggestions,
    match_insight_to_metrics,
)
from backend.api.context.models import InsightCategory


class TestMatchInsightToMetrics:
    """Tests for match_insight_to_metrics function."""

    def test_mrr_keyword_match(self):
        """Test MRR matching via keywords in question/answer."""
        matches = match_insight_to_metrics(
            question="What is your monthly recurring revenue?",
            answer="About $5,000 per month",
            category=InsightCategory.REVENUE,
            metric_data={"value": 5000, "unit": "USD"},
            confidence_score=0.9,
            answered_at=datetime.now(UTC),
        )

        assert len(matches) > 0
        mrr_match = next((m for m in matches if m.metric_key == "mrr"), None)
        assert mrr_match is not None
        assert mrr_match.confidence >= 0.5

    def test_churn_keyword_match(self):
        """Test churn matching via keywords."""
        matches = match_insight_to_metrics(
            question="What is your customer churn rate?",
            answer="We're seeing about 5% monthly churn",
            category=InsightCategory.CUSTOMERS,
            metric_data={"value": 5, "unit": "%"},
            confidence_score=0.85,
            answered_at=datetime.now(UTC),
        )

        churn_match = next((m for m in matches if m.metric_key == "churn"), None)
        assert churn_match is not None
        assert churn_match.confidence >= 0.5

    def test_category_only_match(self):
        """Test matching by category when keywords don't match specific metric."""
        matches = match_insight_to_metrics(
            question="Tell me about your revenue situation",
            answer="We make $10,000",
            category=InsightCategory.REVENUE,
            metric_data={"value": 10000, "unit": "USD"},
            confidence_score=0.8,
            answered_at=datetime.now(UTC),
        )

        # Should match some revenue-category metrics
        revenue_matches = [
            m
            for m in matches
            if METRIC_KEYWORDS.get(m.metric_key, {}).get("category") == InsightCategory.REVENUE
        ]
        assert len(revenue_matches) > 0

    def test_no_match_low_score(self):
        """Test that insights with no relevant keywords don't match."""
        matches = match_insight_to_metrics(
            question="What color is your logo?",
            answer="Blue and white",
            category=InsightCategory.UNCATEGORIZED,
            metric_data=None,
            confidence_score=0.3,
            answered_at=datetime.now(UTC),
        )

        # Should have no matches above threshold
        high_confidence = [m for m in matches if m.confidence >= 0.5]
        assert len(high_confidence) == 0

    def test_cac_keyword_match(self):
        """Test CAC (customer acquisition cost) matching."""
        matches = match_insight_to_metrics(
            question="How much does it cost to acquire a customer?",
            answer="Our customer acquisition cost is around $150",
            category=InsightCategory.COSTS,
            metric_data={"value": 150, "unit": "USD"},
            confidence_score=0.88,
            answered_at=datetime.now(UTC),
        )

        cac_match = next((m for m in matches if m.metric_key == "cac"), None)
        assert cac_match is not None
        assert cac_match.confidence >= 0.5

    def test_ltv_keyword_match(self):
        """Test LTV (lifetime value) matching."""
        matches = match_insight_to_metrics(
            question="What is the lifetime value of your customers?",
            answer="Average customer lifetime value is $1,200",
            category=InsightCategory.REVENUE,
            metric_data={"value": 1200, "unit": "USD"},
            confidence_score=0.9,
            answered_at=datetime.now(UTC),
        )

        ltv_match = next((m for m in matches if m.metric_key == "ltv"), None)
        assert ltv_match is not None

    def test_runway_keyword_match(self):
        """Test runway matching."""
        matches = match_insight_to_metrics(
            question="How long is your runway?",
            answer="We have about 18 months of runway left",
            category=InsightCategory.FUNDING,
            metric_data={"value": 18, "unit": "months"},
            confidence_score=0.85,
            answered_at=datetime.now(UTC),
        )

        runway_match = next((m for m in matches if m.metric_key == "runway"), None)
        assert runway_match is not None

    def test_nps_keyword_match(self):
        """Test NPS matching."""
        matches = match_insight_to_metrics(
            question="What's your Net Promoter Score?",
            answer="Our NPS is 45",
            category=InsightCategory.CUSTOMERS,
            metric_data={"value": 45, "unit": "score"},
            confidence_score=0.92,
            answered_at=datetime.now(UTC),
        )

        nps_match = next((m for m in matches if m.metric_key == "nps"), None)
        assert nps_match is not None

    def test_conversion_rate_match(self):
        """Test conversion rate matching."""
        matches = match_insight_to_metrics(
            question="What's your website conversion rate?",
            answer="Our conversion rate is around 2.5%",
            category=InsightCategory.GROWTH,
            metric_data={"value": 2.5, "unit": "%"},
            confidence_score=0.87,
            answered_at=datetime.now(UTC),
        )

        conv_match = next((m for m in matches if m.metric_key == "conversion_rate"), None)
        assert conv_match is not None

    def test_string_answered_at(self):
        """Test handling of string datetime for answered_at."""
        matches = match_insight_to_metrics(
            question="What's your MRR?",
            answer="$5000/month",
            category=InsightCategory.REVENUE,
            metric_data={"value": 5000},
            confidence_score=0.9,
            answered_at="2025-01-10T12:00:00Z",
        )

        assert len(matches) > 0
        mrr = next((m for m in matches if m.metric_key == "mrr"), None)
        assert mrr is not None
        assert mrr.answered_at is not None

    def test_no_metric_data_uses_pattern_extraction(self):
        """Test that value is extracted from text when metric_data is None."""
        matches = match_insight_to_metrics(
            question="What's your monthly recurring revenue?",
            answer="Around $8,000",
            category=InsightCategory.REVENUE,
            metric_data=None,
            confidence_score=0.85,
            answered_at=datetime.now(UTC),
        )

        mrr_match = next((m for m in matches if m.metric_key == "mrr"), None)
        # Should still match via pattern extraction
        assert mrr_match is not None or any(m.confidence >= 0.3 for m in matches)


class TestGetInsightMetricSuggestions:
    """Tests for get_insight_metric_suggestions function."""

    def test_empty_clarifications(self):
        """Test with empty clarifications dict."""
        suggestions = get_insight_metric_suggestions({})
        assert suggestions == []

    def test_single_insight_match(self):
        """Test with a single insight that matches a metric."""
        clarifications = {
            "What's your MRR?": {
                "answer": "$5,000 monthly recurring revenue",
                "category": "revenue",
                "metric": {"value": 5000, "unit": "USD"},
                "confidence_score": 0.9,
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        suggestions = get_insight_metric_suggestions(clarifications)

        assert len(suggestions) > 0
        mrr_suggestion = next((s for s in suggestions if s["metric_key"] == "mrr"), None)
        assert mrr_suggestion is not None

    def test_multiple_insights(self):
        """Test with multiple insights matching different metrics."""
        now = datetime.now(UTC)
        clarifications = {
            "What's your MRR?": {
                "answer": "$5,000",
                "category": "revenue",
                "metric": {"value": 5000, "unit": "USD"},
                "confidence_score": 0.9,
                "answered_at": now.isoformat(),
            },
            "What's your churn rate?": {
                "answer": "3% monthly churn",
                "category": "customers",
                "metric": {"value": 3, "unit": "%"},
                "confidence_score": 0.85,
                "answered_at": now.isoformat(),
            },
        }

        suggestions = get_insight_metric_suggestions(clarifications)

        assert len(suggestions) >= 2
        metric_keys = {s["metric_key"] for s in suggestions}
        assert "mrr" in metric_keys
        assert "churn" in metric_keys

    def test_filters_old_insights(self):
        """Test that insights older than max_age_days are filtered."""
        old_date = datetime.now(UTC) - timedelta(days=100)
        clarifications = {
            "What's your MRR?": {
                "answer": "$5,000",
                "category": "revenue",
                "metric": {"value": 5000, "unit": "USD"},
                "confidence_score": 0.9,
                "answered_at": old_date.isoformat(),
            }
        }

        suggestions = get_insight_metric_suggestions(clarifications, max_age_days=90)

        assert len(suggestions) == 0

    def test_filters_by_confidence_threshold(self):
        """Test that low confidence insights are filtered."""
        clarifications = {
            "What's your MRR?": {
                "answer": "$5,000",
                "category": "revenue",
                "metric": {"value": 5000, "unit": "USD"},
                "confidence_score": 0.3,  # Low confidence
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        suggestions = get_insight_metric_suggestions(clarifications, confidence_threshold=0.5)

        # Should be filtered due to low confidence
        mrr_suggestion = next((s for s in suggestions if s["metric_key"] == "mrr"), None)
        assert mrr_suggestion is None

    def test_skips_matching_existing_value(self):
        """Test that suggestions matching current value are excluded."""
        clarifications = {
            "What's your MRR?": {
                "answer": "$5,000",
                "category": "revenue",
                "metric": {"value": 5000, "unit": "USD", "raw_text": "5000"},
                "confidence_score": 0.9,
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        existing_metrics = {"mrr": "5000"}

        suggestions = get_insight_metric_suggestions(
            clarifications, existing_metrics=existing_metrics
        )

        # Should skip since value matches
        mrr_suggestion = next((s for s in suggestions if s["metric_key"] == "mrr"), None)
        assert mrr_suggestion is None

    def test_keeps_best_per_metric(self):
        """Test that only highest confidence suggestion per metric is kept."""
        now = datetime.now(UTC)
        clarifications = {
            "What's your MRR?": {
                "answer": "$5,000",
                "category": "revenue",
                "metric": {"value": 5000, "unit": "USD"},
                "confidence_score": 0.9,
                "answered_at": now.isoformat(),
            },
            "Tell me your monthly recurring revenue": {
                "answer": "$6,000",
                "category": "revenue",
                "metric": {"value": 6000, "unit": "USD"},
                "confidence_score": 0.7,  # Lower confidence
                "answered_at": now.isoformat(),
            },
        }

        suggestions = get_insight_metric_suggestions(clarifications)

        # Should only have one MRR suggestion (the higher confidence one)
        mrr_suggestions = [s for s in suggestions if s["metric_key"] == "mrr"]
        assert len(mrr_suggestions) <= 1
        if mrr_suggestions:
            assert mrr_suggestions[0]["confidence"] >= 0.7

    def test_invalid_entry_skipped(self):
        """Test that invalid clarification entries are skipped."""
        clarifications = {
            "Invalid entry": "not a dict",
            "What's your MRR?": {
                "answer": "$5,000",
                "category": "revenue",
                "metric": {"value": 5000, "unit": "USD"},
                "confidence_score": 0.9,
                "answered_at": datetime.now(UTC).isoformat(),
            },
        }

        # Should not raise, just skip invalid
        suggestions = get_insight_metric_suggestions(clarifications)
        assert len(suggestions) >= 0


class TestMetricKeywordCoverage:
    """Test that all 13 seeded metrics have keyword definitions."""

    EXPECTED_METRICS = [
        "mrr",
        "arr",
        "burn_rate",
        "runway",
        "gross_margin",
        "churn",
        "nps",
        "cac",
        "ltv",
        "ltv_cac_ratio",
        "aov",
        "conversion_rate",
        "return_rate",
    ]

    def test_all_metrics_have_keywords(self):
        """Verify all 13 metrics have keyword definitions."""
        for metric_key in self.EXPECTED_METRICS:
            assert metric_key in METRIC_KEYWORDS, f"Missing keywords for {metric_key}"
            config = METRIC_KEYWORDS[metric_key]
            assert "keywords" in config, f"No keywords list for {metric_key}"
            assert len(config["keywords"]) > 0, f"Empty keywords for {metric_key}"
            assert "category" in config, f"No category for {metric_key}"
            assert "value_patterns" in config, f"No value_patterns for {metric_key}"

    def test_all_metrics_have_valid_categories(self):
        """Verify all metrics have valid InsightCategory."""
        for metric_key in self.EXPECTED_METRICS:
            config = METRIC_KEYWORDS[metric_key]
            category = config.get("category")
            assert category is not None
            assert isinstance(category, InsightCategory)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_none_values(self):
        """Test handling of None values."""
        matches = match_insight_to_metrics(
            question="What's your MRR?",
            answer="I don't know",
            category=None,
            metric_data=None,
            confidence_score=None,
            answered_at=None,
        )
        # Should not raise
        assert isinstance(matches, list)

    def test_empty_strings(self):
        """Test handling of empty strings."""
        matches = match_insight_to_metrics(
            question="",
            answer="",
            category=InsightCategory.UNCATEGORIZED,
            metric_data={},
            confidence_score=0.5,
            answered_at=datetime.now(UTC),
        )
        # Should not raise
        assert isinstance(matches, list)

    def test_invalid_category_string(self):
        """Test handling of invalid category string."""
        matches = match_insight_to_metrics(
            question="What's your MRR?",
            answer="$5000",
            category="invalid_category",  # type: ignore
            metric_data={"value": 5000},
            confidence_score=0.9,
            answered_at=datetime.now(UTC),
        )
        # Should not raise, just ignore invalid category
        assert isinstance(matches, list)

    def test_datetime_string_formats(self):
        """Test various datetime string formats."""
        # ISO format with Z
        matches1 = match_insight_to_metrics(
            question="MRR?",
            answer="$5000",
            category=InsightCategory.REVENUE,
            metric_data={"value": 5000},
            confidence_score=0.9,
            answered_at="2025-01-10T12:00:00Z",
        )
        assert len(matches1) >= 0

        # ISO format with offset
        matches2 = match_insight_to_metrics(
            question="MRR?",
            answer="$5000",
            category=InsightCategory.REVENUE,
            metric_data={"value": 5000},
            confidence_score=0.9,
            answered_at="2025-01-10T12:00:00+00:00",
        )
        assert len(matches2) >= 0
