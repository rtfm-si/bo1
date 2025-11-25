"""Response extraction utilities for LLM responses.

Provides reusable extraction patterns to consolidate similar logic across agents.
"""

import logging
from typing import Any

from bo1.constants import TokenLimits
from bo1.utils.xml_parsing import extract_xml_tag


class ResponseExtractor:
    """Utilities for extracting structured data from LLM responses.

    Consolidates common extraction patterns used across facilitator, voting,
    and moderator agents.
    """

    @staticmethod
    def extract_persona_code(
        content: str,
        personas: list[Any],
        logger: logging.Logger | None = None,
    ) -> str | None:
        """Extract persona code from response content.

        Args:
            content: LLM response content to search
            personas: List of PersonaProfile objects with 'code' attribute
            logger: Optional logger for warnings

        Returns:
            Matched persona code, or first persona code as fallback, or None if no personas

        Example:
            >>> personas = [PersonaProfile(code="maria_gomez"), PersonaProfile(code="tariq_khan")]
            >>> ResponseExtractor.extract_persona_code("I think maria_gomez should speak next", personas)
            'maria_gomez'
        """
        if not personas:
            if logger:
                logger.error("No personas available for extraction")
            return None

        content_lower = content.lower()

        # Try exact match first (case-insensitive)
        for persona in personas:
            code: str = persona.code
            if code.lower() in content_lower:
                return code

        # Try with underscores replaced by spaces
        for persona in personas:
            code_str: str = persona.code
            code_with_spaces = code_str.replace("_", " ").lower()
            if code_with_spaces in content_lower:
                return code_str

        # Try matching persona name if available
        for persona in personas:
            if hasattr(persona, "name") and persona.name:
                name_lower = str(persona.name).lower()
                if name_lower in content_lower:
                    return str(persona.code)

        # Fallback to first persona
        fallback_code: str = personas[0].code
        if logger:
            logger.warning(
                f"Could not identify persona in content, defaulting to {fallback_code}. "
                f"Content preview: {content[:100]}..."
            )
        return fallback_code

    @staticmethod
    def extract_after_marker(
        content: str,
        markers: list[str],
        max_length: int = TokenLimits.SNIPPET_MAX_LENGTH,
    ) -> str | None:
        """Extract text immediately after a marker keyword.

        Args:
            content: Content to search
            markers: List of marker strings to look for (e.g., "prompt:", "focus:")
            max_length: Maximum length of extracted snippet

        Returns:
            Extracted text snippet, or None if no marker found

        Example:
            >>> ResponseExtractor.extract_after_marker(
            ...     "The prompt: What are your thoughts? Let's discuss.",
            ...     ["prompt:", "focus:"]
            ... )
            'What are your thoughts?'
        """
        for marker in markers:
            idx = content.lower().find(marker)
            if idx != -1:
                snippet = content[idx + len(marker) : idx + max_length].split("\n")[0].strip()
                if snippet:
                    return snippet
        return None

    @staticmethod
    def extract_enum_from_keywords(
        content: str,
        keyword_map: dict[str, str],
        default: str | None = None,
    ) -> str | None:
        """Extract enum value by matching keywords in content.

        Args:
            content: Content to search
            keyword_map: Dictionary mapping keywords to enum values
            default: Default value if no keyword matches

        Returns:
            Matched enum value, or default if no match

        Example:
            >>> ResponseExtractor.extract_enum_from_keywords(
            ...     "We should trigger the contrarian moderator",
            ...     {"contrarian": "contrarian", "skeptic": "skeptic"},
            ...     default="contrarian"
            ... )
            'contrarian'
        """
        content_lower = content.lower()
        for keyword, value in keyword_map.items():
            if keyword in content_lower:
                return value
        return default

    @staticmethod
    def safe_extract_tag(
        content: str,
        tag: str,
        fallback: str | None = None,
        context: str = "",
        logger: logging.Logger | None = None,
    ) -> str | None:
        """Extract XML tag with automatic fallback and logging.

        This is a convenience wrapper around xml_parsing.extract_xml_tag() that adds
        standardized fallback logging.

        Args:
            content: Content to extract from
            tag: XML tag name to extract
            fallback: Fallback value if extraction fails
            context: Context description for logging (e.g., "vote parsing")
            logger: Optional logger instance

        Returns:
            Extracted content, or fallback value if extraction fails

        Example:
            >>> ResponseExtractor.safe_extract_tag(
            ...     "<vote>approve</vote>",
            ...     "vote",
            ...     fallback="abstain",
            ...     context="vote parsing",
            ...     logger=logger
            ... )
            'approve'
        """
        result = extract_xml_tag(content, tag)

        if result:
            if logger:
                logger.debug(f"Successfully extracted <{tag}> tag")
            return result

        if logger:
            fallback_preview = f": {fallback[:100]}" if fallback else ""
            logger.warning(
                f"Could not extract <{tag}> tag"
                + (f" ({context})" if context else "")
                + (f". Using fallback{fallback_preview}" if fallback else "")
            )

        return fallback

    @staticmethod
    def extract_multiple_tags_safe(
        content: str,
        tags: list[str],
        fallbacks: dict[str, str] | None = None,
        logger: logging.Logger | None = None,
    ) -> dict[str, str | None]:
        """Extract multiple XML tags at once with optional fallbacks.

        Args:
            content: Content to extract from
            tags: List of tag names to extract
            fallbacks: Optional dict mapping tag names to fallback values
            logger: Optional logger instance

        Returns:
            Dictionary mapping tag names to extracted content (or fallback/None)

        Example:
            >>> ResponseExtractor.extract_multiple_tags_safe(
            ...     "<vote>approve</vote><reasoning>Good idea</reasoning>",
            ...     ["vote", "reasoning", "confidence"],
            ...     fallbacks={"confidence": "medium"}
            ... )
            {'vote': 'approve', 'reasoning': 'Good idea', 'confidence': 'medium'}
        """
        fallbacks = fallbacks or {}
        results = {}

        for tag in tags:
            fallback = fallbacks.get(tag)
            results[tag] = ResponseExtractor.safe_extract_tag(
                content, tag, fallback=fallback, context=f"{tag} extraction", logger=logger
            )

        return results
