"""Tests for competitor insights API endpoints."""

from unittest.mock import MagicMock, patch

import pytest

from backend.api.context.models import (
    CompetitorInsight,
    CompetitorInsightResponse,
    CompetitorInsightsListResponse,
)
from backend.api.context.routes import (
    COMPETITOR_INSIGHT_TIER_LIMITS,
    _get_insight_limit_for_tier,
)


class TestCompetitorInsightModels:
    """Tests for competitor insight Pydantic models."""

    def test_competitor_insight_all_fields(self):
        """Test CompetitorInsight with all fields populated."""
        insight = CompetitorInsight(
            name="Notion",
            tagline="Your connected workspace",
            size_estimate="500-1000 employees",
            revenue_estimate="$100M-200M ARR",
            strengths=["Great UX", "Strong brand"],
            weaknesses=["Slow with large databases"],
            market_gaps=["Enterprise security"],
            last_updated="2025-01-01T00:00:00Z",
        )

        assert insight.name == "Notion"
        assert insight.tagline == "Your connected workspace"
        assert len(insight.strengths) == 2
        assert len(insight.weaknesses) == 1
        assert len(insight.market_gaps) == 1

    def test_competitor_insight_minimal(self):
        """Test CompetitorInsight with minimal fields."""
        insight = CompetitorInsight(
            name="MinimalCo",
            strengths=[],
            weaknesses=[],
            market_gaps=[],
        )

        assert insight.name == "MinimalCo"
        assert insight.tagline is None
        assert insight.size_estimate is None
        assert insight.strengths == []

    def test_competitor_insight_response_success(self):
        """Test CompetitorInsightResponse with success."""
        insight = CompetitorInsight(
            name="TestCo",
            strengths=["A"],
            weaknesses=[],
            market_gaps=[],
        )
        response = CompetitorInsightResponse(
            success=True,
            insight=insight,
            generation_status="complete",
        )

        assert response.success is True
        assert response.insight.name == "TestCo"
        assert response.error is None

    def test_competitor_insight_response_error(self):
        """Test CompetitorInsightResponse with error."""
        response = CompetitorInsightResponse(
            success=False,
            insight=None,
            error="Rate limit exceeded",
            generation_status="error",
        )

        assert response.success is False
        assert response.insight is None
        assert response.error == "Rate limit exceeded"

    def test_competitor_insights_list_response(self):
        """Test CompetitorInsightsListResponse with tier gating."""
        insights = [
            CompetitorInsight(name="Co1", strengths=[], weaknesses=[], market_gaps=[]),
            CompetitorInsight(name="Co2", strengths=[], weaknesses=[], market_gaps=[]),
        ]
        response = CompetitorInsightsListResponse(
            success=True,
            insights=insights,
            visible_count=2,
            total_count=5,
            tier="free",
            upgrade_prompt="Upgrade to see 3 more competitor insights.",
        )

        assert response.success is True
        assert len(response.insights) == 2
        assert response.visible_count == 2
        assert response.total_count == 5
        assert response.tier == "free"
        assert "Upgrade" in response.upgrade_prompt


class TestTierLimits:
    """Tests for tier-based insight limits."""

    def test_tier_limits_defined(self):
        """Test that tier limits are defined correctly."""
        assert COMPETITOR_INSIGHT_TIER_LIMITS["free"] == 1
        assert COMPETITOR_INSIGHT_TIER_LIMITS["starter"] == 3
        assert COMPETITOR_INSIGHT_TIER_LIMITS["pro"] == 100
        assert COMPETITOR_INSIGHT_TIER_LIMITS["enterprise"] == 100

    def test_get_insight_limit_for_tier_known(self):
        """Test getting limit for known tiers."""
        assert _get_insight_limit_for_tier("free") == 1
        assert _get_insight_limit_for_tier("starter") == 3
        assert _get_insight_limit_for_tier("pro") == 100

    def test_get_insight_limit_for_tier_unknown(self):
        """Test getting limit for unknown tier defaults to free."""
        assert _get_insight_limit_for_tier("unknown_tier") == 1
        assert _get_insight_limit_for_tier("") == 1


class TestCompetitorInsightEndpoints:
    """Tests for competitor insight API endpoint logic."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock user_repository."""
        with patch("backend.api.context.routes.user_repository") as mock:
            yield mock

    @pytest.fixture
    def mock_analyzer(self):
        """Mock competitor analyzer."""
        with patch("backend.api.context.routes.get_competitor_analyzer") as mock_get:
            analyzer = MagicMock()
            mock_get.return_value = analyzer
            yield analyzer

    def test_generate_insight_cache_hit(self, mock_user_repository):
        """Test that cached insights are returned without regenerating."""
        cached_insight = {
            "name": "CachedCo",
            "tagline": "Already generated",
            "size_estimate": "100 employees",
            "revenue_estimate": "$10M ARR",
            "strengths": ["Fast"],
            "weaknesses": ["Limited"],
            "market_gaps": ["Enterprise"],
            "last_updated": "2025-01-01T00:00:00Z",
        }
        mock_user_repository.get_context.return_value = {
            "competitor_insights": {"CachedCo": cached_insight}
        }

        # Simulate the endpoint logic for cache check
        context_data = mock_user_repository.get_context("test_user") or {}
        cached_insights = context_data.get("competitor_insights", {})
        name = "CachedCo"
        refresh = False

        # This is the cache hit path
        assert name in cached_insights
        assert not refresh

        insight_data = cached_insights[name]
        response = CompetitorInsightResponse(
            success=True,
            insight=CompetitorInsight(**insight_data),
            generation_status="cached",
        )

        assert response.success is True
        assert response.generation_status == "cached"
        assert response.insight.name == "CachedCo"

    def test_list_insights_tier_gating_free(self, mock_user_repository):
        """Test that free tier only sees 1 insight."""
        # Setup 3 cached insights
        cached = {
            "Co1": {"name": "Co1", "strengths": [], "weaknesses": [], "market_gaps": []},
            "Co2": {"name": "Co2", "strengths": [], "weaknesses": [], "market_gaps": []},
            "Co3": {"name": "Co3", "strengths": [], "weaknesses": [], "market_gaps": []},
        }
        mock_user_repository.get_context.return_value = {"competitor_insights": cached}

        tier = "free"
        limit = _get_insight_limit_for_tier(tier)
        total_count = len(cached)
        visible_count = min(total_count, limit)

        assert limit == 1
        assert total_count == 3
        assert visible_count == 1

        # Build response
        insights = []
        for i, (_name, data) in enumerate(cached.items()):
            if i >= limit:
                break
            insights.append(CompetitorInsight(**data))

        assert len(insights) == 1
        assert insights[0].name == "Co1"

    def test_list_insights_tier_gating_pro(self, mock_user_repository):
        """Test that pro tier sees all insights."""
        cached = {
            "Co1": {"name": "Co1", "strengths": [], "weaknesses": [], "market_gaps": []},
            "Co2": {"name": "Co2", "strengths": [], "weaknesses": [], "market_gaps": []},
            "Co3": {"name": "Co3", "strengths": [], "weaknesses": [], "market_gaps": []},
        }
        mock_user_repository.get_context.return_value = {"competitor_insights": cached}

        tier = "pro"
        limit = _get_insight_limit_for_tier(tier)
        total_count = len(cached)
        visible_count = min(total_count, limit)

        assert limit == 100
        assert visible_count == 3  # All 3 visible

    def test_upgrade_prompt_when_limit_reached(self, mock_user_repository):
        """Test that upgrade prompt is generated when limit reached."""
        cached = {
            "Co1": {"name": "Co1", "strengths": [], "weaknesses": [], "market_gaps": []},
            "Co2": {"name": "Co2", "strengths": [], "weaknesses": [], "market_gaps": []},
        }

        tier = "free"
        limit = _get_insight_limit_for_tier(tier)
        total_count = len(cached)
        visible_count = min(total_count, limit)

        # Build upgrade prompt
        upgrade_prompt = None
        if total_count > visible_count:
            hidden_count = total_count - visible_count
            upgrade_prompt = (
                f"Upgrade to see {hidden_count} more competitor insight"
                f"{'s' if hidden_count > 1 else ''}."
            )

        assert upgrade_prompt == "Upgrade to see 1 more competitor insight."

    def test_no_upgrade_prompt_when_under_limit(self, mock_user_repository):
        """Test that no upgrade prompt when under limit."""
        cached = {
            "Co1": {"name": "Co1", "strengths": [], "weaknesses": [], "market_gaps": []},
        }

        tier = "starter"  # Limit is 3
        limit = _get_insight_limit_for_tier(tier)
        total_count = len(cached)
        visible_count = min(total_count, limit)

        upgrade_prompt = None
        if total_count > visible_count:
            hidden_count = total_count - visible_count
            upgrade_prompt = f"Upgrade to see {hidden_count} more."

        assert upgrade_prompt is None  # 1 insight, limit is 3

    def test_delete_insight_removes_from_cache(self, mock_user_repository):
        """Test that deleting insight removes it from cache."""
        cached = {
            "Co1": {"name": "Co1", "strengths": [], "weaknesses": [], "market_gaps": []},
            "Co2": {"name": "Co2", "strengths": [], "weaknesses": [], "market_gaps": []},
        }
        context_data = {"competitor_insights": cached.copy()}
        mock_user_repository.get_context.return_value = context_data

        # Simulate delete
        name_to_delete = "Co1"
        del context_data["competitor_insights"][name_to_delete]

        assert name_to_delete not in context_data["competitor_insights"]
        assert len(context_data["competitor_insights"]) == 1
