"""Tests for context-based project suggestions API.

Tests the GET /api/v1/projects/context-suggestions endpoint
and POST /api/v1/projects/context-suggestions for creating projects.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.context_project_suggester import (
    ContextProjectSuggestion,
    _format_context_for_prompt,
    _is_duplicate,
    get_context_completeness,
    suggest_from_context,
)


class TestContextCompleteness:
    """Tests for get_context_completeness function."""

    def test_no_context_returns_zero_completeness(self):
        """Test that missing context returns 0 completeness."""
        with patch("backend.services.context_project_suggester.UserRepository") as mock_repo:
            mock_repo.return_value.get_context.return_value = None

            result = get_context_completeness("user-123")

            assert result["completeness"] == 0.0
            assert result["has_minimum"] is False
            assert "primary_objective" in result["missing_required"]

    def test_partial_context_returns_partial_completeness(self):
        """Test that partial context returns partial completeness score."""
        with patch("backend.services.context_project_suggester.UserRepository") as mock_repo:
            mock_repo.return_value.get_context.return_value = {
                "primary_objective": "Grow revenue",
                "industry": "SaaS",
            }

            result = get_context_completeness("user-123")

            assert result["completeness"] > 0.0
            assert result["has_minimum"] is True
            assert len(result["missing_required"]) == 0
            assert "main_value_proposition" in result["missing_recommended"]

    def test_full_context_returns_high_completeness(self):
        """Test that full context returns high completeness score."""
        with patch("backend.services.context_project_suggester.UserRepository") as mock_repo:
            mock_repo.return_value.get_context.return_value = {
                "primary_objective": "Grow revenue to $10M ARR",
                "main_value_proposition": "AI-powered analytics",
                "industry": "SaaS",
                "business_model": "B2B subscription",
                "target_market": "Enterprise",
                "competitors": ["Competitor A", "Competitor B"],
            }

            result = get_context_completeness("user-123")

            assert result["completeness"] == 1.0
            assert result["has_minimum"] is True
            assert len(result["missing_required"]) == 0
            assert len(result["missing_recommended"]) == 0


class TestDuplicateDetection:
    """Tests for _is_duplicate function."""

    def test_exact_match_is_duplicate(self):
        """Test exact name match is detected as duplicate."""
        existing = {"product launch", "customer success"}
        assert _is_duplicate("Product Launch", existing) is True

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        existing = {"product launch"}
        assert _is_duplicate("PRODUCT LAUNCH", existing) is True

    def test_high_word_overlap_is_duplicate(self):
        """Test high word overlap is detected as duplicate."""
        existing = {"improve customer onboarding"}
        assert _is_duplicate("Customer Onboarding Improvement", existing) is True

    def test_distinct_names_not_duplicate(self):
        """Test distinct names are not flagged as duplicates."""
        existing = {"product launch", "customer success"}
        assert _is_duplicate("Revenue Growth Strategy", existing) is False


class TestFormatContextForPrompt:
    """Tests for _format_context_for_prompt function."""

    def test_formats_basic_context(self):
        """Test basic context formatting."""
        context = {
            "primary_objective": "Grow revenue",
            "industry": "SaaS",
        }

        result = _format_context_for_prompt(context)

        assert "Primary Objective: Grow revenue" in result
        assert "Industry: SaaS" in result

    def test_formats_competitors_list(self):
        """Test competitor list formatting."""
        context = {
            "primary_objective": "Test",
            "competitors": ["Acme", "BigCorp"],
        }

        result = _format_context_for_prompt(context)

        assert "Competitors: Acme, BigCorp" in result

    def test_handles_empty_context(self):
        """Test empty context returns fallback."""
        context = {}
        result = _format_context_for_prompt(context)
        assert result == "No context available"


class TestSuggestFromContext:
    """Tests for suggest_from_context function."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_context(self):
        """Test returns empty list when no context exists."""
        with patch("backend.services.context_project_suggester.UserRepository") as mock_repo:
            mock_repo.return_value.get_context.return_value = None

            result = await suggest_from_context("user-123")

            assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_missing_primary_objective(self):
        """Test returns empty when primary_objective is missing."""
        with patch("backend.services.context_project_suggester.UserRepository") as mock_repo:
            mock_repo.return_value.get_context.return_value = {
                "industry": "SaaS",
            }

            result = await suggest_from_context("user-123")

            assert result == []

    @pytest.mark.asyncio
    async def test_calls_llm_with_context(self):
        """Test LLM is called with formatted context."""
        with (
            patch("backend.services.context_project_suggester.UserRepository") as mock_user_repo,
            patch(
                "backend.services.context_project_suggester.ProjectRepository"
            ) as mock_project_repo,
            patch("backend.services.context_project_suggester._get_client") as mock_client,
        ):
            mock_user_repo.return_value.get_context.return_value = {
                "primary_objective": "Grow revenue to $10M ARR",
                "industry": "SaaS",
            }
            mock_project_repo.return_value.get_by_user.return_value = (0, [])

            # Mock LLM response
            mock_llm = MagicMock()
            mock_llm.call = AsyncMock(
                return_value=(
                    '{"suggestions": [{"name": "Test Project", "description": "A test", "rationale": "Because", "category": "growth", "priority": "high"}]}',
                    {},
                )
            )
            mock_client.return_value = mock_llm

            result = await suggest_from_context("user-123")

            mock_llm.call.assert_called_once()
            assert len(result) == 1
            assert result[0].name == "Test Project"
            assert result[0].category == "growth"
            assert result[0].priority == "high"

    @pytest.mark.asyncio
    async def test_filters_duplicates(self):
        """Test duplicate suggestions are filtered out."""
        with (
            patch("backend.services.context_project_suggester.UserRepository") as mock_user_repo,
            patch(
                "backend.services.context_project_suggester.ProjectRepository"
            ) as mock_project_repo,
            patch("backend.services.context_project_suggester._get_client") as mock_client,
        ):
            mock_user_repo.return_value.get_context.return_value = {
                "primary_objective": "Grow revenue",
            }
            # Existing project with name "Revenue Growth"
            mock_project_repo.return_value.get_by_user.return_value = (
                1,
                [{"name": "Revenue Growth"}],
            )

            # LLM suggests a duplicate
            mock_llm = MagicMock()
            mock_llm.call = AsyncMock(
                return_value=(
                    '{"suggestions": [{"name": "Revenue Growth Strategy", "description": "Grow revenue", "rationale": "Because", "category": "growth", "priority": "high"}]}',
                    {},
                )
            )
            mock_client.return_value = mock_llm

            result = await suggest_from_context("user-123")

            # Should filter out the duplicate
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_handles_llm_error(self):
        """Test graceful handling of LLM errors."""
        with (
            patch("backend.services.context_project_suggester.UserRepository") as mock_user_repo,
            patch(
                "backend.services.context_project_suggester.ProjectRepository"
            ) as mock_project_repo,
            patch("backend.services.context_project_suggester._get_client") as mock_client,
        ):
            mock_user_repo.return_value.get_context.return_value = {
                "primary_objective": "Grow revenue",
            }
            mock_project_repo.return_value.get_by_user.return_value = (0, [])

            # LLM raises error
            mock_llm = MagicMock()
            mock_llm.call = AsyncMock(side_effect=Exception("API error"))
            mock_client.return_value = mock_llm

            result = await suggest_from_context("user-123")

            assert result == []


class TestContextSuggestionDataclass:
    """Tests for ContextProjectSuggestion dataclass."""

    def test_creates_suggestion(self):
        """Test suggestion creation."""
        suggestion = ContextProjectSuggestion(
            id="test-123",
            name="Test Project",
            description="A test project",
            rationale="For testing",
            category="strategy",
            priority="high",
        )

        assert suggestion.id == "test-123"
        assert suggestion.name == "Test Project"
        assert suggestion.category == "strategy"
        assert suggestion.priority == "high"


class TestAPIEndpoint:
    """Tests for the API endpoint integration.

    Note: Full API integration tests require TestClient setup with auth fixtures.
    These are verified via E2E tests. Basic router verification below.
    """

    def test_endpoints_exist(self):
        """Verify API endpoints are defined in the router."""
        from backend.api.projects import router

        # Check route paths exist (paths include /v1/projects prefix)
        paths = [route.path for route in router.routes]

        assert "/v1/projects/context-suggestions" in paths
