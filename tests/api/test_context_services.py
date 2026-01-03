"""Tests for context services - get_metrics_from_insights and auto_save_competitors.

Tests the insight-to-metric mapping utility function and competitor enrichment persistence.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from backend.api.context.models import DetectedCompetitor, RelevanceFlags
from backend.api.context.services import (
    CATEGORY_TO_FIELD_MAPPING,
    DEFAULT_CONFIDENCE_THRESHOLD,
    MAX_INSIGHT_AGE_DAYS,
    auto_save_competitors,
    get_metrics_from_insights,
)


class TestGetMetricsFromInsights:
    """Tests for get_metrics_from_insights function."""

    def test_returns_empty_for_no_clarifications(self):
        """Test returns empty list when no clarifications provided."""
        result = get_metrics_from_insights({})
        assert result == []

    def test_returns_empty_for_none_clarifications(self):
        """Test returns empty list when clarifications is None-like."""
        result = get_metrics_from_insights(None)  # type: ignore
        assert result == []

    def test_extracts_revenue_suggestion(self):
        """Test extracting revenue metric from clarification."""
        clarifications = {
            "What's your MRR?": {
                "answer": "About $50,000",
                "category": "revenue",
                "confidence_score": 0.85,
                "metric": {
                    "value": 50000,
                    "unit": "USD",
                    "metric_type": "MRR",
                    "raw_text": "$50,000",
                },
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 1
        assert result[0]["field"] == "revenue"
        assert result[0]["suggested_value"] == "$50,000"
        assert result[0]["confidence"] == 0.85
        assert result[0]["source_question"] == "What's your MRR?"

    def test_extracts_customers_suggestion(self):
        """Test extracting customers metric from clarification."""
        clarifications = {
            "How many customers?": {
                "answer": "We have 150 paying customers",
                "category": "customers",
                "confidence_score": 0.9,
                "metric": {"value": 150, "unit": "count", "raw_text": "150"},
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 1
        assert result[0]["field"] == "customers"
        assert result[0]["suggested_value"] == "150"

    def test_extracts_growth_rate_suggestion(self):
        """Test extracting growth_rate metric from clarification."""
        clarifications = {
            "What's your growth rate?": {
                "answer": "15% MoM",
                "category": "growth",
                "confidence_score": 0.75,
                "metric": {"value": 15, "unit": "%", "raw_text": "15%"},
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 1
        assert result[0]["field"] == "growth_rate"
        assert result[0]["suggested_value"] == "15%"

    def test_extracts_team_size_suggestion(self):
        """Test extracting team_size metric from clarification."""
        clarifications = {
            "How big is your team?": {
                "answer": "12 people",
                "category": "team",
                "confidence_score": 0.8,
                "metric": {"value": 12, "unit": "people", "raw_text": "12"},
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 1
        assert result[0]["field"] == "team_size"
        assert result[0]["suggested_value"] == "12"

    def test_filters_low_confidence(self):
        """Test that low confidence insights are filtered out."""
        clarifications = {
            "What's your revenue?": {
                "answer": "Maybe $10K?",
                "category": "revenue",
                "confidence_score": 0.4,  # Below threshold
                "metric": {"value": 10000, "unit": "USD"},
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 0

    def test_custom_confidence_threshold(self):
        """Test using a custom confidence threshold."""
        clarifications = {
            "What's your revenue?": {
                "answer": "About $10K",
                "category": "revenue",
                "confidence_score": 0.5,  # Would pass 0.4 threshold
                "metric": {"value": 10000, "unit": "USD", "raw_text": "$10K"},
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        # Should be filtered with default threshold
        result = get_metrics_from_insights(clarifications)
        assert len(result) == 0

        # Should pass with lower threshold
        result = get_metrics_from_insights(clarifications, confidence_threshold=0.4)
        assert len(result) == 1

    def test_filters_old_insights(self):
        """Test that insights older than 90 days are filtered out."""
        old_date = datetime.now(UTC) - timedelta(days=100)

        clarifications = {
            "What's your revenue?": {
                "answer": "About $50K",
                "category": "revenue",
                "confidence_score": 0.9,
                "metric": {"value": 50000, "unit": "USD", "raw_text": "$50K"},
                "answered_at": old_date.isoformat(),
            }
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 0

    def test_keeps_recent_insights(self):
        """Test that insights within 90 days are kept."""
        recent_date = datetime.now(UTC) - timedelta(days=30)

        clarifications = {
            "What's your revenue?": {
                "answer": "About $50K",
                "category": "revenue",
                "confidence_score": 0.9,
                "metric": {"value": 50000, "unit": "USD", "raw_text": "$50K"},
                "answered_at": recent_date.isoformat(),
            }
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 1

    def test_skips_non_mappable_categories(self):
        """Test that categories not in mapping are skipped."""
        clarifications = {
            "What's your product?": {
                "answer": "A SaaS tool",
                "category": "product",  # Not in CATEGORY_TO_FIELD_MAPPING
                "confidence_score": 0.9,
                "metric": {"raw_text": "SaaS tool"},
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 0

    def test_skips_entries_without_metric(self):
        """Test that entries without metric data are skipped."""
        clarifications = {
            "What's your revenue?": {
                "answer": "About $50K",
                "category": "revenue",
                "confidence_score": 0.9,
                # No metric field
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 0

    def test_skips_matching_current_values(self):
        """Test that suggestions matching current value are skipped."""
        clarifications = {
            "What's your revenue?": {
                "answer": "About $50K",
                "category": "revenue",
                "confidence_score": 0.9,
                "metric": {"value": 50000, "unit": "USD", "raw_text": "$50K"},
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        existing_context = {"revenue": "$50K"}

        result = get_metrics_from_insights(clarifications, existing_context)

        assert len(result) == 0

    def test_includes_current_value_in_suggestion(self):
        """Test that current value is included in suggestion."""
        clarifications = {
            "What's your revenue?": {
                "answer": "Now $60K",
                "category": "revenue",
                "confidence_score": 0.9,
                "metric": {"value": 60000, "unit": "USD", "raw_text": "$60K"},
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        existing_context = {"revenue": "$50K"}

        result = get_metrics_from_insights(clarifications, existing_context)

        assert len(result) == 1
        assert result[0]["current_value"] == "$50K"
        assert result[0]["suggested_value"] == "$60K"

    def test_deduplicates_by_field_highest_confidence(self):
        """Test that multiple insights for same field keep highest confidence."""
        clarifications = {
            "What's your monthly revenue?": {
                "answer": "About $50K",
                "category": "revenue",
                "confidence_score": 0.8,
                "metric": {"value": 50000, "unit": "USD", "raw_text": "$50K"},
                "answered_at": datetime.now(UTC).isoformat(),
            },
            "What's your MRR?": {
                "answer": "Around $55K",
                "category": "revenue",
                "confidence_score": 0.95,  # Higher confidence
                "metric": {"value": 55000, "unit": "USD", "raw_text": "$55K"},
                "answered_at": datetime.now(UTC).isoformat(),
            },
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 1
        assert result[0]["suggested_value"] == "$55K"  # Higher confidence wins
        assert result[0]["confidence"] == 0.95

    def test_sorts_by_confidence_descending(self):
        """Test that results are sorted by confidence (highest first)."""
        clarifications = {
            "What's your revenue?": {
                "answer": "About $50K",
                "category": "revenue",
                "confidence_score": 0.7,
                "metric": {"value": 50000, "unit": "USD", "raw_text": "$50K"},
                "answered_at": datetime.now(UTC).isoformat(),
            },
            "How many customers?": {
                "answer": "150 customers",
                "category": "customers",
                "confidence_score": 0.9,
                "metric": {"value": 150, "unit": "count", "raw_text": "150"},
                "answered_at": datetime.now(UTC).isoformat(),
            },
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 2
        assert result[0]["field"] == "customers"  # Higher confidence first
        assert result[1]["field"] == "revenue"

    def test_handles_legacy_string_entries(self):
        """Test that legacy string entries (not dicts) are skipped."""
        clarifications = {
            "What's your revenue?": "About $50K",  # Legacy format
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 0

    def test_formats_numeric_value_with_usd_unit(self):
        """Test that numeric USD values are formatted correctly."""
        clarifications = {
            "What's your revenue?": {
                "answer": "About 50000",
                "category": "revenue",
                "confidence_score": 0.9,
                "metric": {"value": 50000, "unit": "USD"},  # No raw_text
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 1
        assert result[0]["suggested_value"] == "$50,000"

    def test_formats_numeric_value_with_percent_unit(self):
        """Test that numeric percentage values are formatted correctly."""
        clarifications = {
            "What's your growth rate?": {
                "answer": "About 15 percent",
                "category": "growth",
                "confidence_score": 0.9,
                "metric": {"value": 15, "unit": "%"},  # No raw_text
                "answered_at": datetime.now(UTC).isoformat(),
            }
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 1
        assert result[0]["suggested_value"] == "15%"

    def test_handles_datetime_object_answered_at(self):
        """Test handling datetime objects (not strings) for answered_at."""
        clarifications = {
            "What's your revenue?": {
                "answer": "About $50K",
                "category": "revenue",
                "confidence_score": 0.9,
                "metric": {"value": 50000, "unit": "USD", "raw_text": "$50K"},
                "answered_at": datetime.now(UTC),  # datetime object, not string
            }
        }

        result = get_metrics_from_insights(clarifications)

        assert len(result) == 1
        assert result[0]["answered_at"] is not None


class TestCategoryToFieldMapping:
    """Tests for the category to field mapping constants."""

    def test_revenue_maps_to_revenue(self):
        """Test revenue category maps to revenue field."""
        assert CATEGORY_TO_FIELD_MAPPING["revenue"] == "revenue"

    def test_customers_maps_to_customers(self):
        """Test customers category maps to customers field."""
        assert CATEGORY_TO_FIELD_MAPPING["customers"] == "customers"

    def test_growth_maps_to_growth_rate(self):
        """Test growth category maps to growth_rate field."""
        assert CATEGORY_TO_FIELD_MAPPING["growth"] == "growth_rate"

    def test_team_maps_to_team_size(self):
        """Test team category maps to team_size field."""
        assert CATEGORY_TO_FIELD_MAPPING["team"] == "team_size"

    def test_only_four_mappings_exist(self):
        """Test that exactly 4 mappings are defined."""
        assert len(CATEGORY_TO_FIELD_MAPPING) == 4


class TestConstants:
    """Tests for module constants."""

    def test_default_confidence_threshold(self):
        """Test default confidence threshold is 0.6."""
        assert DEFAULT_CONFIDENCE_THRESHOLD == 0.6

    def test_max_insight_age_days(self):
        """Test max insight age is 90 days."""
        assert MAX_INSIGHT_AGE_DAYS == 90


@pytest.mark.asyncio
class TestAutoSaveCompetitorsEnrichment:
    """Tests for auto_save_competitors preserving enrichment data."""

    @patch("bo1.state.repositories.user_repository")
    @patch("backend.api.context.services.get_single_value")
    async def test_preserves_relevance_score(self, mock_get_single_value, mock_user_repo):
        """Test that relevance_score is persisted when saving competitors."""
        mock_get_single_value.return_value = "pro"
        mock_user_repo.get_context.return_value = {"managed_competitors": []}
        mock_user_repo.save_context = MagicMock()

        competitor = DetectedCompetitor(
            name="Acme Corp",
            url="https://acme.com",
            description="A competitor",
            relevance_score=0.85,
            relevance_flags=None,
            relevance_warning=None,
        )

        result = await auto_save_competitors("user-123", [competitor], source="test")

        assert result == 1
        mock_user_repo.save_context.assert_called_once()
        saved_context = mock_user_repo.save_context.call_args[0][1]
        saved_competitor = saved_context["managed_competitors"][0]
        assert saved_competitor["relevance_score"] == 0.85

    @patch("bo1.state.repositories.user_repository")
    @patch("backend.api.context.services.get_single_value")
    async def test_preserves_relevance_flags(self, mock_get_single_value, mock_user_repo):
        """Test that relevance_flags dict is persisted when saving competitors."""
        mock_get_single_value.return_value = "pro"
        mock_user_repo.get_context.return_value = {"managed_competitors": []}
        mock_user_repo.save_context = MagicMock()

        flags = RelevanceFlags(similar_product=True, same_icp=True, same_market=False)
        competitor = DetectedCompetitor(
            name="Beta Inc",
            url="https://beta.io",
            description="Another competitor",
            relevance_score=0.66,
            relevance_flags=flags,
            relevance_warning=None,
        )

        result = await auto_save_competitors("user-456", [competitor], source="detect")

        assert result == 1
        mock_user_repo.save_context.assert_called_once()
        saved_context = mock_user_repo.save_context.call_args[0][1]
        saved_competitor = saved_context["managed_competitors"][0]
        assert saved_competitor["relevance_flags"] == {
            "similar_product": True,
            "same_icp": True,
            "same_market": False,
        }

    @patch("bo1.state.repositories.user_repository")
    @patch("backend.api.context.services.get_single_value")
    async def test_preserves_relevance_warning(self, mock_get_single_value, mock_user_repo):
        """Test that relevance_warning is persisted when saving competitors."""
        mock_get_single_value.return_value = "starter"
        mock_user_repo.get_context.return_value = {"managed_competitors": []}
        mock_user_repo.save_context = MagicMock()

        competitor = DetectedCompetitor(
            name="Gamma LLC",
            url="https://gamma.com",
            description="Low relevance competitor",
            relevance_score=0.33,
            relevance_flags=RelevanceFlags(similar_product=True, same_icp=False, same_market=False),
            relevance_warning="Only 1 of 3 relevance checks passed",
        )

        result = await auto_save_competitors("user-789", [competitor], source="detect")

        assert result == 1
        mock_user_repo.save_context.assert_called_once()
        saved_context = mock_user_repo.save_context.call_args[0][1]
        saved_competitor = saved_context["managed_competitors"][0]
        assert saved_competitor["relevance_warning"] == "Only 1 of 3 relevance checks passed"

    @patch("bo1.state.repositories.user_repository")
    @patch("backend.api.context.services.get_single_value")
    async def test_handles_none_enrichment_fields(self, mock_get_single_value, mock_user_repo):
        """Test that None enrichment fields are persisted correctly."""
        mock_get_single_value.return_value = "free"
        mock_user_repo.get_context.return_value = {"managed_competitors": []}
        mock_user_repo.save_context = MagicMock()

        # Competitor without any enrichment data (e.g., manually added)
        competitor = DetectedCompetitor(
            name="Delta Corp",
            url=None,
            description=None,
            relevance_score=None,
            relevance_flags=None,
            relevance_warning=None,
        )

        result = await auto_save_competitors("user-abc", [competitor], source="manual")

        assert result == 1
        mock_user_repo.save_context.assert_called_once()
        saved_context = mock_user_repo.save_context.call_args[0][1]
        saved_competitor = saved_context["managed_competitors"][0]
        assert saved_competitor["relevance_score"] is None
        assert saved_competitor["relevance_flags"] is None
        assert saved_competitor["relevance_warning"] is None

    @patch("bo1.state.repositories.user_repository")
    @patch("backend.api.context.services.get_single_value")
    async def test_preserves_all_enrichment_fields_together(
        self, mock_get_single_value, mock_user_repo
    ):
        """Test that all enrichment fields are preserved together."""
        mock_get_single_value.return_value = "pro"
        mock_user_repo.get_context.return_value = {"managed_competitors": []}
        mock_user_repo.save_context = MagicMock()

        flags = RelevanceFlags(similar_product=True, same_icp=True, same_market=True)
        competitor = DetectedCompetitor(
            name="Epsilon Tech",
            url="https://epsilon.tech",
            description="High relevance competitor",
            relevance_score=1.0,
            relevance_flags=flags,
            relevance_warning=None,
        )

        result = await auto_save_competitors("user-full", [competitor], source="detect")

        assert result == 1
        saved_context = mock_user_repo.save_context.call_args[0][1]
        saved_competitor = saved_context["managed_competitors"][0]

        # Verify all core fields
        assert saved_competitor["name"] == "Epsilon Tech"
        assert saved_competitor["url"] == "https://epsilon.tech"
        assert saved_competitor["notes"] == "High relevance competitor"
        assert "added_at" in saved_competitor
        assert saved_competitor["source"] == "detect"

        # Verify all enrichment fields
        assert saved_competitor["relevance_score"] == 1.0
        assert saved_competitor["relevance_flags"] == {
            "similar_product": True,
            "same_icp": True,
            "same_market": True,
        }
        assert saved_competitor["relevance_warning"] is None
