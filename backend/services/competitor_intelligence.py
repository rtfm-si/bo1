"""Competitor Intelligence Service.

Gathers deeper intelligence on competitors using multi-query Tavily search:
- Funding rounds (Crunchbase, TechCrunch)
- Product updates (press, blogs)
- Recent news coverage
- Key signals

Pro tier only. Cost: ~$0.01 per competitor (3 queries + LLM parsing).
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from bo1.config import get_settings
from bo1.llm.client import ClaudeClient
from bo1.logging.errors import ErrorCode, log_error

logger = logging.getLogger(__name__)


@dataclass
class ProductUpdate:
    """A product update or launch."""

    title: str
    date: str | None
    description: str
    source_url: str | None


@dataclass
class FundingRound:
    """A funding round."""

    round_type: str  # e.g., "Series A", "Seed"
    amount: str | None  # e.g., "$10M"
    date: str | None
    investors: list[str]


@dataclass
class CompetitorIntel:
    """Intelligence gathered about a competitor."""

    name: str
    funding_rounds: list[FundingRound]
    product_updates: list[ProductUpdate]
    recent_news: list[dict[str, str]]  # [{title, date, source_url}]
    key_signals: list[str]  # Notable signals like "Raised Series B", "Launched AI feature"
    gathered_at: datetime


class CompetitorIntelligenceService:
    """Service for gathering deep competitor intelligence."""

    def __init__(self) -> None:
        """Initialize the competitor intelligence service."""
        self.settings = get_settings()

    async def gather_competitor_intel(
        self,
        name: str,
        website: str | None = None,
    ) -> CompetitorIntel | None:
        """Gather comprehensive intelligence on a competitor.

        Performs 3 Tavily searches:
        1. Funding/investment news
        2. Product launches/updates
        3. Recent news coverage

        Then uses Haiku to parse results into structured intelligence.

        Args:
            name: Competitor company name
            website: Optional website URL for better search context

        Returns:
            CompetitorIntel with structured data, or None on failure
        """
        if not self.settings.tavily_api_key:
            logger.warning("Tavily API key not configured for competitor intelligence")
            return None

        logger.info(f"Gathering intelligence for competitor: {name}")

        # Run all 3 searches in parallel
        try:
            funding_results, product_results, news_results = await asyncio.gather(
                self._search_funding(name),
                self._search_product_updates(name),
                self._search_recent_news(name),
                return_exceptions=True,
            )

            # Handle any failed searches gracefully
            if isinstance(funding_results, Exception):
                logger.warning(f"Funding search failed for {name}: {funding_results}")
                funding_results = []
            if isinstance(product_results, Exception):
                logger.warning(f"Product search failed for {name}: {product_results}")
                product_results = []
            if isinstance(news_results, Exception):
                logger.warning(f"News search failed for {name}: {news_results}")
                news_results = []

            # Parse combined results with LLM
            intel = await self._parse_intel_with_llm(
                name=name,
                funding_results=funding_results,
                product_results=product_results,
                news_results=news_results,
            )

            return intel

        except asyncio.CancelledError:
            raise
        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Failed to gather intel for {name}: {e}",
                competitor_name=name,
            )
            return None

    async def _search_funding(self, name: str) -> list[dict]:
        """Search for funding/investment news."""
        query = f'"{name}" funding OR raised OR series OR investment'

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.settings.tavily_api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "include_domains": [
                        "crunchbase.com",
                        "techcrunch.com",
                        "venturebeat.com",
                        "businessinsider.com",
                        "forbes.com",
                    ],
                    "max_results": 5,
                },
            )
            response.raise_for_status()
            data = response.json()

        return data.get("results", [])

    async def _search_product_updates(self, name: str) -> list[dict]:
        """Search for product launches and updates."""
        query = f'"{name}" product launch OR release OR update OR feature'

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.settings.tavily_api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "include_domains": [
                        "producthunt.com",
                        "techcrunch.com",
                        "theverge.com",
                        "venturebeat.com",
                    ],
                    "max_results": 5,
                },
            )
            response.raise_for_status()
            data = response.json()

        return data.get("results", [])

    async def _search_recent_news(self, name: str) -> list[dict]:
        """Search for recent news coverage."""
        # Use current year for freshness
        current_year = datetime.now(UTC).year
        query = f'"{name}" news {current_year}'

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.settings.tavily_api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 5,
                },
            )
            response.raise_for_status()
            data = response.json()

        return data.get("results", [])

    async def _parse_intel_with_llm(
        self,
        name: str,
        funding_results: list[dict],
        product_results: list[dict],
        news_results: list[dict],
    ) -> CompetitorIntel:
        """Parse search results into structured intelligence using Haiku."""
        # Build context from all results
        context_parts = []

        if funding_results:
            context_parts.append("=== FUNDING NEWS ===")
            for r in funding_results[:5]:
                context_parts.append(
                    f"Title: {r.get('title', '')}\n"
                    f"URL: {r.get('url', '')}\n"
                    f"Content: {r.get('content', '')[:400]}"
                )

        if product_results:
            context_parts.append("\n=== PRODUCT UPDATES ===")
            for r in product_results[:5]:
                context_parts.append(
                    f"Title: {r.get('title', '')}\n"
                    f"URL: {r.get('url', '')}\n"
                    f"Content: {r.get('content', '')[:400]}"
                )

        if news_results:
            context_parts.append("\n=== RECENT NEWS ===")
            for r in news_results[:5]:
                context_parts.append(
                    f"Title: {r.get('title', '')}\n"
                    f"URL: {r.get('url', '')}\n"
                    f"Content: {r.get('content', '')[:400]}"
                )

        context = "\n\n".join(context_parts)

        if not context.strip():
            # No results found
            return CompetitorIntel(
                name=name,
                funding_rounds=[],
                product_updates=[],
                recent_news=[],
                key_signals=[],
                gathered_at=datetime.now(UTC),
            )

        prompt = f"""Analyze these search results about "{name}" and extract structured intelligence.

{context}

Extract and return a JSON object with:
1. "funding_rounds": Array of funding events with {{round_type, amount, date, investors[]}}
2. "product_updates": Array of product news with {{title, date, description, source_url}}
3. "recent_news": Array of general news with {{title, date, source_url}}
4. "key_signals": Array of 3-5 notable signals (short phrases like "Raised Series B", "Launched AI feature", "Expanding to Europe")

Rules:
- Only include information directly about "{name}", not competitors mentioned in articles
- For dates, use YYYY-MM-DD format or null if unclear
- For funding amounts, include currency symbol (e.g., "$10M")
- Key signals should be actionable insights for a competitor analysis
- If no data found for a category, use empty array

Return ONLY valid JSON, no other text.
"""

        try:
            client = ClaudeClient()
            response, _ = await client.call(
                model="haiku",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500,
                prefill="{",
            )

            # Parse JSON response
            try:
                parsed = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r"\{[\s\S]*\}", response)
                if json_match:
                    parsed = json.loads(json_match.group())
                else:
                    logger.warning(f"Failed to parse LLM intel response: {response[:200]}")
                    parsed = {}

            # Build structured response
            funding_rounds = []
            for fr in parsed.get("funding_rounds", []):
                funding_rounds.append(
                    FundingRound(
                        round_type=fr.get("round_type", "Unknown"),
                        amount=fr.get("amount"),
                        date=fr.get("date"),
                        investors=fr.get("investors", []),
                    )
                )

            product_updates = []
            for pu in parsed.get("product_updates", []):
                product_updates.append(
                    ProductUpdate(
                        title=pu.get("title", ""),
                        date=pu.get("date"),
                        description=pu.get("description", ""),
                        source_url=pu.get("source_url"),
                    )
                )

            recent_news = parsed.get("recent_news", [])
            key_signals = parsed.get("key_signals", [])

            return CompetitorIntel(
                name=name,
                funding_rounds=funding_rounds,
                product_updates=product_updates,
                recent_news=recent_news,
                key_signals=key_signals,
                gathered_at=datetime.now(UTC),
            )

        except asyncio.CancelledError:
            raise
        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"LLM intel parsing failed for {name}: {e}",
            )
            # Return empty intel on parse failure
            return CompetitorIntel(
                name=name,
                funding_rounds=[],
                product_updates=[],
                recent_news=[],
                key_signals=[],
                gathered_at=datetime.now(UTC),
            )


def intel_to_dict(intel: CompetitorIntel) -> dict:
    """Convert CompetitorIntel to dict for JSON storage."""
    return {
        "funding_rounds": [
            {
                "round_type": fr.round_type,
                "amount": fr.amount,
                "date": fr.date,
                "investors": fr.investors,
            }
            for fr in intel.funding_rounds
        ],
        "product_updates": [
            {
                "title": pu.title,
                "date": pu.date,
                "description": pu.description,
                "source_url": pu.source_url,
            }
            for pu in intel.product_updates
        ],
        "recent_news": intel.recent_news,
        "key_signals": intel.key_signals,
        "gathered_at": intel.gathered_at.isoformat() if intel.gathered_at else None,
    }
