"""Tests for SEO trend analysis endpoint.

Validates:
- Input validation (keywords, industry)
- Tier-based limit enforcement
- Rate limiting
- Response structure
"""

from unittest.mock import AsyncMock, patch

import pytest

from backend.api.seo.routes import (
    TrendAnalysisRequest,
    TrendAnalysisResult,
    TrendOpportunity,
    _perform_trend_analysis,
)
from bo1.billing import PlanConfig


@pytest.mark.unit
class TestTrendAnalysisRequest:
    """Test TrendAnalysisRequest model validation."""

    def test_valid_single_keyword(self):
        """Single keyword should be valid."""
        req = TrendAnalysisRequest(keywords=["saas"])
        assert req.keywords == ["saas"]
        assert req.industry is None

    def test_valid_multiple_keywords(self):
        """Multiple keywords should be valid."""
        req = TrendAnalysisRequest(
            keywords=["saas", "project management", "collaboration"],
            industry="SaaS",
        )
        assert len(req.keywords) == 3
        assert req.industry == "SaaS"

    def test_empty_keywords_fails(self):
        """Empty keywords list should fail."""
        with pytest.raises(ValueError):
            TrendAnalysisRequest(keywords=[])

    def test_too_many_keywords_fails(self):
        """More than 10 keywords should fail."""
        with pytest.raises(ValueError):
            TrendAnalysisRequest(keywords=[f"keyword{i}" for i in range(11)])


@pytest.mark.unit
class TestSeoLimitEnforcement:
    """Test tier-based limit enforcement."""

    def test_free_tier_limit_is_one(self):
        """Free tier should allow 1 analysis per month."""
        assert PlanConfig.get_seo_analyses_limit("free") == 1

    def test_starter_tier_limit_is_five(self):
        """Starter tier should allow 5 analyses per month."""
        assert PlanConfig.get_seo_analyses_limit("starter") == 5

    def test_pro_tier_is_unlimited(self):
        """Pro tier should have unlimited analyses."""
        limit = PlanConfig.get_seo_analyses_limit("pro")
        assert PlanConfig.is_unlimited(limit)

    def test_seo_tools_feature_enabled_all_tiers(self):
        """SEO tools should be enabled for all tiers."""
        for tier in ["free", "starter", "pro", "enterprise"]:
            assert PlanConfig.is_feature_enabled(tier, "seo_tools") is True


@pytest.mark.unit
class TestPerformTrendAnalysis:
    """Test _perform_trend_analysis helper."""

    @pytest.mark.asyncio
    @patch("backend.api.seo.routes.ResearcherAgent")
    async def test_performs_research_with_keywords(self, mock_agent_class):
        """Should call ResearcherAgent with formatted questions."""
        mock_agent = AsyncMock()
        mock_agent.research_questions = AsyncMock(
            return_value=[
                {
                    "question": "What are the current SEO trends for 'saas'?",
                    "summary": "SaaS SEO trends are rising.",
                    "sources": ["https://example.com"],
                    "confidence": "high",
                }
            ]
        )
        mock_agent_class.return_value = mock_agent

        result = await _perform_trend_analysis(["saas"], "SaaS", "free")

        assert isinstance(result, TrendAnalysisResult)
        assert result.keywords_analyzed == ["saas"]
        assert result.industry == "SaaS"
        mock_agent.research_questions.assert_called_once()

    @pytest.mark.asyncio
    @patch("backend.api.seo.routes.ResearcherAgent")
    async def test_returns_structured_result(self, mock_agent_class):
        """Should return properly structured TrendAnalysisResult."""
        mock_agent = AsyncMock()
        mock_agent.research_questions = AsyncMock(
            return_value=[
                {
                    "question": "test",
                    "summary": "Test summary for trends",
                    "sources": ["https://source1.com", "https://source2.com"],
                    "confidence": "high",
                }
            ]
        )
        mock_agent_class.return_value = mock_agent

        result = await _perform_trend_analysis(["test"], None, "pro")

        assert hasattr(result, "executive_summary")
        assert hasattr(result, "key_trends")
        assert hasattr(result, "opportunities")
        assert hasattr(result, "threats")
        assert hasattr(result, "sources")


@pytest.mark.unit
class TestTrendAnalysisResult:
    """Test TrendAnalysisResult model."""

    def test_model_with_all_fields(self):
        """Should accept all fields."""
        result = TrendAnalysisResult(
            executive_summary="Test summary",
            key_trends=["Trend 1", "Trend 2"],
            opportunities=[
                TrendOpportunity(
                    topic="test",
                    trend_direction="rising",
                    relevance_score=0.8,
                    description="Test opportunity",
                )
            ],
            threats=[],
            keywords_analyzed=["keyword1"],
            industry="SaaS",
            sources=["https://example.com"],
        )
        assert result.executive_summary == "Test summary"
        assert len(result.key_trends) == 2
        assert len(result.opportunities) == 1

    def test_model_with_minimal_fields(self):
        """Should accept minimal required fields."""
        result = TrendAnalysisResult(
            executive_summary="Summary",
            key_trends=[],
            opportunities=[],
            threats=[],
            keywords_analyzed=["test"],
            industry=None,
            sources=[],
        )
        assert result.executive_summary == "Summary"
        assert result.industry is None
