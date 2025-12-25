"""Competitor insight analyzer service using Claude Haiku.

Generates AI-powered competitor insight cards with structured analysis.
Cost: ~$0.003/request (2K input + 800 output tokens at Haiku rates)

Provides:
- Company identification (tagline, size, revenue estimates)
- Strengths and weaknesses analysis
- Market gaps and opportunities
- Web search integration for fresh data
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from bo1.config import get_settings
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.logging.errors import ErrorCode, log_error
from bo1.prompts.competitor import COMPETITOR_SYSTEM_PROMPT, build_competitor_prompt
from bo1.prompts.sanitizer import sanitize_user_input

logger = logging.getLogger(__name__)


@dataclass
class CompetitorInsightResult:
    """Result of competitor insight generation."""

    name: str
    tagline: str | None = None
    size_estimate: str | None = None
    revenue_estimate: str | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    market_gaps: list[str] | None = None
    last_updated: datetime | None = None
    status: str = "complete"  # complete, cached, limited_data, error
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "name": self.name,
            "tagline": self.tagline,
            "size_estimate": self.size_estimate,
            "revenue_estimate": self.revenue_estimate,
            "strengths": self.strengths or [],
            "weaknesses": self.weaknesses or [],
            "market_gaps": self.market_gaps or [],
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class CompetitorInsightAnalyzer:
    """Analyzes competitors and generates structured insight cards."""

    MAX_STRENGTHS = 5
    MAX_WEAKNESSES = 5
    MAX_GAPS = 5

    def __init__(self) -> None:
        """Initialize analyzer with lazy broker."""
        self._broker: PromptBroker | None = None
        self._settings = get_settings()

    def _get_broker(self) -> PromptBroker:
        """Lazy-initialize prompt broker."""
        if self._broker is None:
            self._broker = PromptBroker()
        return self._broker

    async def generate_insight(
        self,
        competitor_name: str,
        industry: str | None = None,
        product_description: str | None = None,
        value_proposition: str | None = None,
    ) -> CompetitorInsightResult:
        """Generate structured insight for a competitor.

        Args:
            competitor_name: Name of competitor to analyze
            industry: User's industry for context
            product_description: User's product description
            value_proposition: User's main value proposition

        Returns:
            CompetitorInsightResult with analysis or error
        """
        # Sanitize inputs
        competitor_name = sanitize_user_input(competitor_name)[:100]
        if industry:
            industry = sanitize_user_input(industry)[:200]
        if product_description:
            product_description = sanitize_user_input(product_description)[:500]
        if value_proposition:
            value_proposition = sanitize_user_input(value_proposition)[:500]

        # Try web search for fresh data
        search_results = await self._search_competitor(competitor_name)

        # Build prompt
        user_prompt = build_competitor_prompt(
            competitor_name=competitor_name,
            industry=industry,
            product_description=product_description,
            value_proposition=value_proposition,
            search_results=search_results,
        )

        try:
            broker = self._get_broker()
            request = PromptRequest(
                system=COMPETITOR_SYSTEM_PROMPT,
                user_message=user_prompt,
                model="haiku",
                max_tokens=1200,
                temperature=0.3,  # Lower temp for factual analysis
                agent_type="CompetitorAnalyzer",
                prompt_type="competitor_insight",
            )

            response = await broker.call(request)
            result = self._parse_insight(response.text, competitor_name)

            # Mark as limited_data if no search results
            if not search_results:
                result.status = "limited_data"

            return result

        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Competitor insight generation failed: {e}",
                competitor=competitor_name,
            )
            return self._fallback_insight(competitor_name, str(e))

    async def _search_competitor(
        self,
        competitor_name: str,
    ) -> list[dict[str, Any]] | None:
        """Search for competitor information using Tavily.

        Args:
            competitor_name: Name of competitor to search

        Returns:
            List of search results or None if search fails
        """
        if not self._settings.tavily_api_key:
            logger.debug("No Tavily API key, skipping search")
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self._settings.tavily_api_key,
                        "query": f'"{competitor_name}" company products pricing revenue',
                        "search_depth": "basic",
                        "max_results": 5,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("results", [])

        except Exception as e:
            logger.warning(f"Competitor search failed for {competitor_name}: {e}")
            return None

    def _parse_insight(
        self,
        response_text: str,
        competitor_name: str,
    ) -> CompetitorInsightResult:
        """Parse LLM response into CompetitorInsightResult.

        Args:
            response_text: Raw LLM response (expected JSON object)
            competitor_name: Original competitor name for fallback

        Returns:
            Parsed CompetitorInsightResult
        """
        try:
            # Strip any markdown wrapping
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("Expected JSON object")

            return CompetitorInsightResult(
                name=str(data.get("name", competitor_name))[:100],
                tagline=self._safe_str(data.get("tagline"), 200),
                size_estimate=self._safe_str(data.get("size_estimate"), 100),
                revenue_estimate=self._safe_str(data.get("revenue_estimate"), 100),
                strengths=self._safe_list(data.get("strengths"), self.MAX_STRENGTHS),
                weaknesses=self._safe_list(data.get("weaknesses"), self.MAX_WEAKNESSES),
                market_gaps=self._safe_list(data.get("market_gaps"), self.MAX_GAPS),
                last_updated=datetime.now(UTC),
                status="complete",
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse competitor insight: {e}")
            return self._fallback_insight(competitor_name, f"Parse error: {e}")

    def _safe_str(self, value: Any, max_len: int) -> str | None:
        """Safely convert value to string with length limit."""
        if value is None:
            return None
        return str(value)[:max_len] if value else None

    def _safe_list(self, value: Any, max_items: int) -> list[str]:
        """Safely convert value to list of strings."""
        if not value or not isinstance(value, list):
            return []
        return [str(item)[:200] for item in value[:max_items] if item]

    def _fallback_insight(
        self,
        competitor_name: str,
        error: str,
    ) -> CompetitorInsightResult:
        """Return minimal fallback insight when analysis fails.

        Args:
            competitor_name: Original competitor name
            error: Error message

        Returns:
            Minimal CompetitorInsightResult with error status
        """
        return CompetitorInsightResult(
            name=competitor_name,
            tagline=None,
            size_estimate=None,
            revenue_estimate=None,
            strengths=[],
            weaknesses=[],
            market_gaps=[],
            last_updated=datetime.now(UTC),
            status="error",
            error=error,
        )


# Module-level singleton
_analyzer: CompetitorInsightAnalyzer | None = None


def get_competitor_analyzer() -> CompetitorInsightAnalyzer:
    """Get or create the competitor analyzer singleton."""
    global _analyzer
    if _analyzer is None:
        _analyzer = CompetitorInsightAnalyzer()
    return _analyzer
