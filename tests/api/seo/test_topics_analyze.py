"""Tests for SEO topics analyze endpoint.

Validates:
- Request validation (empty input, max items)
- Response model structure
- TopicSuggestion fields
"""

import pytest

from backend.api.seo.routes import (
    AnalyzeTopicsRequest,
    AnalyzeTopicsResponse,
    TopicSuggestion,
)


@pytest.mark.unit
class TestAnalyzeTopicsRequest:
    """Test AnalyzeTopicsRequest validation."""

    def test_valid_single_word(self):
        """Single word is valid."""
        req = AnalyzeTopicsRequest(words=["marketing"])
        assert len(req.words) == 1
        assert req.words[0] == "marketing"

    def test_valid_multiple_words(self):
        """Multiple words up to 10 is valid."""
        words = [f"word{i}" for i in range(10)]
        req = AnalyzeTopicsRequest(words=words)
        assert len(req.words) == 10

    def test_empty_list_invalid(self):
        """Empty word list should be rejected."""
        with pytest.raises(ValueError):
            AnalyzeTopicsRequest(words=[])

    def test_too_many_words_invalid(self):
        """More than 10 words should be rejected."""
        words = [f"word{i}" for i in range(11)]
        with pytest.raises(ValueError):
            AnalyzeTopicsRequest(words=words)


@pytest.mark.unit
class TestTopicSuggestion:
    """Test TopicSuggestion model."""

    def test_valid_suggestion(self):
        """Valid suggestion with all fields."""
        suggestion = TopicSuggestion(
            keyword="content marketing strategy",
            seo_potential="high",
            trend_status="rising",
            related_keywords=["marketing", "content strategy", "SEO"],
            description="Guide to building an effective content marketing strategy",
        )
        assert suggestion.keyword == "content marketing strategy"
        assert suggestion.seo_potential == "high"
        assert suggestion.trend_status == "rising"
        assert len(suggestion.related_keywords) == 3
        assert suggestion.description.startswith("Guide")

    def test_empty_related_keywords(self):
        """Related keywords can be empty."""
        suggestion = TopicSuggestion(
            keyword="test topic",
            seo_potential="medium",
            trend_status="stable",
            related_keywords=[],
            description="Test description",
        )
        assert len(suggestion.related_keywords) == 0

    def test_seo_potential_values(self):
        """SEO potential accepts expected values."""
        for potential in ["high", "medium", "low"]:
            suggestion = TopicSuggestion(
                keyword="test",
                seo_potential=potential,
                trend_status="stable",
                related_keywords=[],
                description="Test",
            )
            assert suggestion.seo_potential == potential

    def test_trend_status_values(self):
        """Trend status accepts expected values."""
        for status in ["rising", "stable", "declining"]:
            suggestion = TopicSuggestion(
                keyword="test",
                seo_potential="medium",
                trend_status=status,
                related_keywords=[],
                description="Test",
            )
            assert suggestion.trend_status == status


@pytest.mark.unit
class TestAnalyzeTopicsResponse:
    """Test AnalyzeTopicsResponse model."""

    def test_empty_response(self):
        """Empty response is valid."""
        resp = AnalyzeTopicsResponse(
            suggestions=[],
            analyzed_words=["test"],
        )
        assert len(resp.suggestions) == 0
        assert len(resp.analyzed_words) == 1

    def test_response_with_suggestions(self):
        """Response with suggestions is valid."""
        suggestion = TopicSuggestion(
            keyword="AI automation",
            seo_potential="high",
            trend_status="rising",
            related_keywords=["automation", "AI tools"],
            description="How AI is transforming business automation",
        )
        resp = AnalyzeTopicsResponse(
            suggestions=[suggestion],
            analyzed_words=["AI", "automation"],
        )
        assert len(resp.suggestions) == 1
        assert len(resp.analyzed_words) == 2
        assert resp.suggestions[0].keyword == "AI automation"

    def test_multiple_suggestions(self):
        """Response can have multiple suggestions."""
        suggestions = [
            TopicSuggestion(
                keyword=f"topic {i}",
                seo_potential="medium",
                trend_status="stable",
                related_keywords=[],
                description=f"Description {i}",
            )
            for i in range(5)
        ]
        resp = AnalyzeTopicsResponse(
            suggestions=suggestions,
            analyzed_words=["test"],
        )
        assert len(resp.suggestions) == 5


@pytest.mark.unit
class TestWordProcessing:
    """Test word processing logic used in the endpoint."""

    def test_strip_whitespace(self):
        """Words should have whitespace stripped."""
        raw_words = ["  marketing  ", "content ", " SEO"]
        processed = [w.strip() for w in raw_words if w.strip()]
        assert processed == ["marketing", "content", "SEO"]

    def test_filter_empty_strings(self):
        """Empty strings should be filtered out."""
        raw_words = ["marketing", "", "  ", "SEO"]
        processed = [w.strip() for w in raw_words if w.strip()]
        assert processed == ["marketing", "SEO"]

    def test_preserve_order(self):
        """Word order should be preserved."""
        raw_words = ["first", "second", "third"]
        processed = [w.strip() for w in raw_words if w.strip()]
        assert processed == ["first", "second", "third"]


@pytest.mark.unit
class TestTopicSuggestionValidation:
    """Test TopicSuggestion validation fields."""

    def test_default_validation_status(self):
        """Default validation status is unvalidated."""
        suggestion = TopicSuggestion(
            keyword="test topic",
            seo_potential="medium",
            trend_status="stable",
            related_keywords=[],
            description="Test description",
        )
        assert suggestion.validation_status == "unvalidated"
        assert suggestion.competitor_presence == "unknown"
        assert suggestion.search_volume_indicator == "unknown"
        assert suggestion.validation_sources == []

    def test_validated_suggestion(self):
        """Validated suggestion with all fields."""
        suggestion = TopicSuggestion(
            keyword="content marketing strategy",
            seo_potential="high",
            trend_status="rising",
            related_keywords=["marketing", "content"],
            description="Guide to content marketing",
            validation_status="validated",
            competitor_presence="medium",
            search_volume_indicator="high",
            validation_sources=["example.com - Source 1", "test.com - Source 2"],
        )
        assert suggestion.validation_status == "validated"
        assert suggestion.competitor_presence == "medium"
        assert suggestion.search_volume_indicator == "high"
        assert len(suggestion.validation_sources) == 2

    def test_validation_status_values(self):
        """Validation status accepts expected values."""
        for status in ["validated", "unvalidated"]:
            suggestion = TopicSuggestion(
                keyword="test",
                seo_potential="medium",
                trend_status="stable",
                related_keywords=[],
                description="Test",
                validation_status=status,
            )
            assert suggestion.validation_status == status

    def test_competitor_presence_values(self):
        """Competitor presence accepts expected values."""
        for presence in ["high", "medium", "low", "unknown"]:
            suggestion = TopicSuggestion(
                keyword="test",
                seo_potential="medium",
                trend_status="stable",
                related_keywords=[],
                description="Test",
                competitor_presence=presence,
            )
            assert suggestion.competitor_presence == presence

    def test_search_volume_indicator_values(self):
        """Search volume indicator accepts expected values."""
        for volume in ["high", "medium", "low", "unknown"]:
            suggestion = TopicSuggestion(
                keyword="test",
                seo_potential="medium",
                trend_status="stable",
                related_keywords=[],
                description="Test",
                search_volume_indicator=volume,
            )
            assert suggestion.search_volume_indicator == volume


@pytest.mark.unit
class TestAnalyzeTopicsRequestSkipValidation:
    """Test AnalyzeTopicsRequest skip_validation field."""

    def test_default_skip_validation_false(self):
        """Skip validation defaults to False."""
        req = AnalyzeTopicsRequest(words=["marketing"])
        assert req.skip_validation is False

    def test_skip_validation_true(self):
        """Skip validation can be set to True."""
        req = AnalyzeTopicsRequest(words=["marketing"], skip_validation=True)
        assert req.skip_validation is True

    def test_skip_validation_false_explicit(self):
        """Skip validation can be explicitly set to False."""
        req = AnalyzeTopicsRequest(words=["marketing"], skip_validation=False)
        assert req.skip_validation is False
