"""Metric keyword mapping and insight-to-metric matcher.

Maps insights to business_metrics using:
- Category matching (InsightCategory → metric_key)
- Keyword presence in question/answer text
- Value pattern extraction confidence
"""

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.api.context.models import InsightCategory

logger = logging.getLogger(__name__)


@dataclass
class MetricMatch:
    """A matched metric suggestion from an insight."""

    metric_key: str
    suggested_value: str | float
    confidence: float
    source_question: str
    source_answer: str
    answered_at: datetime | None


# =============================================================================
# Metric Keyword Definitions
# =============================================================================

# Maps metric_key → {keywords, category, value_patterns}
METRIC_KEYWORDS: dict[str, dict[str, Any]] = {
    "mrr": {
        "keywords": [
            "monthly recurring",
            "mrr",
            "subscription revenue",
            "monthly revenue",
            "recurring revenue",
        ],
        "category": InsightCategory.REVENUE,
        "value_patterns": [
            r"\$[\d,]+(?:\.\d{2})?\s*(?:/mo|per month|monthly|mrr)?",
            r"[\d,]+(?:\.\d{2})?\s*(?:usd|dollars?)?\s*(?:/mo|per month|monthly)",
        ],
        "unit": "$",
    },
    "arr": {
        "keywords": [
            "annual recurring",
            "arr",
            "yearly revenue",
            "annual revenue",
        ],
        "category": InsightCategory.REVENUE,
        "value_patterns": [
            r"\$[\d,]+(?:\.\d{2})?\s*(?:/yr|per year|annually|arr)?",
            r"[\d,]+k?\s*arr",
        ],
        "unit": "$",
    },
    "burn_rate": {
        "keywords": [
            "burn rate",
            "monthly burn",
            "cash burn",
            "spending rate",
            "monthly expenses",
        ],
        "category": InsightCategory.COSTS,
        "value_patterns": [
            r"\$[\d,]+(?:\.\d{2})?\s*(?:/mo|per month|monthly)?",
            r"burning\s*\$?[\d,]+",
        ],
        "unit": "$",
    },
    "runway": {
        "keywords": [
            "runway",
            "months of cash",
            "cash runway",
            "time before funding",
        ],
        "category": InsightCategory.FUNDING,
        "value_patterns": [
            r"(\d+)\s*(?:months?|mo)",
            r"runway\s*(?:of|is)?\s*(\d+)",
        ],
        "unit": "months",
    },
    "gross_margin": {
        "keywords": [
            "gross margin",
            "margin",
            "profit margin",
            "gross profit",
        ],
        "category": InsightCategory.REVENUE,
        "value_patterns": [
            r"(\d+(?:\.\d+)?)\s*%",
            r"margin\s*(?:of|is)?\s*(\d+)",
        ],
        "unit": "%",
    },
    "churn": {
        "keywords": [
            "churn",
            "churn rate",
            "customer churn",
            "cancellation rate",
            "attrition",
        ],
        "category": InsightCategory.CUSTOMERS,
        "value_patterns": [
            r"(\d+(?:\.\d+)?)\s*%",
            r"churn\s*(?:of|is|rate)?\s*(\d+(?:\.\d+)?)",
        ],
        "unit": "%",
    },
    "nps": {
        "keywords": [
            "nps",
            "net promoter",
            "promoter score",
            "customer satisfaction",
        ],
        "category": InsightCategory.CUSTOMERS,
        "value_patterns": [
            r"nps\s*(?:of|is|score)?\s*(-?\d+)",
            r"score\s*(?:of|is)?\s*(-?\d+)",
        ],
        "unit": "score",
    },
    "cac": {
        "keywords": [
            "cac",
            "customer acquisition cost",
            "acquisition cost",
            "cost per customer",
            "cost to acquire",
        ],
        "category": InsightCategory.COSTS,
        "value_patterns": [
            r"\$[\d,]+(?:\.\d{2})?",
            r"cac\s*(?:of|is)?\s*\$?(\d+)",
        ],
        "unit": "$",
    },
    "ltv": {
        "keywords": [
            "ltv",
            "lifetime value",
            "customer lifetime",
            "clv",
            "customer value",
        ],
        "category": InsightCategory.REVENUE,
        "value_patterns": [
            r"\$[\d,]+(?:\.\d{2})?",
            r"ltv\s*(?:of|is)?\s*\$?(\d+)",
        ],
        "unit": "$",
    },
    "ltv_cac_ratio": {
        "keywords": [
            "ltv:cac",
            "ltv/cac",
            "ltv cac ratio",
            "lifetime to acquisition",
        ],
        "category": InsightCategory.GROWTH,
        "value_patterns": [
            r"(\d+(?:\.\d+)?)\s*(?:x|:1|to 1)",
            r"ratio\s*(?:of|is)?\s*(\d+(?:\.\d+)?)",
        ],
        "unit": "ratio",
    },
    "aov": {
        "keywords": [
            "aov",
            "average order",
            "order value",
            "basket size",
            "average purchase",
        ],
        "category": InsightCategory.REVENUE,
        "value_patterns": [
            r"\$[\d,]+(?:\.\d{2})?",
            r"aov\s*(?:of|is)?\s*\$?(\d+)",
        ],
        "unit": "$",
    },
    "conversion_rate": {
        "keywords": [
            "conversion rate",
            "conversion",
            "cvr",
            "purchase rate",
        ],
        "category": InsightCategory.GROWTH,
        "value_patterns": [
            r"(\d+(?:\.\d+)?)\s*%",
            r"conversion\s*(?:of|is|rate)?\s*(\d+(?:\.\d+)?)",
        ],
        "unit": "%",
    },
    "return_rate": {
        "keywords": [
            "return rate",
            "returns",
            "refund rate",
        ],
        "category": InsightCategory.OPERATIONS,
        "value_patterns": [
            r"(\d+(?:\.\d+)?)\s*%",
            r"return\s*(?:rate|of|is)?\s*(\d+(?:\.\d+)?)",
        ],
        "unit": "%",
    },
}


def _extract_value_from_text(text: str, patterns: list[str]) -> str | None:
    """Extract numeric value from text using patterns.

    Returns the first matched value as a string.
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Return the full match or first group
            if match.groups():
                return match.group(1)
            return match.group(0)
    return None


def _calculate_keyword_score(text: str, keywords: list[str]) -> float:
    """Calculate keyword match score (0-1).

    Returns proportion of keywords found in text.
    """
    if not keywords:
        return 0.0
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return matches / len(keywords)


def match_insight_to_metrics(
    question: str,
    answer: str,
    category: InsightCategory | str | None,
    metric_data: dict[str, Any] | None,
    confidence_score: float | None,
    answered_at: datetime | str | None,
) -> list[MetricMatch]:
    """Match an insight to potential business metrics.

    Uses multi-factor scoring:
    1. Category match (+0.3)
    2. Keyword presence in question/answer (+0.4)
    3. Value pattern extraction (+0.3)

    Args:
        question: The clarification question
        answer: User's answer
        category: InsightCategory or string
        metric_data: Extracted metric dict (value, unit, raw_text)
        confidence_score: Parse confidence from insight
        answered_at: When answered

    Returns:
        List of MetricMatch sorted by confidence (highest first)
    """
    matches: list[MetricMatch] = []

    # Normalize category
    if isinstance(category, str):
        try:
            category = InsightCategory(category)
        except ValueError:
            category = None

    # Combine question and answer for keyword search
    combined_text = f"{question} {answer}".lower()

    # Parse answered_at if string
    if isinstance(answered_at, str):
        try:
            answered_at = datetime.fromisoformat(answered_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            answered_at = None

    for metric_key, config in METRIC_KEYWORDS.items():
        score = 0.0

        # Factor 1: Category match (0.3)
        if category and config.get("category") == category:
            score += 0.3

        # Factor 2: Keyword presence (0.4)
        keywords = config.get("keywords", [])
        keyword_score = _calculate_keyword_score(combined_text, keywords)
        score += keyword_score * 0.4

        # Factor 3: Value extraction (0.3)
        patterns = config.get("value_patterns", [])
        extracted_value = _extract_value_from_text(combined_text, patterns)
        if extracted_value:
            score += 0.3

        # Skip if score too low
        if score < 0.3:
            continue

        # Determine suggested value
        suggested_value: str | float | None = None

        # Prefer extracted metric data if available
        if metric_data:
            suggested_value = metric_data.get("raw_text") or metric_data.get("value")

        # Fall back to pattern extraction
        if suggested_value is None and extracted_value:
            suggested_value = extracted_value

        # Skip if no value
        if suggested_value is None:
            continue

        # Boost score with original confidence if available
        if confidence_score is not None:
            score = (score + confidence_score) / 2

        matches.append(
            MetricMatch(
                metric_key=metric_key,
                suggested_value=suggested_value,
                confidence=round(min(score, 1.0), 2),
                source_question=question,
                source_answer=answer,
                answered_at=answered_at,
            )
        )

    # Sort by confidence descending
    matches.sort(key=lambda m: m.confidence, reverse=True)

    return matches


def get_insight_metric_suggestions(
    clarifications: dict[str, Any],
    existing_metrics: dict[str, Any] | None = None,
    confidence_threshold: float = 0.5,
    max_age_days: int = 90,
) -> list[dict[str, Any]]:
    """Get metric suggestions from all clarification insights.

    Scans all insights and returns suggestions for business_metrics that
    could be auto-populated.

    Args:
        clarifications: Dict mapping question -> insight entry
        existing_metrics: Dict mapping metric_key -> current value
        confidence_threshold: Minimum confidence to include (default 0.5)
        max_age_days: Exclude insights older than this (default 90)

    Returns:
        List of suggestion dicts: {
            metric_key: str,
            suggested_value: str | float,
            current_value: Any | None,
            source_question: str,
            confidence: float,
            answered_at: str | None,
        }
    """
    if not clarifications:
        return []

    cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)
    best_per_metric: dict[str, dict[str, Any]] = {}

    for question, entry in clarifications.items():
        if not isinstance(entry, dict):
            continue

        # Get entry fields
        answer = entry.get("answer", "")
        category = entry.get("category")
        metric_data = entry.get("metric")
        confidence_score = entry.get("confidence_score")
        answered_at = entry.get("answered_at")

        # Check recency
        if answered_at:
            try:
                if isinstance(answered_at, str):
                    answered_dt = datetime.fromisoformat(answered_at.replace("Z", "+00:00"))
                else:
                    answered_dt = answered_at
                if answered_dt < cutoff_date:
                    continue
            except (ValueError, TypeError):
                pass

        # Match to metrics
        matches = match_insight_to_metrics(
            question=question,
            answer=answer,
            category=category,
            metric_data=metric_data,
            confidence_score=confidence_score,
            answered_at=answered_at,
        )

        for match in matches:
            if match.confidence < confidence_threshold:
                continue

            # Get current value if exists
            current_value = None
            if existing_metrics and match.metric_key in existing_metrics:
                current_value = existing_metrics[match.metric_key]

            # Skip if value matches current
            if current_value is not None:
                if str(current_value) == str(match.suggested_value):
                    continue

            suggestion = {
                "metric_key": match.metric_key,
                "suggested_value": match.suggested_value,
                "current_value": current_value,
                "source_question": match.source_question,
                "confidence": match.confidence,
                "answered_at": match.answered_at.isoformat() if match.answered_at else None,
            }

            # Keep best per metric
            if match.metric_key not in best_per_metric or match.confidence > best_per_metric[
                match.metric_key
            ].get("confidence", 0):
                best_per_metric[match.metric_key] = suggestion

    # Sort by confidence
    suggestions = list(best_per_metric.values())
    suggestions.sort(key=lambda s: s.get("confidence", 0), reverse=True)

    return suggestions
