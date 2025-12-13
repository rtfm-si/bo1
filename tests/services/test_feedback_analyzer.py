"""Unit tests for feedback analyzer service.

Tests sentiment and theme extraction using mocked Haiku responses.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.feedback_analyzer import (
    FeedbackAnalysis,
    FeedbackAnalyzer,
    Sentiment,
    analyze_feedback,
    get_feedback_analyzer,
)


class TestFeedbackAnalysis:
    """Tests for FeedbackAnalysis dataclass."""

    def test_to_dict(self):
        """Should serialize to dictionary correctly."""
        analysis = FeedbackAnalysis(
            sentiment=Sentiment.POSITIVE,
            sentiment_confidence=0.9,
            themes=["usability", "features"],
            analyzed_at="2025-12-13T10:00:00Z",
        )
        result = analysis.to_dict()

        assert result["sentiment"] == "positive"
        assert result["sentiment_confidence"] == 0.9
        assert result["themes"] == ["usability", "features"]
        assert result["analyzed_at"] == "2025-12-13T10:00:00Z"

    def test_from_dict(self):
        """Should deserialize from dictionary correctly."""
        data = {
            "sentiment": "negative",
            "sentiment_confidence": 0.85,
            "themes": ["reliability", "performance"],
            "analyzed_at": "2025-12-13T10:00:00Z",
        }
        analysis = FeedbackAnalysis.from_dict(data)

        assert analysis.sentiment == Sentiment.NEGATIVE
        assert analysis.sentiment_confidence == 0.85
        assert analysis.themes == ["reliability", "performance"]

    def test_from_dict_invalid_sentiment(self):
        """Should default to neutral for invalid sentiment."""
        data = {
            "sentiment": "invalid",
            "sentiment_confidence": 0.5,
            "themes": [],
        }
        analysis = FeedbackAnalysis.from_dict(data)
        assert analysis.sentiment == Sentiment.NEUTRAL


class TestFeedbackAnalyzer:
    """Tests for FeedbackAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return FeedbackAnalyzer()

    @pytest.mark.asyncio
    async def test_analyze_feedback_positive(self, analyzer):
        """Should detect positive sentiment."""
        mock_response = '{"sentiment": "positive", "sentiment_confidence": 0.9, "themes": ["features", "usability"], "summary": "Great new features"}'

        with patch.object(analyzer, "_get_client") as mock_client:
            mock_client.return_value.call = AsyncMock(return_value=(mock_response, {}))
            result = await analyzer.analyze_feedback(
                "Love the new features!",
                "The recent update is fantastic. Everything works smoothly.",
            )

        assert result is not None
        assert result.sentiment == Sentiment.POSITIVE
        assert result.sentiment_confidence == 0.9
        assert "features" in result.themes

    @pytest.mark.asyncio
    async def test_analyze_feedback_negative(self, analyzer):
        """Should detect negative sentiment."""
        mock_response = '{"sentiment": "negative", "sentiment_confidence": 0.95, "themes": ["reliability", "performance"], "summary": "App crashes"}'

        with patch.object(analyzer, "_get_client") as mock_client:
            mock_client.return_value.call = AsyncMock(return_value=(mock_response, {}))
            result = await analyzer.analyze_feedback(
                "App keeps crashing", "Every time I try to load a meeting, the page freezes."
            )

        assert result is not None
        assert result.sentiment == Sentiment.NEGATIVE
        assert "reliability" in result.themes

    @pytest.mark.asyncio
    async def test_analyze_feedback_neutral(self, analyzer):
        """Should detect neutral sentiment for feature requests."""
        mock_response = '{"sentiment": "neutral", "sentiment_confidence": 0.8, "themes": ["design"], "summary": "Dark mode request"}'

        with patch.object(analyzer, "_get_client") as mock_client:
            mock_client.return_value.call = AsyncMock(return_value=(mock_response, {}))
            result = await analyzer.analyze_feedback(
                "Add dark mode", "Would be nice to have a dark theme option."
            )

        assert result is not None
        assert result.sentiment == Sentiment.NEUTRAL

    @pytest.mark.asyncio
    async def test_analyze_feedback_mixed(self, analyzer):
        """Should detect mixed sentiment."""
        mock_response = '{"sentiment": "mixed", "sentiment_confidence": 0.7, "themes": ["features", "reliability"], "summary": "Good but buggy"}'

        with patch.object(analyzer, "_get_client") as mock_client:
            mock_client.return_value.call = AsyncMock(return_value=(mock_response, {}))
            result = await analyzer.analyze_feedback(
                "Good idea, poor execution", "I love the concept but the implementation is buggy."
            )

        assert result is not None
        assert result.sentiment == Sentiment.MIXED

    @pytest.mark.asyncio
    async def test_analyze_feedback_empty_input(self, analyzer):
        """Should return None for empty input."""
        result = await analyzer.analyze_feedback("", "")
        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_feedback_llm_failure_uses_fallback(self, analyzer):
        """Should use fallback when LLM fails."""
        with patch.object(analyzer, "_get_client") as mock_client:
            mock_client.return_value.call = AsyncMock(side_effect=Exception("API error"))
            result = await analyzer.analyze_feedback(
                "Slow loading times", "The app is very slow and needs optimization."
            )

        assert result is not None
        # Fallback should detect performance theme
        assert any(t in ["performance", "reliability"] for t in result.themes)

    def test_fallback_analyze_positive(self, analyzer):
        """Fallback should detect positive words."""
        result = analyzer._fallback_analyze(
            "Great app", "I love this app, it's amazing and fantastic!"
        )
        assert result.sentiment == Sentiment.POSITIVE

    def test_fallback_analyze_negative(self, analyzer):
        """Fallback should detect negative words."""
        result = analyzer._fallback_analyze(
            "Terrible experience", "This app is broken and frustrating to use."
        )
        assert result.sentiment == Sentiment.NEGATIVE

    def test_fallback_analyze_themes(self, analyzer):
        """Fallback should extract themes from keywords."""
        result = analyzer._fallback_analyze(
            "Performance issue", "The app is very slow and loading times are terrible."
        )
        assert "performance" in result.themes

    def test_fallback_analyze_pricing_theme(self, analyzer):
        """Fallback should detect pricing theme."""
        result = analyzer._fallback_analyze(
            "Too expensive", "The pricing plans are too expensive for small businesses."
        )
        assert "pricing" in result.themes


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_feedback_analyzer_singleton(self):
        """Should return singleton instance."""
        analyzer1 = get_feedback_analyzer()
        analyzer2 = get_feedback_analyzer()
        assert analyzer1 is analyzer2

    @pytest.mark.asyncio
    async def test_analyze_feedback_convenience(self):
        """Convenience function should work."""
        with patch("backend.services.feedback_analyzer.get_feedback_analyzer") as mock_get:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_feedback = AsyncMock(
                return_value=FeedbackAnalysis(
                    sentiment=Sentiment.POSITIVE,
                    sentiment_confidence=0.9,
                    themes=["features"],
                    analyzed_at="2025-12-13T10:00:00Z",
                )
            )
            mock_get.return_value = mock_analyzer

            result = await analyze_feedback("Test", "Description")

        assert result is not None
        assert result.sentiment == Sentiment.POSITIVE
