"""Feedback analyzer service using Claude Haiku.

Extracts sentiment and themes from user feedback using fast, cheap Haiku calls.
Cost: ~$0.00025/request (1K input + 200 output tokens)

Provides:
- Sentiment classification (positive/negative/neutral/mixed)
- Theme extraction (1-5 topic tags)
- Confidence scoring
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from bo1.llm.client import ClaudeClient

logger = logging.getLogger(__name__)


class Sentiment(str, Enum):
    """Feedback sentiment classification."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


@dataclass
class FeedbackAnalysis:
    """Analysis result for a feedback submission."""

    sentiment: Sentiment
    sentiment_confidence: float  # 0.0-1.0
    themes: list[str]  # 1-5 theme tags
    analyzed_at: str  # ISO timestamp

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "sentiment": self.sentiment.value,
            "sentiment_confidence": self.sentiment_confidence,
            "themes": self.themes,
            "analyzed_at": self.analyzed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackAnalysis":
        """Create from dictionary."""
        sentiment_str = data.get("sentiment", "neutral")
        try:
            sentiment = Sentiment(sentiment_str)
        except ValueError:
            sentiment = Sentiment.NEUTRAL

        return cls(
            sentiment=sentiment,
            sentiment_confidence=data.get("sentiment_confidence", 0.5),
            themes=data.get("themes", []),
            analyzed_at=data.get("analyzed_at", datetime.now(UTC).isoformat()),
        )


class FeedbackAnalyzer:
    """Analyzes feedback submissions using Claude Haiku."""

    # Common theme tags for consistency
    STANDARD_THEMES = [
        "usability",
        "performance",
        "reliability",
        "pricing",
        "features",
        "design",
        "documentation",
        "onboarding",
        "support",
        "integration",
        "mobile",
        "export",
        "collaboration",
        "security",
        "customization",
    ]

    def __init__(self) -> None:
        """Initialize analyzer with lazy Claude client."""
        self._client: ClaudeClient | None = None

    def _get_client(self) -> ClaudeClient:
        """Lazy-initialize Claude client."""
        if self._client is None:
            self._client = ClaudeClient()
        return self._client

    async def analyze_feedback(self, title: str, description: str) -> FeedbackAnalysis | None:
        """Analyze feedback to extract sentiment and themes.

        Args:
            title: Feedback title/summary
            description: Detailed feedback description

        Returns:
            FeedbackAnalysis with sentiment and themes, or None on failure
        """
        if not title and not description:
            return None

        try:
            return await self._analyze_with_llm(title, description)
        except Exception as e:
            logger.warning(f"Feedback analysis failed, using fallback: {e}")
            # Fall back to simple rule-based analysis
            return self._fallback_analyze(title, description)

    async def _analyze_with_llm(self, title: str, description: str) -> FeedbackAnalysis:
        """Analyze feedback using Claude Haiku."""
        prompt = f"""Analyze this product feedback to extract sentiment and themes.

Title: "{title}"
Description: "{description}"

Return JSON with:
- sentiment: one of [positive, negative, neutral, mixed]
- sentiment_confidence: 0.0-1.0 (how confident in sentiment classification)
- themes: list of 1-5 theme tags (lowercase, e.g., "usability", "performance", "pricing", "features", "design", "reliability", "documentation", "onboarding", "support", "integration", "mobile", "export", "collaboration", "security", "customization")

Examples:
Input: "Dark mode would be great" / "I often use the app at night and the bright screen hurts my eyes. A dark theme would be amazing."
Output: {{"sentiment": "neutral", "sentiment_confidence": 0.8, "themes": ["design", "usability"]}}

Input: "Page keeps crashing" / "Every time I try to open a meeting, the page freezes and I have to refresh. Very frustrating."
Output: {{"sentiment": "negative", "sentiment_confidence": 0.95, "themes": ["reliability", "performance"]}}

Input: "Love the new features!" / "The recent update is fantastic. The charts are beautiful and the export works perfectly now."
Output: {{"sentiment": "positive", "sentiment_confidence": 0.9, "themes": ["features", "design", "export"]}}

Return ONLY valid JSON, no other text."""

        client = self._get_client()
        response, _ = await client.call(
            model="haiku",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
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

        # Validate and normalize sentiment
        sentiment_str = data.get("sentiment", "neutral").lower()
        try:
            sentiment = Sentiment(sentiment_str)
        except ValueError:
            sentiment = Sentiment.NEUTRAL

        # Normalize themes
        themes = data.get("themes", [])
        if isinstance(themes, list):
            # Clean and lowercase themes
            themes = [str(t).lower().strip() for t in themes[:5] if t]
        else:
            themes = []

        return FeedbackAnalysis(
            sentiment=sentiment,
            sentiment_confidence=min(1.0, max(0.0, float(data.get("sentiment_confidence", 0.5)))),
            themes=themes,
            analyzed_at=datetime.now(UTC).isoformat(),
        )

    def _fallback_analyze(self, title: str, description: str) -> FeedbackAnalysis:
        """Simple rule-based fallback analyzer."""
        text = f"{title} {description}".lower()

        # Sentiment detection
        positive_words = [
            "love",
            "great",
            "amazing",
            "fantastic",
            "excellent",
            "awesome",
            "perfect",
            "thanks",
            "helpful",
        ]
        negative_words = [
            "crash",
            "bug",
            "broken",
            "frustrating",
            "terrible",
            "awful",
            "hate",
            "slow",
            "annoying",
            "error",
            "issue",
            "problem",
        ]

        positive_count = sum(1 for w in positive_words if w in text)
        negative_count = sum(1 for w in negative_words if w in text)

        if positive_count > negative_count:
            sentiment = Sentiment.POSITIVE
            confidence = min(0.7, 0.4 + (positive_count * 0.1))
        elif negative_count > positive_count:
            sentiment = Sentiment.NEGATIVE
            confidence = min(0.7, 0.4 + (negative_count * 0.1))
        elif positive_count > 0 and negative_count > 0:
            sentiment = Sentiment.MIXED
            confidence = 0.5
        else:
            sentiment = Sentiment.NEUTRAL
            confidence = 0.4

        # Theme detection
        themes = []
        theme_keywords = {
            "usability": ["usability", "easy", "intuitive", "confusing", "ux", "user experience"],
            "performance": ["slow", "fast", "performance", "speed", "loading", "lag"],
            "reliability": ["crash", "bug", "error", "broken", "fix", "issue"],
            "pricing": ["price", "pricing", "cost", "expensive", "cheap", "plan", "subscription"],
            "features": ["feature", "add", "want", "wish", "would be nice"],
            "design": ["design", "ui", "look", "appearance", "dark mode", "theme", "color"],
            "documentation": ["docs", "documentation", "help", "guide", "tutorial"],
            "onboarding": ["onboarding", "getting started", "setup", "first time"],
            "support": ["support", "contact", "help", "response"],
            "integration": ["integration", "connect", "api", "import", "sync"],
            "mobile": ["mobile", "phone", "app", "ios", "android"],
            "export": ["export", "download", "pdf", "csv"],
        }

        for theme, keywords in theme_keywords.items():
            if any(kw in text for kw in keywords):
                themes.append(theme)
                if len(themes) >= 5:
                    break

        if not themes:
            themes = ["features"]  # Default theme

        return FeedbackAnalysis(
            sentiment=sentiment,
            sentiment_confidence=confidence,
            themes=themes,
            analyzed_at=datetime.now(UTC).isoformat(),
        )


# Module-level singleton
_analyzer: FeedbackAnalyzer | None = None


def get_feedback_analyzer() -> FeedbackAnalyzer:
    """Get or create feedback analyzer singleton."""
    global _analyzer
    if _analyzer is None:
        _analyzer = FeedbackAnalyzer()
    return _analyzer


async def analyze_feedback(title: str, description: str) -> FeedbackAnalysis | None:
    """Convenience function to analyze feedback.

    Args:
        title: Feedback title/summary
        description: Detailed feedback description

    Returns:
        FeedbackAnalysis with sentiment and themes, or None on failure
    """
    analyzer = get_feedback_analyzer()
    return await analyzer.analyze_feedback(title, description)
