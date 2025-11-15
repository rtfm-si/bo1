"""Utilities for parsing vote decisions and confidence from LLM responses.

DEPRECATED: The parse_vote_decision function is no longer used in the recommendation system.
Only parse_confidence_level and parse_conditions are still actively used.
"""


def parse_vote_decision(decision_str: str | None) -> str:
    """Parse vote decision from string.

    DEPRECATED: This function is no longer used in the recommendation system.
    Kept for backward compatibility with old tests only.

    Args:
        decision_str: Decision string from vote (e.g., "Yes", "No", "Conditional")
                     Can be None or empty.

    Returns:
        String decision value ("yes", "no", "conditional", "abstain")
    """
    if not decision_str:
        return "abstain"

    decision_lower = decision_str.lower().strip()

    # Check for conditional FIRST (to catch "Yes, if..." before plain "Yes")
    if any(
        keyword in decision_lower for keyword in ["conditional", " if ", "only if", "provided that"]
    ):
        return "conditional"

    # Check for yes/approve/support
    if any(keyword in decision_lower for keyword in ["yes", "approve", "support", "accept"]):
        return "yes"

    # Check for no/reject/oppose
    # Use word boundaries and handle standalone "no" or "no" with punctuation
    if (
        decision_lower == "no"
        or decision_lower.startswith("no ")
        or decision_lower.startswith("no,")
        or decision_lower.startswith("no.")
        or decision_lower.endswith(" no")
        or any(keyword in decision_lower for keyword in ["reject", "oppose", "decline"])
    ):
        return "no"

    # Default to abstain for unclear responses
    return "abstain"


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
