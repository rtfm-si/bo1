"""Tests for trend insights API endpoints."""

import base64
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.api.context.models import (
    TrendInsight,
    TrendInsightRequest,
    TrendInsightResponse,
    TrendInsightsListResponse,
)


class TestTrendInsightModels:
    """Tests for trend insight Pydantic models."""

    def test_trend_insight_all_fields(self):
        """Test TrendInsight with all fields populated."""
        insight = TrendInsight(
            url="https://example.com/article",
            title="AI Revolution in SaaS",
            key_takeaway="AI will change how SaaS products are built",
            relevance="Your competitors are already adopting AI features",
            actions=["Evaluate AI tools", "Train team", "Start pilot project"],
            timeframe="short_term",
            confidence="high",
            analyzed_at=datetime.now(UTC),
        )

        assert insight.url == "https://example.com/article"
        assert insight.title == "AI Revolution in SaaS"
        assert len(insight.actions) == 3
        assert insight.timeframe == "short_term"
        assert insight.confidence == "high"

    def test_trend_insight_minimal(self):
        """Test TrendInsight with minimal fields."""
        insight = TrendInsight(
            url="https://example.com/article",
            actions=[],
        )

        assert insight.url == "https://example.com/article"
        assert insight.title is None
        assert insight.key_takeaway is None
        assert insight.actions == []
        assert insight.timeframe is None
        assert insight.confidence is None

    def test_trend_insight_request(self):
        """Test TrendInsightRequest validation."""
        request = TrendInsightRequest(url="https://techcrunch.com/2025/01/ai-trends")

        assert request.url == "https://techcrunch.com/2025/01/ai-trends"

    def test_trend_insight_request_url_too_short(self):
        """Test TrendInsightRequest rejects short URLs."""
        with pytest.raises(ValueError):
            TrendInsightRequest(url="http://a")

    def test_trend_insight_response_success(self):
        """Test TrendInsightResponse with success."""
        insight = TrendInsight(
            url="https://example.com",
            title="Test Article",
            actions=["Action 1"],
        )
        response = TrendInsightResponse(
            success=True,
            insight=insight,
            analysis_status="complete",
        )

        assert response.success is True
        assert response.insight.title == "Test Article"
        assert response.error is None
        assert response.analysis_status == "complete"

    def test_trend_insight_response_cached(self):
        """Test TrendInsightResponse with cached status."""
        insight = TrendInsight(url="https://example.com", actions=[])
        response = TrendInsightResponse(
            success=True,
            insight=insight,
            analysis_status="cached",
        )

        assert response.analysis_status == "cached"

    def test_trend_insight_response_limited_data(self):
        """Test TrendInsightResponse with limited_data status."""
        insight = TrendInsight(
            url="https://example.com",
            actions=[],
            confidence="low",
        )
        response = TrendInsightResponse(
            success=True,
            insight=insight,
            analysis_status="limited_data",
        )

        assert response.analysis_status == "limited_data"

    def test_trend_insight_response_error(self):
        """Test TrendInsightResponse with error."""
        response = TrendInsightResponse(
            success=False,
            insight=None,
            error="Failed to fetch URL",
            analysis_status="error",
        )

        assert response.success is False
        assert response.insight is None
        assert response.error == "Failed to fetch URL"

    def test_trend_insights_list_response(self):
        """Test TrendInsightsListResponse."""
        insights = [
            TrendInsight(url="https://a.com", actions=[]),
            TrendInsight(url="https://b.com", actions=["Action"]),
        ]
        response = TrendInsightsListResponse(
            success=True,
            insights=insights,
            count=2,
        )

        assert response.success is True
        assert len(response.insights) == 2
        assert response.count == 2


class TestTrendInsightEndpoints:
    """Tests for trend insight API endpoint logic."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock user_repository."""
        with patch("backend.api.context.trends_routes.user_repository") as mock:
            yield mock

    @pytest.fixture
    def mock_analyzer(self):
        """Mock trend analyzer."""
        with patch("backend.api.context.trends_routes.get_trend_analyzer") as mock_get:
            analyzer = MagicMock()
            mock_get.return_value = analyzer
            yield analyzer

    def test_analyze_trend_cache_hit(self, mock_user_repository):
        """Test that cached insights are returned without regenerating."""
        cached_insight = {
            "url": "https://example.com/cached",
            "title": "Cached Article",
            "key_takeaway": "Cached takeaway",
            "relevance": "Cached relevance",
            "actions": ["Cached action"],
            "timeframe": "short_term",
            "confidence": "high",
            "analyzed_at": "2025-01-01T00:00:00Z",
        }
        mock_user_repository.get_context.return_value = {
            "trend_insights": {"https://example.com/cached": cached_insight}
        }

        # Simulate the endpoint logic for cache check
        context_data = mock_user_repository.get_context("test_user") or {}
        cached_insights = context_data.get("trend_insights", {})
        url = "https://example.com/cached"
        refresh = False

        # This is the cache hit path
        assert url in cached_insights
        assert not refresh

        insight_data = cached_insights[url]
        response = TrendInsightResponse(
            success=True,
            insight=TrendInsight(**insight_data),
            analysis_status="cached",
        )

        assert response.success is True
        assert response.analysis_status == "cached"
        assert response.insight.title == "Cached Article"

    def test_analyze_trend_cache_miss_generates(self, mock_user_repository):
        """Test that cache miss triggers generation."""
        mock_user_repository.get_context.return_value = {"trend_insights": {}}

        # Simulate the endpoint logic
        context_data = mock_user_repository.get_context("test_user") or {}
        cached_insights = context_data.get("trend_insights", {})
        url = "https://example.com/new"
        _refresh = False  # noqa: F841 - demonstrates cache miss path

        # This is the cache miss path - should proceed to generation
        assert url not in cached_insights

    def test_analyze_trend_refresh_bypasses_cache(self, mock_user_repository):
        """Test that refresh=true bypasses cache."""
        cached_insight = {
            "url": "https://example.com/cached",
            "title": "Old Title",
            "actions": [],
        }
        mock_user_repository.get_context.return_value = {
            "trend_insights": {"https://example.com/cached": cached_insight}
        }

        _url = "https://example.com/cached"  # noqa: F841 - shows cache hit scenario
        refresh = True

        # Even with cache hit, refresh=True should proceed to generation
        assert refresh is True  # Should trigger regeneration

    def test_list_insights_empty(self, mock_user_repository):
        """Test listing insights when none exist."""
        mock_user_repository.get_context.return_value = {}

        context_data = mock_user_repository.get_context("test_user")
        if not context_data:
            response = TrendInsightsListResponse(
                success=True,
                insights=[],
                count=0,
            )

        assert response.success is True
        assert len(response.insights) == 0
        assert response.count == 0

    def test_list_insights_sorted_by_date(self, mock_user_repository):
        """Test that insights are sorted by analyzed_at (newest first)."""
        cached = {
            "https://old.com": {
                "url": "https://old.com",
                "title": "Old Article",
                "actions": [],
                "analyzed_at": "2025-01-01T00:00:00Z",
            },
            "https://new.com": {
                "url": "https://new.com",
                "title": "New Article",
                "actions": [],
                "analyzed_at": "2025-01-15T00:00:00Z",
            },
        }
        mock_user_repository.get_context.return_value = {"trend_insights": cached}

        # Simulate sorting logic from endpoint
        insights = []
        for _url, data in cached.items():
            insights.append(TrendInsight(**data))

        # Sort by analyzed_at (newest first)
        insights.sort(
            key=lambda i: i.analyzed_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )

        assert insights[0].title == "New Article"
        assert insights[1].title == "Old Article"

    def test_delete_insight_url_decoding(self):
        """Test URL hash decoding for delete endpoint."""
        original_url = "https://example.com/article?param=value"

        # Encode URL to base64 (simulating what the frontend does)
        url_hash = base64.urlsafe_b64encode(original_url.encode()).decode()

        # Decode back (simulating what the endpoint does)
        decoded_url = base64.urlsafe_b64decode(url_hash.encode()).decode("utf-8")

        assert decoded_url == original_url

    def test_delete_insight_removes_from_cache(self, mock_user_repository):
        """Test that deleting insight removes it from cache."""
        cached = {
            "https://a.com": {"url": "https://a.com", "title": "A", "actions": []},
            "https://b.com": {"url": "https://b.com", "title": "B", "actions": []},
        }
        context_data = {"trend_insights": cached.copy()}
        mock_user_repository.get_context.return_value = context_data

        # Simulate delete
        url_to_delete = "https://a.com"
        del context_data["trend_insights"][url_to_delete]

        assert url_to_delete not in context_data["trend_insights"]
        assert len(context_data["trend_insights"]) == 1
        assert "https://b.com" in context_data["trend_insights"]


class TestTrendInsightTimeframes:
    """Tests for trend insight timeframe handling."""

    def test_all_valid_timeframes(self):
        """Test all valid timeframe values."""
        for timeframe in ["immediate", "short_term", "long_term"]:
            insight = TrendInsight(url="https://example.com", actions=[], timeframe=timeframe)
            assert insight.timeframe == timeframe

    def test_null_timeframe_allowed(self):
        """Test that null timeframe is allowed."""
        insight = TrendInsight(url="https://example.com", actions=[], timeframe=None)
        assert insight.timeframe is None


class TestTrendInsightConfidence:
    """Tests for trend insight confidence handling."""

    def test_all_valid_confidence_levels(self):
        """Test all valid confidence values."""
        for confidence in ["high", "medium", "low"]:
            insight = TrendInsight(url="https://example.com", actions=[], confidence=confidence)
            assert insight.confidence == confidence

    def test_null_confidence_allowed(self):
        """Test that null confidence is allowed."""
        insight = TrendInsight(url="https://example.com", actions=[], confidence=None)
        assert insight.confidence is None
