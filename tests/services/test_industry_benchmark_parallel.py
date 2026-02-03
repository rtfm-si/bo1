"""Tests for parallel search in IndustryBenchmarkResearcher.

Tests that Brave and Tavily searches run concurrently for improved latency.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from backend.services.industry_benchmark_researcher import IndustryBenchmarkResearcher


class TestParallelBenchmarkSearch:
    """Tests for parallel Brave/Tavily search execution."""

    @pytest.fixture
    def researcher(self):
        """Create researcher with mocked settings."""
        with patch("backend.services.industry_benchmark_researcher.get_settings") as mock_settings:
            settings = MagicMock()
            settings.brave_api_key = "test-brave-key"
            settings.tavily_api_key = "test-tavily-key"
            settings.anthropic_api_key = "test-anthropic-key"
            mock_settings.return_value = settings
            yield IndustryBenchmarkResearcher()

    @pytest.mark.asyncio
    async def test_searches_run_in_parallel(self, researcher):
        """Should run 2 Brave + 1 Tavily searches concurrently, not sequentially."""
        search_start_times = []
        search_end_times = []

        async def mock_brave_search(query, industry):
            search_start_times.append(("brave", asyncio.get_event_loop().time()))
            await asyncio.sleep(0.05)  # Simulate network delay
            search_end_times.append(("brave", asyncio.get_event_loop().time()))
            return [{"url": f"https://brave.com/{query[:10]}", "title": "Result"}]

        async def mock_tavily_search(query, industry):
            search_start_times.append(("tavily", asyncio.get_event_loop().time()))
            await asyncio.sleep(0.05)  # Simulate network delay
            search_end_times.append(("tavily", asyncio.get_event_loop().time()))
            return [{"url": f"https://tavily.com/{query[:10]}", "title": "Result"}]

        with patch.object(researcher, "_brave_search", side_effect=mock_brave_search):
            with patch.object(researcher, "_tavily_search", side_effect=mock_tavily_search):
                await researcher._search_industry_benchmarks("SaaS")

        # Should have 3 searches total
        assert len(search_start_times) == 3

        # All searches should start at approximately the same time (within 10ms)
        start_times = [t for _, t in search_start_times]
        assert max(start_times) - min(start_times) < 0.01

    @pytest.mark.asyncio
    async def test_deduplicates_results_by_url(self, researcher):
        """Should deduplicate results from parallel searches by URL."""

        async def mock_brave_search(query, industry):
            # Both Brave searches return the same URL
            return [
                {"url": "https://duplicate.com/benchmark", "title": "Duplicate"},
                {"url": f"https://unique-{query[:5]}.com", "title": "Unique"},
            ]

        async def mock_tavily_search(query, industry):
            return [
                {"url": "https://duplicate.com/benchmark", "title": "Duplicate"},
                {"url": "https://tavily-unique.com", "title": "Tavily Unique"},
            ]

        with patch.object(researcher, "_brave_search", side_effect=mock_brave_search):
            with patch.object(researcher, "_tavily_search", side_effect=mock_tavily_search):
                results = await researcher._search_industry_benchmarks("SaaS")

        # Should have deduplicated the duplicate URL
        urls = [r["url"] for r in results]
        assert urls.count("https://duplicate.com/benchmark") == 1

    @pytest.mark.asyncio
    async def test_handles_failed_search_gracefully(self, researcher):
        """Should continue with other results if one search fails."""

        async def mock_brave_search(query, industry):
            if "benchmarks" in query:
                raise Exception("Brave API error")
            return [{"url": "https://brave.com/result", "title": "Brave Result"}]

        async def mock_tavily_search(query, industry):
            return [{"url": "https://tavily.com/result", "title": "Tavily Result"}]

        with patch.object(researcher, "_brave_search", side_effect=mock_brave_search):
            with patch.object(researcher, "_tavily_search", side_effect=mock_tavily_search):
                results = await researcher._search_industry_benchmarks("SaaS")

        # Should have results from the non-failing searches
        assert len(results) >= 1
        urls = [r["url"] for r in results]
        assert "https://tavily.com/result" in urls

    @pytest.mark.asyncio
    async def test_handles_all_searches_failing(self, researcher):
        """Should return empty list if all searches fail."""

        async def mock_brave_search(query, industry):
            raise Exception("Brave API error")

        async def mock_tavily_search(query, industry):
            raise Exception("Tavily API error")

        with patch.object(researcher, "_brave_search", side_effect=mock_brave_search):
            with patch.object(researcher, "_tavily_search", side_effect=mock_tavily_search):
                results = await researcher._search_industry_benchmarks("SaaS")

        assert results == []
