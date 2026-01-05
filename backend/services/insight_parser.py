"""Insight parser service using Claude Haiku.

Parses free-form user insights into structured format with:
- Metric extraction (value, unit, type)
- Category classification (revenue, growth, team, operations, etc.)
- Confidence scoring

Uses Haiku for fast, cheap (~$0.0001/insight) parsing.
"""

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from bo1.llm.client import ClaudeClient

logger = logging.getLogger(__name__)

# Responses that indicate "no answer" rather than meaningful content
# Note: These must appear as the ENTIRE response (after normalization), not as substrings
_INVALID_RESPONSE_PATTERNS = frozenset(
    {
        "none",
        "n/a",
        "na",
        "no",
        "not applicable",
        "not available",
        "nothing",
        "null",
        "unknown",
        "skip",
        "skipped",
        "-",
        "—",
        "...",
        ".",
    }
)

# Minimum length for a valid insight response (characters, after strip)
_MIN_INSIGHT_LENGTH = 5


def is_valid_insight_response(text: str | None) -> bool:
    """Check if an insight response contains meaningful content.

    Rejects null/empty responses and common "no answer" patterns.
    Allows "none" in context (e.g., "none of the above apply because...").

    Args:
        text: The insight response text to validate

    Returns:
        True if the response is valid and should be stored, False otherwise
    """
    if text is None:
        return False

    # Strip and normalize
    normalized = text.strip().lower()

    # Reject empty or whitespace-only
    if not normalized:
        return False

    # Reject if too short (single word non-answers)
    if len(normalized) < _MIN_INSIGHT_LENGTH:
        # Check if it's a known invalid pattern
        if normalized in _INVALID_RESPONSE_PATTERNS:
            return False

    # Check for exact match with invalid patterns
    if normalized in _INVALID_RESPONSE_PATTERNS:
        return False

    # Check if it's JUST the invalid pattern (with possible punctuation)
    # e.g., "none.", "n/a!", "not applicable."
    normalized_no_punct = normalized.rstrip(".,!?;:")
    if normalized_no_punct in _INVALID_RESPONSE_PATTERNS:
        return False

    # Valid: longer responses that contain "none" in context
    # e.g., "none of the above apply because..." is valid
    # e.g., "we have none at the moment but planning to add" is valid
    return True


class InsightCategory(str, Enum):
    """Business insight categories."""

    REVENUE = "revenue"
    GROWTH = "growth"
    CUSTOMERS = "customers"
    TEAM = "team"
    PRODUCT = "product"
    OPERATIONS = "operations"
    MARKET = "market"
    COMPETITION = "competition"
    FUNDING = "funding"
    COSTS = "costs"
    # D2C/Product-specific categories
    INVENTORY = "inventory"
    MARGIN = "margin"
    CONVERSION = "conversion"
    AOV = "aov"
    COGS = "cogs"
    RETURNS = "returns"
    UNCATEGORIZED = "uncategorized"


@dataclass
class InsightMetric:
    """Extracted metric from insight."""

    value: float | None = None
    unit: str | None = None  # USD, %, count, etc.
    metric_type: str | None = None  # MRR, ARR, churn, etc.
    period: str | None = None  # monthly, yearly, etc.
    raw_text: str | None = None  # Original metric text


@dataclass
class StructuredInsight:
    """Structured representation of a user insight."""

    raw_text: str
    category: InsightCategory
    metric: InsightMetric | None
    confidence_score: float  # 0.0 - 1.0
    summary: str | None = None  # Brief one-liner
    key_entities: list[str] | None = None  # Products, competitors, etc.
    parsed_at: str | None = None  # ISO timestamp

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        result = {
            "raw_text": self.raw_text,
            "category": self.category.value,
            "confidence_score": self.confidence_score,
        }
        if self.metric:
            result["metric"] = {
                "value": self.metric.value,
                "unit": self.metric.unit,
                "metric_type": self.metric.metric_type,
                "period": self.metric.period,
                "raw_text": self.metric.raw_text,
            }
        if self.summary:
            result["summary"] = self.summary
        if self.key_entities:
            result["key_entities"] = self.key_entities
        if self.parsed_at:
            result["parsed_at"] = self.parsed_at
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StructuredInsight":
        """Create from dictionary."""
        metric = None
        if data.get("metric"):
            m = data["metric"]
            metric = InsightMetric(
                value=m.get("value"),
                unit=m.get("unit"),
                metric_type=m.get("metric_type"),
                period=m.get("period"),
                raw_text=m.get("raw_text"),
            )

        return cls(
            raw_text=data.get("raw_text", ""),
            category=InsightCategory(data.get("category", "uncategorized")),
            metric=metric,
            confidence_score=data.get("confidence_score", 0.5),
            summary=data.get("summary"),
            key_entities=data.get("key_entities"),
            parsed_at=data.get("parsed_at"),
        )


class InsightParser:
    """Parses user insights using Claude Haiku."""

    def __init__(self) -> None:
        """Initialize parser with lazy Claude client."""
        self._client: ClaudeClient | None = None

    def _get_client(self) -> ClaudeClient:
        """Lazy-initialize Claude client."""
        if self._client is None:
            self._client = ClaudeClient()
        return self._client

    async def parse_insight(self, raw_text: str) -> StructuredInsight:
        """Parse a free-form insight into structured format.

        Args:
            raw_text: User-provided insight text

        Returns:
            StructuredInsight with extracted category, metrics, etc.
        """
        from datetime import UTC, datetime

        if not raw_text or not raw_text.strip():
            return StructuredInsight(
                raw_text=raw_text or "",
                category=InsightCategory.UNCATEGORIZED,
                metric=None,
                confidence_score=0.0,
                parsed_at=datetime.now(UTC).isoformat(),
            )

        # Try LLM parsing first
        try:
            result = await self._parse_with_llm(raw_text)
            result.parsed_at = datetime.now(UTC).isoformat()
            return result
        except Exception as e:
            logger.warning(f"LLM parsing failed, using fallback: {e}")
            # Fall back to rule-based parsing
            return self._fallback_parse(raw_text)

    async def _parse_with_llm(self, raw_text: str) -> StructuredInsight:
        """Parse insight using Claude Haiku."""
        prompt = f"""Parse this business insight into structured format.

Insight: "{raw_text}"

Return JSON with:
- category: one of [revenue, growth, customers, team, product, operations, market, competition, funding, costs, uncategorized]
- metric: {{value: number|null, unit: "USD"|"%"|"count"|null, metric_type: string|null, period: "monthly"|"yearly"|"quarterly"|null, raw_text: string|null}} or null
- confidence: 0.0-1.0 (how confident in the categorization/extraction)
- summary: brief one-line summary (max 100 chars)
- key_entities: list of proper nouns, products, competitors mentioned

Examples:
Input: "Monthly revenue is $25,000"
Output: {{"category": "revenue", "metric": {{"value": 25000, "unit": "USD", "metric_type": "MRR", "period": "monthly", "raw_text": "$25,000"}}, "confidence": 0.95, "summary": "Monthly revenue of $25K", "key_entities": []}}

Input: "Team grew to 5 people last month"
Output: {{"category": "team", "metric": {{"value": 5, "unit": "count", "metric_type": "headcount", "period": null, "raw_text": "5 people"}}, "confidence": 0.9, "summary": "Team size increased to 5", "key_entities": []}}

Input: "We compete with Asana and Monday.com"
Output: {{"category": "competition", "metric": null, "confidence": 0.85, "summary": "Competes with Asana and Monday.com", "key_entities": ["Asana", "Monday.com"]}}

Return ONLY valid JSON, no other text."""

        client = self._get_client()
        response, _ = await client.call(
            model="haiku",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
            prefill="{",
        )

        # Parse JSON response
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.error(f"Failed to parse Haiku response: {response[:200]}")
                raise ValueError("Failed to parse LLM response as JSON") from None

        # Build StructuredInsight from parsed data
        metric = None
        if data.get("metric"):
            m = data["metric"]
            metric = InsightMetric(
                value=m.get("value"),
                unit=m.get("unit"),
                metric_type=m.get("metric_type"),
                period=m.get("period"),
                raw_text=m.get("raw_text"),
            )

        category_str = data.get("category", "uncategorized").lower()
        try:
            category = InsightCategory(category_str)
        except ValueError:
            category = InsightCategory.UNCATEGORIZED

        return StructuredInsight(
            raw_text=raw_text,
            category=category,
            metric=metric,
            confidence_score=data.get("confidence", 0.5),
            summary=data.get("summary"),
            key_entities=data.get("key_entities"),
        )

    def _fallback_parse(self, raw_text: str) -> StructuredInsight:
        """Rule-based fallback parser when LLM fails."""
        from datetime import UTC, datetime

        text_lower = raw_text.lower()
        category = InsightCategory.UNCATEGORIZED
        metric = None

        # Category detection rules (order matters - more specific first)
        if any(w in text_lower for w in ["revenue", "mrr", "arr", "income", "sales"]):
            category = InsightCategory.REVENUE
        elif any(w in text_lower for w in ["team", "employee", "hire", "staff"]):
            category = InsightCategory.TEAM
        elif " people" in text_lower and not any(w in text_lower for w in ["customer", "user"]):
            # "people" alone often means team, but "people use our product" is customers
            category = InsightCategory.TEAM
        elif any(w in text_lower for w in ["growth", "increase", "growing"]):
            category = InsightCategory.GROWTH
        elif "grew" in text_lower and "team" not in text_lower:
            category = InsightCategory.GROWTH
        elif any(w in text_lower for w in ["customer", "user", "client", "subscriber"]):
            category = InsightCategory.CUSTOMERS
        elif any(w in text_lower for w in ["product", "feature", "launch", "release"]):
            category = InsightCategory.PRODUCT
        elif any(w in text_lower for w in ["compete", "competitor", "vs", "versus"]):
            category = InsightCategory.COMPETITION
        elif any(w in text_lower for w in ["market", "industry", "sector"]):
            category = InsightCategory.MARKET
        elif any(w in text_lower for w in ["funding", "raise", "investment", "investor"]):
            category = InsightCategory.FUNDING
        elif any(w in text_lower for w in ["cost", "expense", "spend", "budget"]):
            category = InsightCategory.COSTS
        elif any(w in text_lower for w in ["operation", "process", "workflow"]):
            category = InsightCategory.OPERATIONS

        # Try to extract numeric values with currency
        # Match $X, $X.XX, $XK, $X.XK, $XM, $X.XM formats
        currency_match = re.search(r"\$[\d,]+(?:\.\d+)?(?:k|K|m|M)?", raw_text)
        if currency_match:
            raw_value = currency_match.group()
            # Parse value
            value_str = raw_value.replace("$", "").replace(",", "")
            multiplier = 1
            if value_str.endswith(("k", "K")):
                multiplier = 1000
                value_str = value_str[:-1]
            elif value_str.endswith(("m", "M")):
                multiplier = 1_000_000
                value_str = value_str[:-1]
            try:
                value = float(value_str) * multiplier
                metric = InsightMetric(
                    value=value,
                    unit="USD",
                    metric_type="MRR" if "monthly" in text_lower else "revenue",
                    period="monthly" if "month" in text_lower else None,
                    raw_text=raw_value,
                )
            except ValueError:
                pass

        # Try to extract percentage
        if not metric:
            pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", raw_text)
            if pct_match:
                try:
                    value = float(pct_match.group(1))
                    metric = InsightMetric(
                        value=value,
                        unit="%",
                        metric_type="rate",
                        raw_text=pct_match.group(),
                    )
                except ValueError:
                    pass

        # Try to extract plain numbers with context
        if not metric:
            num_match = re.search(r"(\d+)\s*(people|employees|customers|users)", text_lower)
            if num_match:
                try:
                    value = float(num_match.group(1))
                    metric = InsightMetric(
                        value=value,
                        unit="count",
                        metric_type=num_match.group(2),
                        raw_text=num_match.group(),
                    )
                except ValueError:
                    pass

        return StructuredInsight(
            raw_text=raw_text,
            category=category,
            metric=metric,
            confidence_score=0.4 if category != InsightCategory.UNCATEGORIZED else 0.2,
            parsed_at=datetime.now(UTC).isoformat(),
        )


# Module-level singleton for convenience
_parser: InsightParser | None = None


def get_insight_parser() -> InsightParser:
    """Get or create insight parser singleton."""
    global _parser
    if _parser is None:
        _parser = InsightParser()
    return _parser


async def parse_insight(raw_text: str) -> StructuredInsight:
    """Convenience function to parse an insight.

    Args:
        raw_text: User-provided insight text

    Returns:
        StructuredInsight with extracted category, metrics, etc.
    """
    parser = get_insight_parser()
    return await parser.parse_insight(raw_text)
