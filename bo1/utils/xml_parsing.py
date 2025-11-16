"""Utilities for parsing XML-like tags from LLM responses.

This module consolidates XML tag extraction logic that was previously
duplicated across multiple files (voting.py, facilitator.py, moderator.py).
"""

import logging
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


def extract_xml_tag_with_fallback(
    text: str,
    tag: str,
    logger: logging.Logger | None = None,
    fallback_to_full: bool = True,
    context: str = "",
) -> str:
    """Extract XML tag with automatic fallback and logging.

    Consolidates the common pattern of extracting XML tags with fallback
    handling and standardized logging messages.

    Args:
        text: Text containing XML tag
        tag: Tag name to extract (without < >)
        logger: Logger instance for logging messages (optional)
        fallback_to_full: If True, return full text when tag not found.
                         If False, return empty string. (default True)
        context: Optional context string for log messages (e.g., "synthesis report")

    Returns:
        Extracted tag content, or fallback value if not found

    Examples:
        >>> import logging
        >>> logger = logging.getLogger(__name__)
        >>> text = "<report>Analysis complete</report>"
        >>> extract_xml_tag_with_fallback(text, "report", logger)
        'Analysis complete'

        >>> extract_xml_tag_with_fallback("No tags", "report", logger, context="synthesis")
        'No tags'

        >>> extract_xml_tag_with_fallback("No tags", "report", fallback_to_full=False)
        ''
    """
    extracted = extract_xml_tag(text, tag)

    if extracted:
        if logger:
            context_msg = f" ({context})" if context else ""
            logger.info(f"✓ Successfully extracted <{tag}> tag{context_msg}")
        return extracted

    # Tag not found - use fallback
    if logger:
        context_msg = f" ({context})" if context else ""
        fallback_msg = "full response" if fallback_to_full else "empty string"
        logger.warning(
            f"⚠️ FALLBACK: Could not extract <{tag}> tag{context_msg}. "
            f"Using {fallback_msg}. Preview: {text[:200]}..."
        )

    return text if fallback_to_full else ""
