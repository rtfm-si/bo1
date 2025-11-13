"""Utilities for parsing XML-like tags from LLM responses.

This module consolidates XML tag extraction logic that was previously
duplicated across multiple files (voting.py, facilitator.py, moderator.py).
"""

import re


def extract_xml_tag(text: str, tag: str, case_insensitive: bool = True) -> str | None:
    """Extract content from XML-like tag.

    Args:
        text: Text containing XML tags
        tag: Tag name to extract (without < >)
        case_insensitive: Whether to match case-insensitively (default True)

    Returns:
        Tag content (stripped) or None if not found

    Examples:
        >>> extract_xml_tag("<thinking>Deep analysis</thinking>", "thinking")
        'Deep analysis'

        >>> extract_xml_tag("<VOTE>Yes</VOTE>", "vote")
        'Yes'

        >>> extract_xml_tag("No tags here", "missing")
        None

        >>> extract_xml_tag("<outer><inner>nested</inner></outer>", "inner")
        'nested'
    """
    flags = re.DOTALL | (re.IGNORECASE if case_insensitive else 0)
    pattern = rf"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def extract_multiple_tags(
    text: str, tags: list[str], case_insensitive: bool = True
) -> dict[str, str | None]:
    """Extract multiple XML tags from text.

    Args:
        text: Text containing XML tags
        tags: List of tag names to extract
        case_insensitive: Whether to match case-insensitively (default True)

    Returns:
        Dictionary mapping tag names to content (or None if not found)

    Examples:
        >>> text = "<thinking>Analysis</thinking><contribution>My view</contribution>"
        >>> extract_multiple_tags(text, ["thinking", "contribution"])
        {'thinking': 'Analysis', 'contribution': 'My view'}

        >>> extract_multiple_tags("<vote>Yes</vote>", ["vote", "confidence"])
        {'vote': 'Yes', 'confidence': None}
    """
    return {tag: extract_xml_tag(text, tag, case_insensitive) for tag in tags}
