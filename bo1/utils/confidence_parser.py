"""Utilities for parsing confidence levels and conditions from LLM responses.

These utilities are used in the recommendation system for parsing expert recommendations.
"""

import re


def extract_confidence_from_text(text: str) -> str | None:
    """Extract confidence value from unstructured text using fallback patterns.

    Used when <confidence> tag extraction fails. Tries multiple patterns
    to find confidence level or score in the text.

    Args:
        text: Full response text to search

    Returns:
        Extracted confidence string or None if not found

    Examples:
        >>> extract_confidence_from_text("My confidence is high for this recommendation")
        'high'
        >>> extract_confidence_from_text("I have 85% confidence in this approach")
        '85%'
        >>> extract_confidence_from_text("Confidence: 0.75")
        '0.75'
    """
    # Patterns to try (in order of preference)
    patterns = [
        # "confidence: high" or "confidence level: medium"
        r"confidence(?:\s+level)?[:\s]+([a-z]+|\d+\.?\d*%?)",
        # "I am/have [very] high/medium/low confidence"
        r"(?:i\s+(?:am|have)\s+)?(?:very\s+)?(high|medium|moderate|low)\s+confidence",
        # "with high confidence" or "with 80% confidence"
        r"with\s+(?:a\s+)?(\d+\.?\d*%?|high|medium|moderate|low)\s+confidence",
        # "confidence of 0.8" or "confidence of high"
        r"confidence\s+of\s+(\d+\.?\d*%?|high|medium|moderate|low)",
        # Just "high confidence" or "medium confidence" at word boundaries
        r"\b(high|medium|moderate|low)\s+confidence\b",
    ]

    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return match.group(1)

    return None


def parse_confidence_level(confidence_str: str | None) -> float:
    """Parse confidence from string to 0-1 score.

    Supports both named levels (high/medium/low) and numeric values.

    Args:
        confidence_str: Confidence string (e.g., "High", "0.8", "80%")
                       Can be None or empty.

    Returns:
        Float between 0 and 1 (defaults to 0.6 if unparseable)

    Examples:
        >>> parse_confidence_level("high")
        0.85
        >>> parse_confidence_level("medium")
        0.6
        >>> parse_confidence_level("low")
        0.3
        >>> parse_confidence_level("0.75")
        0.75
        >>> parse_confidence_level("85%")
        0.85
        >>> parse_confidence_level(None)
        0.6
    """
    if not confidence_str:
        return 0.6  # Default: medium confidence

    confidence_lower = confidence_str.lower().strip()

    # Named levels
    if "high" in confidence_lower or "strong" in confidence_lower:
        return 0.85
    elif "medium" in confidence_lower or "moderate" in confidence_lower:
        return 0.6
    elif "low" in confidence_lower or "weak" in confidence_lower:
        return 0.3

    # Try to parse as number
    try:
        # Check if it has % symbol
        has_percent = "%" in confidence_lower
        # Remove % if present
        num_str = confidence_lower.replace("%", "").strip()
        value = float(num_str)

        # If > 1 OR has percent symbol, treat as percentage (convert to 0-1 scale)
        if value > 1 or has_percent:
            value = value / 100

        # Clamp to 0-1 range
        return max(0.0, min(1.0, value))
    except (ValueError, TypeError):
        return 0.6  # Default to medium confidence if parsing fails


def parse_conditions(conditions_str: str | None) -> list[str]:
    r"""Parse conditions from multi-line string.

    Extracts individual conditions by splitting on newlines and cleaning up
    formatting (bullets, dashes, numbers, etc.).

    Args:
        conditions_str: Multi-line string containing conditions
                       Can be None or empty.

    Returns:
        List of condition strings (empty list if no valid conditions)

    Examples:
        >>> parse_conditions("- Budget must be approved\n- Timeline is 6 months")
        ['Budget must be approved', 'Timeline is 6 months']
        >>> parse_conditions("1. First condition\n2. Second condition")
        ['First condition', 'Second condition']
        >>> parse_conditions(None)
        []
    """
    if not conditions_str:
        return []

    conditions = []
    for line in conditions_str.split("\n"):
        line = line.strip()
        # Skip empty lines, XML tags, and very short lines
        if line and not line.startswith("<") and len(line) > 5:
            # Remove bullet points, dashes, numbers, asterisks
            cleaned = line.lstrip("- •*0123456789.)")
            if cleaned:
                conditions.append(cleaned.strip())

    return conditions
