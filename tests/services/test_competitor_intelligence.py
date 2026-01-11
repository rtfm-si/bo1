"""Tests for CompetitorIntelligenceService.

Tests multi-query Tavily search and LLM parsing for competitor intelligence.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.services.competitor_intelligence import (
    CompetitorIntel,
    CompetitorIntelligenceService,
    FundingRound,
    ProductUpdate,
    intel_to_dict,
)


class TestIntelToDict:
    """Tests for intel_to_dict helper function."""

    def test_converts_full_intel_to_dict(self):
        """Should convert CompetitorIntel with all fields to dict."""
        intel = CompetitorIntel(
            name="Acme Corp",
            funding_rounds=[
                FundingRound(
                    round_type="Series A",
                    amount="$10M",
                    date="2024-06-15",
                    investors=["Sequoia", "a16z"],
                )
            ],
            product_updates=[
                ProductUpdate(
                    title="AI Feature Launch",
                    date="2024-08-01",
                    description="Launched new AI assistant",
                    source_url="https://techcrunch.com/acme-ai",
                )
            ],
            recent_news=[
                {
                    "title": "Acme Expands",
                    "date": "2024-09-01",
                    "source_url": "https://news.com/acme",
                }
            ],
            key_signals=["Raised Series A", "Launched AI feature", "Expanding to Europe"],
            gathered_at=datetime(2024, 10, 1, 12, 0, 0, tzinfo=UTC),
        )

        result = intel_to_dict(intel)

        assert result["funding_rounds"] == [
            {
                "round_type": "Series A",
                "amount": "$10M",
                "date": "2024-06-15",
                "investors": ["Sequoia", "a16z"],
            }
        ]
        assert result["product_updates"] == [
            {
                "title": "AI Feature Launch",
                "date": "2024-08-01",
                "description": "Launched new AI assistant",
                "source_url": "https://techcrunch.com/acme-ai",
            }
        ]
        assert result["key_signals"] == [
            "Raised Series A",
            "Launched AI feature",
            "Expanding to Europe",
        ]
        assert result["recent_news"] == [
            {"title": "Acme Expands", "date": "2024-09-01", "source_url": "https://news.com/acme"}
        ]
        assert result["gathered_at"] == "2024-10-01T12:00:00+00:00"

    def test_converts_empty_intel_to_dict(self):
        """Should convert empty CompetitorIntel to dict with empty arrays."""
        intel = CompetitorIntel(
            name="Empty Corp",
            funding_rounds=[],
            product_updates=[],
            recent_news=[],
            key_signals=[],
            gathered_at=datetime(2024, 10, 1, 12, 0, 0, tzinfo=UTC),
        )

        result = intel_to_dict(intel)

        assert result["funding_rounds"] == []
        assert result["product_updates"] == []
        assert result["recent_news"] == []
        assert result["key_signals"] == []


class TestCompetitorIntelligenceService:
    """Tests for CompetitorIntelligenceService."""

    @pytest.fixture
    def service(self):
        """Create service with mocked settings."""
        with patch("backend.services.competitor_intelligence.get_settings") as mock_settings:
            settings = MagicMock()
            settings.tavily_api_key = "test-api-key"
            mock_settings.return_value = settings
            yield CompetitorIntelligenceService()

    @pytest.fixture
    def mock_tavily_funding_response(self):
        """Mock Tavily response for funding search."""
        return {
            "results": [
                {
                    "title": "Acme Corp Raises $20M Series B",
                    "url": "https://techcrunch.com/acme-series-b",
                    "content": "Acme Corp announced today that it has raised $20 million in Series B funding led by Sequoia Capital.",
                },
                {
                    "title": "Acme Funding History - Crunchbase",
                    "url": "https://crunchbase.com/acme",
                    "content": "Acme Corp has raised a total of $30M in funding. Series A: $10M in 2023.",
                },
            ]
        }

    @pytest.fixture
    def mock_tavily_product_response(self):
        """Mock Tavily response for product search."""
        return {
            "results": [
                {
                    "title": "Acme Launches AI-Powered Analytics",
                    "url": "https://producthunt.com/acme-ai",
                    "content": "Today Acme released its new AI analytics feature, allowing users to get insights faster.",
                },
            ]
        }

    @pytest.fixture
    def mock_tavily_news_response(self):
        """Mock Tavily response for news search."""
        return {
            "results": [
                {
                    "title": "Acme Expands to European Market",
                    "url": "https://news.com/acme-europe",
                    "content": "Acme Corp announced expansion plans to serve customers in UK and Germany.",
                },
            ]
        }

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM response for intel parsing."""
        return json.dumps(
            {
                "funding_rounds": [
                    {
                        "round_type": "Series B",
                        "amount": "$20M",
                        "date": "2024-06-15",
                        "investors": ["Sequoia Capital"],
                    },
                    {
                        "round_type": "Series A",
                        "amount": "$10M",
                        "date": "2023-01-01",
                        "investors": [],
                    },
                ],
                "product_updates": [
                    {
                        "title": "AI-Powered Analytics Launch",
                        "date": "2024-08-01",
                        "description": "New AI feature for faster insights",
                        "source_url": "https://producthunt.com/acme-ai",
                    }
                ],
                "recent_news": [
                    {
                        "title": "European Expansion",
                        "date": "2024-09-15",
                        "source_url": "https://news.com/acme-europe",
                    }
                ],
                "key_signals": [
                    "Raised $20M Series B",
                    "Launched AI analytics",
                    "Expanding to Europe",
                ],
            }
        )

    @pytest.mark.asyncio
    async def test_gather_intel_returns_none_without_api_key(self):
        """Should return None when Tavily API key is not configured."""
        with patch("backend.services.competitor_intelligence.get_settings") as mock_settings:
            settings = MagicMock()
            settings.tavily_api_key = None
            mock_settings.return_value = settings
            service = CompetitorIntelligenceService()

            result = await service.gather_competitor_intel("Acme Corp")

            assert result is None

    @pytest.mark.asyncio
    async def test_gather_intel_makes_three_tavily_searches(
        self,
        service,
        mock_tavily_funding_response,
        mock_tavily_product_response,
        mock_tavily_news_response,
        mock_llm_response,
    ):
        """Should make 3 parallel Tavily searches for funding, products, and news."""
        search_calls = []

        async def mock_post(url, json):
            search_calls.append(json["query"])
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()

            if "funding" in json["query"].lower():
                mock_response.json.return_value = mock_tavily_funding_response
            elif "product" in json["query"].lower():
                mock_response.json.return_value = mock_tavily_product_response
            else:
                mock_response.json.return_value = mock_tavily_news_response

            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = mock_post
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            with patch("backend.services.competitor_intelligence.ClaudeClient") as mock_claude:
                mock_claude_instance = MagicMock()
                mock_claude_instance.call = AsyncMock(return_value=(mock_llm_response, {}))
                mock_claude.return_value = mock_claude_instance

                await service.gather_competitor_intel("Acme Corp")

        # Should have made 3 search calls
        assert len(search_calls) == 3
        assert any("funding" in q.lower() for q in search_calls)
        assert any("product" in q.lower() for q in search_calls)
        assert any("news" in q.lower() for q in search_calls)

    @pytest.mark.asyncio
    async def test_gather_intel_parses_results_with_llm(
        self,
        service,
        mock_tavily_funding_response,
        mock_tavily_product_response,
        mock_tavily_news_response,
        mock_llm_response,
    ):
        """Should parse combined search results with LLM into structured intel."""

        async def mock_post(url, json):
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            if "funding" in json["query"].lower():
                mock_response.json.return_value = mock_tavily_funding_response
            elif "product" in json["query"].lower():
                mock_response.json.return_value = mock_tavily_product_response
            else:
                mock_response.json.return_value = mock_tavily_news_response
            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = mock_post
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            with patch("backend.services.competitor_intelligence.ClaudeClient") as mock_claude:
                mock_claude_instance = MagicMock()
                mock_claude_instance.call = AsyncMock(return_value=(mock_llm_response, {}))
                mock_claude.return_value = mock_claude_instance

                result = await service.gather_competitor_intel("Acme Corp")

        assert result is not None
        assert result.name == "Acme Corp"
        assert len(result.funding_rounds) == 2
        assert result.funding_rounds[0].round_type == "Series B"
        assert result.funding_rounds[0].amount == "$20M"
        assert len(result.product_updates) == 1
        assert result.product_updates[0].title == "AI-Powered Analytics Launch"
        assert len(result.key_signals) == 3
        assert "Raised $20M Series B" in result.key_signals

    @pytest.mark.asyncio
    async def test_gather_intel_handles_failed_search_gracefully(self, service, mock_llm_response):
        """Should continue if one search fails, using empty results for that category."""
        call_count = 0

        async def mock_post(url, json):
            nonlocal call_count
            call_count += 1
            if "funding" in json["query"].lower():
                raise httpx.HTTPError("Connection failed")

            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"results": []}
            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = mock_post
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            # LLM returns empty intel since no results
            empty_response = json.dumps(
                {
                    "funding_rounds": [],
                    "product_updates": [],
                    "recent_news": [],
                    "key_signals": [],
                }
            )

            with patch("backend.services.competitor_intelligence.ClaudeClient") as mock_claude:
                mock_claude_instance = MagicMock()
                mock_claude_instance.call = AsyncMock(return_value=(empty_response, {}))
                mock_claude.return_value = mock_claude_instance

                result = await service.gather_competitor_intel("Acme Corp")

        # Should still return a result, just with empty arrays
        assert result is not None
        assert result.name == "Acme Corp"
        assert len(result.funding_rounds) == 0

    @pytest.mark.asyncio
    async def test_gather_intel_handles_invalid_llm_response(
        self,
        service,
        mock_tavily_funding_response,
        mock_tavily_product_response,
        mock_tavily_news_response,
    ):
        """Should return empty intel if LLM response is invalid JSON."""

        async def mock_post(url, json):
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"results": []}
            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = mock_post
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            with patch("backend.services.competitor_intelligence.ClaudeClient") as mock_claude:
                mock_claude_instance = MagicMock()
                mock_claude_instance.call = AsyncMock(return_value=("invalid json response", {}))
                mock_claude.return_value = mock_claude_instance

                result = await service.gather_competitor_intel("Acme Corp")

        # Should return empty intel rather than crashing
        assert result is not None
        assert result.name == "Acme Corp"
        assert len(result.funding_rounds) == 0
        assert len(result.product_updates) == 0
        assert len(result.key_signals) == 0

    @pytest.mark.asyncio
    async def test_search_funding_uses_correct_domains(self, service):
        """Should search funding-related domains (Crunchbase, TechCrunch, etc.)."""
        captured_json = None

        async def mock_post(url, json):
            nonlocal captured_json
            captured_json = json
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"results": []}
            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = mock_post
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            await service._search_funding("Acme Corp")

        assert captured_json is not None
        assert "crunchbase.com" in captured_json["include_domains"]
        assert "techcrunch.com" in captured_json["include_domains"]

    @pytest.mark.asyncio
    async def test_search_product_updates_uses_correct_domains(self, service):
        """Should search product-related domains (ProductHunt, TechCrunch, etc.)."""
        captured_json = None

        async def mock_post(url, json):
            nonlocal captured_json
            captured_json = json
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"results": []}
            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = mock_post
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            await service._search_product_updates("Acme Corp")

        assert captured_json is not None
        assert "producthunt.com" in captured_json["include_domains"]


class TestFundingRoundModel:
    """Tests for FundingRound dataclass."""

    def test_creates_funding_round_with_all_fields(self):
        """Should create FundingRound with all fields populated."""
        round = FundingRound(
            round_type="Series A",
            amount="$10M",
            date="2024-06-15",
            investors=["Sequoia", "a16z"],
        )

        assert round.round_type == "Series A"
        assert round.amount == "$10M"
        assert round.date == "2024-06-15"
        assert round.investors == ["Sequoia", "a16z"]

    def test_creates_funding_round_with_optional_fields_none(self):
        """Should allow None for optional fields."""
        round = FundingRound(
            round_type="Seed",
            amount=None,
            date=None,
            investors=[],
        )

        assert round.round_type == "Seed"
        assert round.amount is None
        assert round.date is None
        assert round.investors == []


class TestProductUpdateModel:
    """Tests for ProductUpdate dataclass."""

    def test_creates_product_update_with_all_fields(self):
        """Should create ProductUpdate with all fields populated."""
        update = ProductUpdate(
            title="AI Feature Launch",
            date="2024-08-01",
            description="Launched new AI assistant feature",
            source_url="https://techcrunch.com/acme-ai",
        )

        assert update.title == "AI Feature Launch"
        assert update.date == "2024-08-01"
        assert update.description == "Launched new AI assistant feature"
        assert update.source_url == "https://techcrunch.com/acme-ai"

    def test_creates_product_update_with_optional_fields_none(self):
        """Should allow None for optional fields."""
        update = ProductUpdate(
            title="Minor Update",
            date=None,
            description="Small improvements",
            source_url=None,
        )

        assert update.title == "Minor Update"
        assert update.date is None
        assert update.source_url is None
