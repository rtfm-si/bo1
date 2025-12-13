"""Context extraction service using Claude Haiku.

Extracts business context updates from user text input. Identifies updatable fields
like revenue, customers, growth_rate, team_size, etc. with confidence scoring.

Uses Haiku for fast, cheap (~$0.0001/extraction) parsing.
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


class ContextUpdateSource(str, Enum):
    """Source of context update."""

    CLARIFICATION = "clarification"
    PROBLEM_STATEMENT = "problem_statement"
    ACTION_UPDATE = "action"


# Fields that can be auto-updated from user input
UPDATABLE_CONTEXT_FIELDS = [
    "revenue",
    "customers",
    "growth_rate",
    "team_size",
    "business_stage",
    "primary_objective",
    "industry",
    "pricing_model",
    "target_geography",
    "competitors",
    "mau_bucket",
    "revenue_stage",
]

# Confidence threshold for auto-apply (>= 0.8)
AUTO_APPLY_CONFIDENCE_THRESHOLD = 0.8

# Max pending updates per user (avoid suggestion fatigue)
MAX_PENDING_UPDATES = 5


@dataclass
class ContextUpdate:
    """A proposed update to business context."""

    field_name: str
    new_value: str | float | int | list[str] | list[dict[str, Any]]
    confidence: float  # 0.0 - 1.0
    source_type: ContextUpdateSource
    source_text: str  # Original text snippet
    extracted_at: str | None = None  # ISO timestamp

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "field_name": self.field_name,
            "new_value": self.new_value,
            "confidence": self.confidence,
            "source_type": self.source_type.value,
            "source_text": self.source_text,
            "extracted_at": self.extracted_at or datetime.now(UTC).isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextUpdate":
        """Create from dictionary."""
        return cls(
            field_name=data["field_name"],
            new_value=data["new_value"],
            confidence=data.get("confidence", 0.5),
            source_type=ContextUpdateSource(data.get("source_type", "clarification")),
            source_text=data.get("source_text", ""),
            extracted_at=data.get("extracted_at"),
        )


class ContextExtractor:
    """Extracts context updates from user text using Claude Haiku."""

    def __init__(self) -> None:
        """Initialize extractor with lazy Claude client."""
        self._client: ClaudeClient | None = None

    def _get_client(self) -> ClaudeClient:
        """Lazy-initialize Claude client."""
        if self._client is None:
            self._client = ClaudeClient()
        return self._client

    async def extract_context_updates(
        self,
        text: str,
        existing_context: dict[str, Any] | None = None,
        source_type: ContextUpdateSource = ContextUpdateSource.CLARIFICATION,
    ) -> list[ContextUpdate]:
        """Extract business context updates from user text.

        Args:
            text: User-provided text (clarification answer, problem statement, etc.)
            existing_context: Current business context (for comparison)
            source_type: Where the text came from

        Returns:
            List of ContextUpdate objects with field updates and confidence scores
        """
        if not text or not text.strip():
            return []

        # Try LLM extraction first
        try:
            updates = await self._extract_with_llm(text, existing_context, source_type)
            return updates
        except Exception as e:
            logger.warning(f"LLM extraction failed, using fallback: {e}")
            # Fall back to rule-based extraction
            return self._fallback_extract(text, source_type)

    async def _extract_with_llm(
        self,
        text: str,
        existing_context: dict[str, Any] | None,
        source_type: ContextUpdateSource,
    ) -> list[ContextUpdate]:
        """Extract updates using Claude Haiku."""
        existing_str = ""
        if existing_context:
            relevant = {
                k: v for k, v in existing_context.items() if k in UPDATABLE_CONTEXT_FIELDS and v
            }
            if relevant:
                existing_str = f"\n\nCurrent context:\n{json.dumps(relevant, indent=2)}"

        prompt = f"""Extract business context updates from this text.

Text: "{text}"{existing_str}

Look for explicit mentions of:
- revenue/MRR/ARR (field: revenue, value: string like "$50,000 MRR")
- customer count (field: customers, value: string like "200 active customers")
- growth rate (field: growth_rate, value: string like "15% MoM")
- team size (field: team_size, value: string like "small (2-5)" or "8 people")
- business stage (field: business_stage, value: "idea"|"early"|"growing"|"scaling")
- industry (field: industry, value: string)
- competitors (field: competitors, value: array of objects)

COMPETITORS - IMPORTANT:
Extract SPECIFIC company names only, NOT generic categories.

GOOD examples:
- "We compete against Asana and Monday.com" → [{{"name": "Asana", "category": "direct", "confidence": 0.95}}, {{"name": "Monday.com", "category": "direct", "confidence": 0.95}}]
- "Our main competitor is Figma" → [{{"name": "Figma", "category": "direct", "confidence": 0.9}}]
- "We're also watching Canva and Adobe XD" → [{{"name": "Canva", "category": "indirect", "confidence": 0.8}}, {{"name": "Adobe XD", "category": "indirect", "confidence": 0.8}}]

BAD examples (do NOT extract):
- "project management tools" → NOT specific companies
- "SaaS competitors" → NOT specific companies
- "other design software" → NOT specific companies

Return JSON array of updates:
[{{
  "field_name": "revenue",
  "new_value": "$50,000 MRR",
  "confidence": 0.95,
  "source_text": "our MRR is $50,000"
}},
{{
  "field_name": "competitors",
  "new_value": [{{"name": "Asana", "category": "direct", "confidence": 0.95}}],
  "confidence": 0.95,
  "source_text": "we compete against Asana"
}}]

Confidence scoring:
- 0.9-1.0: Explicit, unambiguous statement ("Our revenue is $50K")
- 0.7-0.89: Implied but clear ("we hit $50K this month")
- 0.5-0.69: Hedged/uncertain ("revenue is around $50K", "might be")
- <0.5: Speculation or unclear

For competitors specifically:
- "direct": Head-to-head competitor in same market
- "indirect": Related product or potential substitute

Return [] if no updates found. Only extract EXPLICIT statements about the business.
Do NOT infer or guess values not clearly stated.
Do NOT extract metaphorical statements ("customers are gold").
Do NOT extract generic competitor categories (e.g., "project management tools").

Return ONLY valid JSON array, no other text."""

        client = self._get_client()
        response, _ = await client.call(
            model="haiku",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000,
            prefill="[",
        )

        # Parse JSON response
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r"\[[\s\S]*\]", response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.warning(f"Failed to parse Haiku response: {response[:200]}")
                return []

        # Convert to ContextUpdate objects
        updates: list[ContextUpdate] = []
        now = datetime.now(UTC).isoformat()

        for item in data:
            if not isinstance(item, dict):
                continue

            field_name = item.get("field_name", "")
            if field_name not in UPDATABLE_CONTEXT_FIELDS:
                continue

            updates.append(
                ContextUpdate(
                    field_name=field_name,
                    new_value=item.get("new_value", ""),
                    confidence=float(item.get("confidence", 0.5)),
                    source_type=source_type,
                    source_text=item.get("source_text", text[:100]),
                    extracted_at=now,
                )
            )

        return updates

    def _fallback_extract(self, text: str, source_type: ContextUpdateSource) -> list[ContextUpdate]:
        """Rule-based fallback extraction when LLM fails."""
        updates: list[ContextUpdate] = []
        text_lower = text.lower()
        now = datetime.now(UTC).isoformat()

        # Revenue patterns
        revenue_match = re.search(
            r"\$[\d,]+(?:\.\d+)?(?:k|K|m|M)?\s*(?:mrr|arr|revenue|monthly|annually)?",
            text,
            re.IGNORECASE,
        )
        if revenue_match:
            updates.append(
                ContextUpdate(
                    field_name="revenue",
                    new_value=revenue_match.group().strip(),
                    confidence=0.7,
                    source_type=source_type,
                    source_text=revenue_match.group(),
                    extracted_at=now,
                )
            )

        # Customer count patterns
        customer_match = re.search(
            r"(\d+)\s*(?:active\s+)?(?:customers?|clients?|users?|subscribers?)",
            text_lower,
        )
        if customer_match:
            updates.append(
                ContextUpdate(
                    field_name="customers",
                    new_value=customer_match.group(1),
                    confidence=0.6,
                    source_type=source_type,
                    source_text=customer_match.group(),
                    extracted_at=now,
                )
            )

        # Team size patterns
        team_match = re.search(
            r"(\d+)\s*(?:people|employees?|team\s*members?|engineers?|staff)",
            text_lower,
        )
        if team_match:
            count = int(team_match.group(1))
            if count == 1:
                team_size = "solo"
            elif count <= 5:
                team_size = "small (2-5)"
            elif count <= 20:
                team_size = "medium (6-20)"
            else:
                team_size = "large (20+)"

            updates.append(
                ContextUpdate(
                    field_name="team_size",
                    new_value=team_size,
                    confidence=0.6,
                    source_type=source_type,
                    source_text=team_match.group(),
                    extracted_at=now,
                )
            )

        # Growth rate patterns
        growth_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:mom|yoy|growth|growing)", text_lower)
        if growth_match:
            updates.append(
                ContextUpdate(
                    field_name="growth_rate",
                    new_value=f"{growth_match.group(1)}%",
                    confidence=0.6,
                    source_type=source_type,
                    source_text=growth_match.group(),
                    extracted_at=now,
                )
            )

        # Competitor patterns - extract specific company names
        competitor_updates = self._extract_competitors_fallback(text, source_type, now)
        updates.extend(competitor_updates)

        return updates

    def _extract_competitors_fallback(
        self, text: str, source_type: ContextUpdateSource, now: str
    ) -> list[ContextUpdate]:
        """Extract specific competitor company names using pattern matching."""
        competitors: list[dict[str, Any]] = []

        # Pattern 1: "competing with X and Y" / "compete against X and Y"
        compete_pattern = re.search(
            r"compet(?:e|ing)\s+(?:with|against)\s+([^.]+)",
            text,
            re.IGNORECASE,
        )
        if compete_pattern:
            names = self._extract_proper_nouns(compete_pattern.group(1))
            for name in names:
                competitors.append({"name": name, "category": "direct", "confidence": 0.7})

        # Pattern 2: "X is our main competitor" / "our competitor is X"
        main_competitor = re.search(
            r"(?:main|primary|biggest|key)\s+competitor\s+(?:is\s+)?([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
            text,
            re.IGNORECASE,
        )
        if main_competitor:
            name = main_competitor.group(1).strip().rstrip(".")
            if self._is_likely_company_name(name):
                competitors.append({"name": name, "category": "direct", "confidence": 0.75})

        # Pattern 3: "competitors like X, Y, Z" / "competitors include X, Y, Z"
        competitors_list = re.search(
            r"competitors?\s+(?:like|include|are|such\s+as)\s+([^.]+)",
            text,
            re.IGNORECASE,
        )
        if competitors_list:
            names = self._extract_proper_nouns(competitors_list.group(1))
            for name in names:
                if not any(c["name"].lower() == name.lower() for c in competitors):
                    competitors.append({"name": name, "category": "direct", "confidence": 0.65})

        # Pattern 4: "X and Y are our competitors"
        are_competitors = re.search(
            r"([A-Z][a-zA-Z0-9.,\s]+)\s+are\s+(?:our\s+)?competitors?",
            text,
        )
        if are_competitors:
            names = self._extract_proper_nouns(are_competitors.group(1))
            for name in names:
                if not any(c["name"].lower() == name.lower() for c in competitors):
                    competitors.append({"name": name, "category": "direct", "confidence": 0.65})

        if not competitors:
            return []

        # Return as single update with list of competitors
        source_text = text[:100] if len(text) > 100 else text
        return [
            ContextUpdate(
                field_name="competitors",
                new_value=competitors,
                confidence=max(c["confidence"] for c in competitors),
                source_type=source_type,
                source_text=source_text,
                extracted_at=now,
            )
        ]

    def _extract_proper_nouns(self, text: str) -> list[str]:
        """Extract proper nouns (potential company names) from text."""
        # Split by common separators: and, or, comma
        parts = re.split(r",\s*|\s+and\s+|\s+or\s+", text)
        names = []

        for part in parts:
            part = part.strip()
            # Look for capitalized words or known company patterns
            # Match: "Asana", "Monday.com", "Adobe XD", "Slack"
            match = re.match(
                r"^([A-Z][a-zA-Z0-9]*(?:\.[a-zA-Z]+)?(?:\s+[A-Z][a-zA-Z0-9]*)*)$", part
            )
            if match and self._is_likely_company_name(match.group(1)):
                names.append(match.group(1))
            else:
                # Try to extract capitalized words from the part
                words = re.findall(r"\b([A-Z][a-zA-Z0-9]*(?:\.[a-zA-Z]+)?)\b", part)
                for word in words:
                    if self._is_likely_company_name(word):
                        names.append(word)

        return names

    def _is_likely_company_name(self, name: str) -> bool:
        """Check if a name is likely a company name (not a generic term)."""
        # Exclude common words that are capitalized at sentence start
        generic_words = {
            "the",
            "a",
            "an",
            "our",
            "their",
            "we",
            "they",
            "it",
            "project",
            "management",
            "tools",
            "software",
            "apps",
            "saas",
            "companies",
            "competitors",
            "products",
            "services",
            "other",
            "many",
            "some",
            "all",
            "most",
            "few",
        }
        return len(name) >= 2 and name.lower() not in generic_words and name[0].isupper()


# Module-level singleton
_extractor: ContextExtractor | None = None


def get_context_extractor() -> ContextExtractor:
    """Get or create context extractor singleton."""
    global _extractor
    if _extractor is None:
        _extractor = ContextExtractor()
    return _extractor


async def extract_context_updates(
    text: str,
    existing_context: dict[str, Any] | None = None,
    source_type: ContextUpdateSource = ContextUpdateSource.CLARIFICATION,
) -> list[ContextUpdate]:
    """Convenience function to extract context updates.

    Args:
        text: User-provided text
        existing_context: Current business context
        source_type: Source of the text

    Returns:
        List of ContextUpdate objects
    """
    extractor = get_context_extractor()
    return await extractor.extract_context_updates(text, existing_context, source_type)


def filter_high_confidence_updates(
    updates: list[ContextUpdate],
    threshold: float = AUTO_APPLY_CONFIDENCE_THRESHOLD,
) -> tuple[list[ContextUpdate], list[ContextUpdate]]:
    """Split updates into high-confidence (auto-apply) and low-confidence (pending).

    Args:
        updates: List of context updates
        threshold: Confidence threshold for auto-apply

    Returns:
        Tuple of (high_confidence, low_confidence) update lists
    """
    high = [u for u in updates if u.confidence >= threshold]
    low = [u for u in updates if u.confidence < threshold]
    return high, low


def merge_competitors(
    existing: list[dict[str, Any]] | str | None,
    new: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge extracted competitors with existing, deduplicating by name.

    Args:
        existing: Current competitors (list of dicts or comma-separated string)
        new: Newly extracted competitors

    Returns:
        Merged list of competitor dicts, deduplicated by name (case-insensitive)
    """
    result: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    # Handle existing competitors
    if existing:
        if isinstance(existing, str):
            # Convert comma-separated string to list of dicts
            for name in existing.split(","):
                name = name.strip()
                if name and name.lower() not in seen_names:
                    seen_names.add(name.lower())
                    result.append({"name": name, "category": "direct", "confidence": 1.0})
        elif isinstance(existing, list):
            for comp in existing:
                if isinstance(comp, dict) and "name" in comp:
                    name = comp["name"]
                    if name.lower() not in seen_names:
                        seen_names.add(name.lower())
                        result.append(comp)
                elif isinstance(comp, str):
                    if comp.lower() not in seen_names:
                        seen_names.add(comp.lower())
                        result.append({"name": comp, "category": "direct", "confidence": 1.0})

    # Add new competitors
    for comp in new:
        name = comp.get("name", "")
        if name and name.lower() not in seen_names:
            seen_names.add(name.lower())
            result.append(comp)

    return result


def format_competitors_for_display(competitors: list[dict[str, Any]] | str | None) -> str:
    """Format competitors list for human-readable display.

    Args:
        competitors: List of competitor dicts or comma-separated string

    Returns:
        Human-readable string like "Asana, Monday.com, Figma"
    """
    if not competitors:
        return ""

    if isinstance(competitors, str):
        return competitors

    names = []
    for comp in competitors:
        if isinstance(comp, dict) and "name" in comp:
            names.append(comp["name"])
        elif isinstance(comp, str):
            names.append(comp)

    return ", ".join(names)
