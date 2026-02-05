"""Market trend insight analyzer service using Claude Haiku.

Generates AI-powered insights from market trend URLs with structured analysis.
Cost: ~$0.003/request (2K input + 800 output tokens at Haiku rates)

Provides:
- Key takeaway extraction
- Relevance to user's business
- Recommended actions
- Timeframe classification
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

import httpx

from bo1.config import get_settings
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.logging.errors import ErrorCode, log_error
from bo1.prompts.sanitizer import sanitize_user_input
from bo1.prompts.trend import TREND_SYSTEM_PROMPT, build_trend_prompt
from bo1.utils.json_parsing import parse_json_with_fallback

logger = logging.getLogger(__name__)

TimeframeType = Literal["immediate", "short_term", "long_term"]
ConfidenceType = Literal["high", "medium", "low"]


@dataclass
class TrendInsightResult:
    """Result of trend insight generation."""

    url: str
    title: str | None = None
    key_takeaway: str | None = None
    relevance: str | None = None
    actions: list[str] | None = None
    timeframe: TimeframeType | None = None
    confidence: ConfidenceType | None = None
    analyzed_at: datetime | None = None
    status: str = "complete"  # complete, cached, limited_data, error
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "url": self.url,
            "title": self.title,
            "key_takeaway": self.key_takeaway,
            "relevance": self.relevance,
            "actions": self.actions or [],
            "timeframe": self.timeframe,
            "confidence": self.confidence,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
        }


class TrendAnalyzer:
    """Analyzes market trend URLs and generates structured insights."""

    MAX_ACTIONS = 5
    FETCH_TIMEOUT = 30.0
    MAX_CONTENT_LENGTH = 10000

    def __init__(self) -> None:
        """Initialize analyzer with lazy broker."""
        self._broker: PromptBroker | None = None
        self._settings = get_settings()

    def _get_broker(self) -> PromptBroker:
        """Lazy-initialize prompt broker."""
        if self._broker is None:
            self._broker = PromptBroker()
        return self._broker

    async def analyze_trend(
        self,
        url: str,
        industry: str | None = None,
        product_description: str | None = None,
        business_model: str | None = None,
        target_market: str | None = None,
    ) -> TrendInsightResult:
        """Analyze a trend URL and generate structured insights.

        Args:
            url: URL of the trend article to analyze
            industry: User's industry for context
            product_description: User's product description
            business_model: User's business model
            target_market: User's target market

        Returns:
            TrendInsightResult with analysis or error
        """
        # Sanitize URL (basic validation)
        url = url.strip()[:2000]
        if not url.startswith(("http://", "https://")):
            return TrendInsightResult(
                url=url,
                status="error",
                error="Invalid URL: must start with http:// or https://",
            )

        # Sanitize context inputs
        if industry:
            industry = sanitize_user_input(industry)[:200]
        if product_description:
            product_description = sanitize_user_input(product_description)[:500]
        if business_model:
            business_model = sanitize_user_input(business_model)[:200]
        if target_market:
            target_market = sanitize_user_input(target_market)[:500]

        # Fetch URL content
        content, title = await self._fetch_url_content(url)

        # Build prompt
        user_prompt = build_trend_prompt(
            url=url,
            content=content,
            title=title,
            industry=industry,
            product_description=product_description,
            business_model=business_model,
            target_market=target_market,
        )

        try:
            broker = self._get_broker()
            request = PromptRequest(
                system=TREND_SYSTEM_PROMPT,
                user_message=user_prompt,
                model="haiku",
                max_tokens=1200,
                temperature=0.3,  # Lower temp for factual analysis
                agent_type="TrendAnalyzer",
                prompt_type="trend_insight",
            )

            response = await broker.call(request)
            result = self._parse_insight(response.text, url, title)

            # Mark as limited_data if content was not accessible
            if not content or len(content.strip()) < 100:
                result.status = "limited_data"

            return result

        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Trend insight generation failed: {e}",
                url=url,
            )
            return self._fallback_insight(url, title, str(e))

    async def _fetch_url_content(
        self,
        url: str,
    ) -> tuple[str | None, str | None]:
        """Fetch and extract text content from a URL.

        Args:
            url: URL to fetch

        Returns:
            Tuple of (content text, page title) or (None, None) if fetch fails
        """
        try:
            async with httpx.AsyncClient(
                timeout=self.FETCH_TIMEOUT,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; Bo1Bot/1.0; +https://boardof.one)"
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")

                # Skip non-HTML content
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    logger.info(f"Skipping non-HTML content type: {content_type}")
                    return None, None

                html = response.text

                # Extract title
                title = self._extract_title(html)

                # Extract text content (basic extraction)
                text = self._extract_text(html)

                return text, title

        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching URL: {url}")
            return None, None
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error fetching URL {url}: {e.response.status_code}")
            return None, None
        except Exception as e:
            logger.warning(f"Failed to fetch URL {url}: {e}")
            return None, None

    def _extract_title(self, html: str) -> str | None:
        """Extract page title from HTML."""
        import re

        # Try <title> tag
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()[:200]

        # Try og:title
        og_match = re.search(
            r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if og_match:
            return og_match.group(1).strip()[:200]

        return None

    def _extract_text(self, html: str) -> str:
        """Extract readable text content from HTML.

        Basic extraction that removes scripts, styles, and tags.
        For production, consider using readability-lxml or similar.
        """
        import re

        # Remove script and style elements
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML comments
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

        # Remove all tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Decode HTML entities
        import html

        text = html.unescape(text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        # Truncate to max length
        return text.strip()[: self.MAX_CONTENT_LENGTH]

    def _parse_insight(
        self,
        response_text: str,
        url: str,
        title: str | None,
    ) -> TrendInsightResult:
        """Parse LLM response into TrendInsightResult.

        Args:
            response_text: Raw LLM response (expected JSON object)
            url: Original URL for reference
            title: Page title if extracted

        Returns:
            Parsed TrendInsightResult
        """
        try:
            data, errors = parse_json_with_fallback(response_text, context="trend_analyzer")
            if data is None:
                raise ValueError(f"Parse error: {errors}")

            # Parse timeframe
            timeframe = data.get("timeframe")
            if timeframe not in ("immediate", "short_term", "long_term"):
                timeframe = "short_term"

            # Parse confidence
            confidence = data.get("confidence")
            if confidence not in ("high", "medium", "low"):
                confidence = "medium"

            return TrendInsightResult(
                url=url,
                title=self._safe_str(data.get("title"), 200) or title,
                key_takeaway=self._safe_str(data.get("key_takeaway"), 500),
                relevance=self._safe_str(data.get("relevance"), 500),
                actions=self._safe_list(data.get("actions"), self.MAX_ACTIONS),
                timeframe=timeframe,
                confidence=confidence,
                analyzed_at=datetime.now(UTC),
                status="complete",
            )

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse trend insight: {e}")
            return self._fallback_insight(url, title, f"Parse error: {e}")

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

    def _fallback_insight(
        self,
        url: str,
        title: str | None,
        error: str,
    ) -> TrendInsightResult:
        """Return minimal fallback insight when analysis fails.

        Args:
            url: Original URL
            title: Page title if available
            error: Error message

        Returns:
            Minimal TrendInsightResult with error status
        """
        return TrendInsightResult(
            url=url,
            title=title,
            key_takeaway=None,
            relevance=None,
            actions=[],
            timeframe=None,
            confidence="low",
            analyzed_at=datetime.now(UTC),
            status="error",
            error=error,
        )


# Module-level singleton
_analyzer: TrendAnalyzer | None = None


def get_trend_analyzer() -> TrendAnalyzer:
    """Get or create the trend analyzer singleton."""
    global _analyzer
    if _analyzer is None:
        _analyzer = TrendAnalyzer()
    return _analyzer
