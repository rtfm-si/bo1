"""Tests for demo question generator service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.demo_questions import (
    FALLBACK_QUESTIONS,
    DemoQuestion,
    _build_context_summary,
    clear_cached_questions,
    generate_demo_questions,
)


class TestBuildContextSummary:
    """Tests for _build_context_summary function."""

    def test_empty_context(self):
        """Empty context returns default message."""
        result = _build_context_summary({})
        assert result == "No business context provided."

    def test_full_context(self):
        """Full context includes all fields."""
        context = {
            "business_model": "B2B SaaS",
            "target_market": "Small businesses",
            "product_description": "AI analytics tool",
            "company_name": "Acme Corp",
            "stage": "growing",
            "industry": "Technology",
            "revenue": 500000,
            "customers": 150,
            "growth_rate": 25.5,
            "competitors": ["Competitor A", "Competitor B"],
            "challenges": ["Scaling", "Retention"],
        }
        result = _build_context_summary(context)

        assert "Business model: B2B SaaS" in result
        assert "Target market: Small businesses" in result
        assert "Product/service: AI analytics tool" in result
        assert "Company: Acme Corp" in result
        assert "Business stage: growing" in result
        assert "Industry: Technology" in result
        assert "Revenue: $500,000" in result
        assert "Customers: 150" in result
        assert "Growth rate: 25.5%" in result
        assert "Competitors: Competitor A, Competitor B" in result
        assert "Key challenges: Scaling, Retention" in result

    def test_partial_context(self):
        """Partial context includes only provided fields."""
        context = {
            "business_model": "B2B SaaS",
            "company_name": "Acme",
        }
        result = _build_context_summary(context)

        assert "Business model: B2B SaaS" in result
        assert "Company: Acme" in result
        assert "Revenue" not in result
        assert "Competitors" not in result


class TestGenerateDemoQuestions:
    """Tests for generate_demo_questions function."""

    @pytest.mark.asyncio
    async def test_returns_fallback_for_empty_context(self):
        """Returns fallback questions when context is empty."""
        result = await generate_demo_questions("user-123", context=None)

        assert result.generated is False
        assert result.cached is False
        assert len(result.questions) == len(FALLBACK_QUESTIONS)
        assert result.questions[0].question == FALLBACK_QUESTIONS[0].question

    @pytest.mark.asyncio
    async def test_returns_fallback_for_none_values(self):
        """Returns fallback when context has all None values."""
        result = await generate_demo_questions(
            "user-123",
            context={"business_model": None, "company_name": None},
        )

        assert result.generated is False
        assert len(result.questions) == len(FALLBACK_QUESTIONS)

    @pytest.mark.asyncio
    async def test_returns_cached_questions(self):
        """Returns cached questions without regenerating."""
        cached_questions = [
            DemoQuestion(
                question="Cached question?",
                category="strategy",
                relevance="Test relevance",
            )
        ]

        with patch(
            "backend.services.demo_questions._get_cached_questions",
            return_value=cached_questions,
        ):
            result = await generate_demo_questions(
                "user-123",
                context={"business_model": "B2B SaaS"},
                force_refresh=False,
            )

        assert result.cached is True
        assert result.generated is False
        assert result.questions == cached_questions

    @pytest.mark.asyncio
    async def test_force_refresh_skips_cache(self):
        """Force refresh skips cache and generates new questions."""
        cached_questions = [
            DemoQuestion(
                question="Cached question?",
                category="strategy",
                relevance="Test relevance",
            )
        ]

        # Mock cache to return questions
        with (
            patch(
                "backend.services.demo_questions._get_cached_questions",
                return_value=cached_questions,
            ),
            patch("backend.services.demo_questions._cache_questions") as mock_cache,
        ):
            # Mock LLM broker to return valid response
            mock_response = MagicMock()
            mock_response.content = json.dumps(
                [
                    {
                        "question": "New question?",
                        "category": "growth",
                        "relevance": "New relevance",
                    }
                ]
            )

            mock_broker = AsyncMock()
            mock_broker.call = AsyncMock(return_value=mock_response)

            with patch(
                "backend.services.demo_questions.PromptBroker",
                return_value=mock_broker,
            ):
                result = await generate_demo_questions(
                    "user-123",
                    context={"business_model": "B2B SaaS"},
                    force_refresh=True,
                )

        # Should have generated new questions
        assert result.generated is True
        assert result.cached is False
        assert result.questions[0].question == "New question?"
        # Should have cached the new questions
        mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_failure_returns_fallback(self):
        """Returns fallback questions when LLM fails."""
        with (
            patch(
                "backend.services.demo_questions._get_cached_questions",
                return_value=None,
            ),
            patch(
                "backend.services.demo_questions.PromptBroker",
                side_effect=Exception("LLM unavailable"),
            ),
        ):
            result = await generate_demo_questions(
                "user-123",
                context={"business_model": "B2B SaaS"},
            )

        assert result.generated is False
        assert result.cached is False
        assert len(result.questions) == len(FALLBACK_QUESTIONS)

    @pytest.mark.asyncio
    async def test_invalid_json_returns_fallback(self):
        """Returns fallback when LLM returns invalid JSON."""
        with patch(
            "backend.services.demo_questions._get_cached_questions",
            return_value=None,
        ):
            mock_response = MagicMock()
            mock_response.content = "Not valid JSON"

            mock_broker = AsyncMock()
            mock_broker.call = AsyncMock(return_value=mock_response)

            with patch(
                "backend.services.demo_questions.PromptBroker",
                return_value=mock_broker,
            ):
                result = await generate_demo_questions(
                    "user-123",
                    context={"business_model": "B2B SaaS"},
                )

        assert result.generated is False
        assert len(result.questions) == len(FALLBACK_QUESTIONS)


class TestClearCachedQuestions:
    """Tests for clear_cached_questions function."""

    def test_clear_success(self):
        """Successfully clears cached questions."""
        mock_client = MagicMock()

        with patch(
            "backend.services.demo_questions._get_redis_client",
            return_value=mock_client,
        ):
            result = clear_cached_questions("user-123")

        assert result is True
        mock_client.delete.assert_called_once_with("demo_questions:user-123")

    def test_clear_handles_redis_error(self):
        """Handles Redis errors gracefully."""
        with patch(
            "backend.services.demo_questions._get_redis_client",
            side_effect=Exception("Redis unavailable"),
        ):
            result = clear_cached_questions("user-123")

        assert result is False


class TestDemoQuestionModel:
    """Tests for DemoQuestion model."""

    def test_valid_question(self):
        """Valid question creates successfully."""
        q = DemoQuestion(
            question="Should we expand?",
            category="growth",
            relevance="Given your stage, expansion is relevant.",
        )
        assert q.question == "Should we expand?"
        assert q.category == "growth"
        assert q.relevance == "Given your stage, expansion is relevant."

    def test_model_dump(self):
        """Model dumps to dictionary correctly."""
        q = DemoQuestion(
            question="Test?",
            category="strategy",
            relevance="Test relevance",
        )
        data = q.model_dump()
        assert data == {
            "question": "Test?",
            "category": "strategy",
            "relevance": "Test relevance",
        }
