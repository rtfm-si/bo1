"""Market trend summary generator service using Brave Search + Claude Haiku.

Generates AI-powered industry trend summaries with:
- Executive summary of current market conditions
- Key trends (3-5 items)
- Opportunities (2-4 items)
- Threats/challenges (2-4 items)

Cost: ~$0.005/generation (search $0.003 + Haiku $0.002)
Refresh: Every 7 days or on industry change
"""

import asyncio
import html
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from bo1.config import get_settings
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.circuit_breaker import get_service_circuit_breaker
from bo1.llm.context import get_cost_context
from bo1.llm.cost_tracker import CostTracker
from bo1.logging.errors import ErrorCode, log_error
from bo1.prompts.sanitizer import sanitize_user_input

logger = logging.getLogger(__name__)


# Tier limits for forecast timeframe access
# 'now' is always available (handled by summary endpoint)
# Free: now only (no forecasts)
# Starter: now + 3m forecast
# Pro/Enterprise: now + all forecasts (3m, 12m, 24m)
TREND_FORECAST_TIER_LIMITS: dict[str, list[str]] = {
    "free": [],
    "starter": ["3m"],
    "pro": ["3m", "12m", "24m"],
    "enterprise": ["3m", "12m", "24m"],
}


def get_available_timeframes(tier: str) -> list[str]:
    """Get available forecast timeframes for a subscription tier."""
    return TREND_FORECAST_TIER_LIMITS.get(tier, ["3m"])


# System prompt for trend summary generation
TREND_SUMMARY_SYSTEM_PROMPT = """You are a market intelligence analyst generating executive summaries of industry trends.

Given search results about current trends in a specific industry, synthesize the information into a structured market intelligence report.

Your summary should include:
1. Executive summary - A 2-3 sentence overview of the current market landscape
2. Key trends - The 3-5 most important trends shaping the industry
3. Opportunities - 2-4 actionable opportunities for businesses in this space
4. Threats - 2-4 key challenges or risks to be aware of

IMPORTANT RULES:
- Be factual and evidence-based - cite trends from the search results
- Focus on ACTIONABLE insights relevant to business owners
- Keep language concise and business-focused
- Prioritize recent developments (2024-2025)
- Do not include generic advice - be specific to the industry
- Each key trend should be 1-2 sentences max
- Each opportunity/threat should be a brief bullet point

Output JSON object only - no markdown, no explanation:
{
  "summary": "2-3 sentence executive summary...",
  "key_trends": ["Trend 1 description", "Trend 2", "Trend 3"],
  "opportunities": ["Opportunity 1", "Opportunity 2"],
  "threats": ["Threat 1", "Threat 2"]
}"""


TIMEFRAME_LABELS: dict[str, str] = {
    "3m": "3 months",
    "12m": "12 months",
    "24m": "24 months",
}


def strip_html_to_text(html_content: str, max_chars: int = 10000) -> str:
    """Convert HTML to plain text by stripping tags and normalizing whitespace.

    Args:
        html_content: Raw HTML string
        max_chars: Maximum characters to return (default 10KB)

    Returns:
        Clean plain text
    """
    if not html_content:
        return ""

    # Remove script and style blocks completely
    text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Replace common block elements with newlines for readability
    text = re.sub(r"<(?:p|div|br|h[1-6]|li|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)

    # Strip all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    text = html.unescape(text)

    # Normalize whitespace: collapse multiple spaces/newlines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = text.strip()

    return text[:max_chars]


def build_trend_summary_prompt(
    industry: str,
    search_results: list[dict],
    timeframe: str = "3m",
) -> str:
    """Build user prompt for trend summary generation.

    Args:
        industry: User's industry
        search_results: List of Brave Search results with title, url, snippet, and optional content
        timeframe: Forecast horizon (3m, 12m, 24m)

    Returns:
        Formatted user prompt string
    """
    # Format search results for context
    formatted_results = []
    for i, result in enumerate(search_results[:10], 1):
        entry = (
            f"{i}. {result.get('title', 'No title')}\n"
            f"   URL: {result.get('url', 'N/A')}\n"
            f"   Snippet: {result.get('snippet', 'No description')}"
        )
        # Include extracted content if available (truncated to 1500 chars)
        content = result.get("content")
        if content:
            truncated = content[:1500]
            if len(content) > 1500:
                truncated += "..."
            entry += f"\n   Article Content:\n   {truncated}"
        formatted_results.append(entry)

    results_text = "\n\n".join(formatted_results)
    timeframe_label = TIMEFRAME_LABELS.get(timeframe, "3 months")

    return f"""Generate a market trend summary for the {industry} industry, focusing on the next {timeframe_label}.

Recent search results about "{industry} industry trends 2025":

{results_text}

Based on these search results, provide a structured market intelligence summary for business owners in the {industry} industry. Focus on developments and predictions relevant to the next {timeframe_label}. Provide actionable insights with appropriate time horizons.

Output JSON only."""


@dataclass
class TrendSummaryResult:
    """Result of trend summary generation."""

    summary: str | None = None
    key_trends: list[str] | None = None
    opportunities: list[str] | None = None
    threats: list[str] | None = None
    generated_at: datetime | None = None
    industry: str | None = None
    timeframe: str = "3m"  # 3m, 12m, 24m
    available_timeframes: list[str] | None = None  # UI hints for tier-gated access
    sources_enriched: int = 0  # Number of URLs with content successfully extracted
    status: str = "complete"  # complete, error, rate_limited
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/API response."""
        return {
            "summary": self.summary,
            "key_trends": self.key_trends or [],
            "opportunities": self.opportunities or [],
            "threats": self.threats or [],
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "industry": self.industry,
            "timeframe": self.timeframe,
            "available_timeframes": self.available_timeframes or ["3m"],
            "sources_enriched": self.sources_enriched,
        }


class TrendSummaryGenerator:
    """Generates AI-powered market trend summaries using Brave Search + Haiku."""

    MAX_KEY_TRENDS = 5
    MAX_OPPORTUNITIES = 4
    MAX_THREATS = 4
    SEARCH_TIMEOUT = 10.0
    CONTENT_FETCH_TIMEOUT = 5.0  # Per-URL timeout
    CONTENT_FETCH_TOTAL_TIMEOUT = 8.0  # Total batch timeout
    CONTENT_MAX_BYTES = 10000  # 10KB max per URL
    CONTENT_URLS_TO_FETCH = 3  # Top N URLs to enrich

    def __init__(self) -> None:
        """Initialize generator with lazy broker."""
        self._broker: PromptBroker | None = None
        self._settings = get_settings()

    def _get_broker(self) -> PromptBroker:
        """Lazy-initialize prompt broker."""
        if self._broker is None:
            self._broker = PromptBroker()
        return self._broker

    async def _fetch_url_content(self, url: str) -> str | None:
        """Fetch and extract text content from a URL.

        Args:
            url: URL to fetch content from

        Returns:
            Extracted plain text content, or None on failure
        """
        if not url:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    timeout=self.CONTENT_FETCH_TIMEOUT,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; Bo1Bot/1.0; +https://bo1.ai)",
                        "Accept": "text/html,application/xhtml+xml",
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()

                # Check content type - only process HTML
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    logger.debug(f"Skipping non-HTML content: {content_type} for {url[:50]}")
                    return None

                # Truncate raw content to limit
                raw_content = response.text[: self.CONTENT_MAX_BYTES]

                # Convert HTML to text
                text_content = strip_html_to_text(raw_content)

                # Minimum viable content check
                if len(text_content) < 100:
                    logger.debug(f"Content too short after extraction: {len(text_content)} chars")
                    return None

                return text_content

        except httpx.TimeoutException:
            logger.debug(f"Timeout fetching URL: {url[:50]}...")
            return None
        except httpx.HTTPStatusError as e:
            logger.debug(f"HTTP error {e.response.status_code} for URL: {url[:50]}...")
            return None
        except Exception as e:
            logger.debug(f"Failed to fetch URL content: {e}")
            return None

    async def _enrich_search_results(self, results: list[dict]) -> tuple[list[dict], int]:
        """Enrich top search results with extracted page content.

        Args:
            results: List of search results with title, url, snippet

        Returns:
            Tuple of (enriched results list, count of successfully enriched)
        """
        if not results:
            return results, 0

        # Select top N URLs to fetch
        urls_to_fetch = [
            r.get("url") for r in results[: self.CONTENT_URLS_TO_FETCH] if r.get("url")
        ]

        if not urls_to_fetch:
            return results, 0

        try:
            # Fetch all URLs in parallel with total timeout
            fetch_tasks = [self._fetch_url_content(url) for url in urls_to_fetch]
            contents = await asyncio.wait_for(
                asyncio.gather(*fetch_tasks, return_exceptions=True),
                timeout=self.CONTENT_FETCH_TOTAL_TIMEOUT,
            )

            # Attach content to results
            enriched_count = 0
            for i, content in enumerate(contents):
                if i < len(results) and isinstance(content, str) and content:
                    results[i]["content"] = content
                    enriched_count += 1

            logger.info(f"Enriched {enriched_count}/{len(urls_to_fetch)} URLs with content")
            return results, enriched_count

        except TimeoutError:
            logger.warning("Content extraction timed out")
            return results, 0
        except Exception as e:
            logger.warning(f"Content extraction failed: {e}")
            return results, 0

    async def generate_summary(
        self,
        industry: str,
        timeframe: str = "3m",
        available_timeframes: list[str] | None = None,
    ) -> TrendSummaryResult:
        """Generate a market trend summary for an industry.

        Args:
            industry: User's industry to analyze
            timeframe: Forecast horizon (3m, 12m, 24m)
            available_timeframes: List of timeframes available to user's tier

        Returns:
            TrendSummaryResult with summary or error
        """
        if not industry or len(industry.strip()) < 2:
            return TrendSummaryResult(
                status="error",
                error="Industry is required for trend summary generation",
            )

        # Validate timeframe
        if timeframe not in TIMEFRAME_LABELS:
            timeframe = "3m"

        # Sanitize industry input
        industry = sanitize_user_input(industry)[:200]

        # Step 1: Search for recent industry trends (timeframe-aware query)
        search_results = await self._brave_search(industry, timeframe)

        if not search_results:
            return TrendSummaryResult(
                industry=industry,
                timeframe=timeframe,
                available_timeframes=available_timeframes or ["3m"],
                status="error",
                error="Could not fetch industry trends - search API unavailable",
            )

        # Step 1.5: Enrich top results with extracted page content
        search_results, sources_enriched = await self._enrich_search_results(search_results)

        # Step 2: Generate summary using Claude Haiku
        user_prompt = build_trend_summary_prompt(industry, search_results, timeframe)

        try:
            broker = self._get_broker()
            request = PromptRequest(
                system=TREND_SUMMARY_SYSTEM_PROMPT,
                user_message=user_prompt,
                model="haiku",
                max_tokens=800,
                temperature=0.3,  # Lower temp for factual analysis
                agent_type="TrendSummaryGenerator",
                prompt_type="trend_summary",
            )

            response = await broker.call(request)
            result = self._parse_summary(
                response.text, industry, timeframe, available_timeframes, sources_enriched
            )
            return result

        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Trend summary generation failed: {e}",
                industry=industry,
            )
            return TrendSummaryResult(
                industry=industry,
                timeframe=timeframe,
                available_timeframes=available_timeframes or ["3m"],
                status="error",
                error=f"Summary generation failed: {e!s}",
            )

    async def _brave_search(self, industry: str, timeframe: str = "3m") -> list[dict]:
        """Search for industry trends using Brave Search API.

        Args:
            industry: Industry to search for
            timeframe: Forecast horizon (3m, 12m, 24m)

        Returns:
            List of search results with title, url, snippet
        """
        brave_api_key = self._settings.brave_api_key

        if not brave_api_key:
            logger.warning("BRAVE_API_KEY not set - trend summary unavailable")
            return []

        # Check circuit breaker
        breaker = get_service_circuit_breaker("brave")
        if breaker.state.value == "open":
            logger.warning("Brave circuit breaker is OPEN")
            return []

        # Get cost context
        ctx = get_cost_context()

        # Build timeframe-aware search query
        timeframe_suffix = {
            "3m": "short term outlook",
            "12m": "12 month forecast",
            "24m": "long term forecast 2025 2026",
        }.get(timeframe, "")

        try:
            query = f"{industry} industry trends 2025 {timeframe_suffix}".strip()

            with CostTracker.track_call(
                provider="brave",
                operation_type="web_search",
                session_id=ctx.get("session_id"),
                user_id=ctx.get("user_id"),
                node_name="trend_summary",
                prompt_type="search",
                metadata={"query": query[:100]},
            ):
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        headers={"X-Subscription-Token": brave_api_key},
                        params={
                            "q": query,
                            "count": 10,
                            "freshness": "py",  # Past year for freshness
                        },
                        timeout=self.SEARCH_TIMEOUT,
                    )
                    response.raise_for_status()
                    data = response.json()
                    breaker._record_success_sync()

            # Extract web results
            web_results = data.get("web", {}).get("results", [])
            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("description", ""),
                }
                for r in web_results
            ]

            logger.info(f"Brave search returned {len(results)} results for '{query}'")
            return results

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Brave Search rate limited")
                breaker._record_failure_sync()
            else:
                logger.error(f"Brave Search HTTP error: {e.response.status_code}")
                breaker._record_failure_sync()
            return []
        except Exception as e:
            logger.error(f"Brave Search failed: {e}")
            breaker._record_failure_sync()
            return []

    def _parse_summary(
        self,
        response_text: str,
        industry: str,
        timeframe: str = "3m",
        available_timeframes: list[str] | None = None,
        sources_enriched: int = 0,
    ) -> TrendSummaryResult:
        """Parse LLM response into TrendSummaryResult.

        Args:
            response_text: Raw LLM response (expected JSON object)
            industry: Industry for reference
            timeframe: Forecast horizon used for generation
            available_timeframes: Timeframes available to user's tier
            sources_enriched: Number of URLs with extracted content

        Returns:
            Parsed TrendSummaryResult
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

            return TrendSummaryResult(
                summary=self._safe_str(data.get("summary"), 1000),
                key_trends=self._safe_list(data.get("key_trends"), self.MAX_KEY_TRENDS),
                opportunities=self._safe_list(data.get("opportunities"), self.MAX_OPPORTUNITIES),
                threats=self._safe_list(data.get("threats"), self.MAX_THREATS),
                generated_at=datetime.now(UTC),
                industry=industry,
                timeframe=timeframe,
                available_timeframes=available_timeframes or ["3m"],
                sources_enriched=sources_enriched,
                status="complete",
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse trend summary: {e}")
            return TrendSummaryResult(
                industry=industry,
                timeframe=timeframe,
                available_timeframes=available_timeframes or ["3m"],
                sources_enriched=sources_enriched,
                status="error",
                error=f"Parse error: {e}",
            )

    def _safe_str(self, value: Any, max_len: int) -> str | None:
        """Safely convert value to string with length limit."""
        if value is None:
            return None
        return str(value)[:max_len] if value else None

    def _safe_list(self, value: Any, max_items: int) -> list[str]:
        """Safely convert value to list of strings."""
        if not value or not isinstance(value, list):
            return []
        return [str(item)[:300] for item in value[:max_items] if item]


# Module-level singleton
_generator: TrendSummaryGenerator | None = None


def get_trend_summary_generator() -> TrendSummaryGenerator:
    """Get or create the trend summary generator singleton."""
    global _generator
    if _generator is None:
        _generator = TrendSummaryGenerator()
    return _generator
