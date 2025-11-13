"""Utilities for parsing JSON from LLM responses with fallback strategies.

This module consolidates JSON parsing logic that was previously duplicated
across multiple files (voting.py, decomposer.py, selector.py, facilitator.py).
"""

import json
import logging
import re
from typing import Any


def parse_json_with_fallback(
    content: str,
    prefill: str = "",
    context: str = "",
    logger: logging.Logger | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    r"""Parse JSON from LLM response with multiple fallback strategies.

    Attempts multiple parsing strategies in order:
    1. Direct JSON parse (with optional prefill)
    2. Extract from markdown code block (```json ... ```)
    3. Regex extraction of first JSON object

    Args:
        content: Content to parse (may contain JSON)
        prefill: Optional string to prepend (e.g., "{" for assistant prefill)
        context: Context string for error logging (e.g., "vote parsing")
        logger: Optional logger for error messages

    Returns:
        Tuple of (parsed_data, error_messages)
        - parsed_data: Parsed dict or None if all strategies failed
        - error_messages: List of error messages from each strategy

    Examples:
        >>> parse_json_with_fallback('{"key": "value"}')
        ({'key': 'value'}, [])

        >>> parse_json_with_fallback('```json\n{"key": "value"}\n```')
        ({'key': 'value'}, ['Strategy 1 (direct parse): ...'])

        >>> parse_json_with_fallback('"sub_problems": [...]', prefill="{")
        ({'sub_problems': [...]}, [])

        >>> parse_json_with_fallback('No JSON here')
        (None, ['Strategy 1: ...', 'Strategy 2: ...', 'Strategy 3: ...'])
    """
    errors: list[str] = []

    # Prepare content with prefill
    json_content = content
    if prefill:
        json_content = prefill + content.lstrip()

    # Strategy 1: Direct parse
    try:
        data = json.loads(json_content)
        return data, errors
    except json.JSONDecodeError as e:
        errors.append(f"Strategy 1 (direct parse): {e}")

    # Strategy 2: Markdown code block extraction
    if "```" in content:
        code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(code_block_pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                data = json.loads(match.group(1))
                if logger:
                    logger.warning(f"JSON extracted from markdown code block ({context})")
                return data, errors
            except json.JSONDecodeError as e:
                errors.append(f"Strategy 2 (markdown block): {e}")

    # Strategy 3: Regex extraction of first JSON object
    json_pattern = r"\{.*\}"
    match = re.search(json_pattern, content, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if logger:
                logger.warning(f"JSON extracted via regex ({context})")
            return data, errors
        except json.JSONDecodeError as e:
            errors.append(f"Strategy 3 (regex extraction): {e}")

    # All strategies failed
    if logger:
        logger.error(f"All JSON parsing strategies failed ({context})")
        logger.debug(f"Content preview: {content[:200]}...")

    errors.append("All parsing strategies exhausted")
    return None, errors


def validate_json_schema(
    data: dict[str, Any],
    required_fields: list[str],
    optional_fields: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """Validate JSON data has required fields.

    Args:
        data: Parsed JSON data
        required_fields: List of required field names
        optional_fields: List of optional field names (for validation)

    Returns:
        Tuple of (is_valid, error_messages)

    Examples:
        >>> validate_json_schema({"name": "Alice", "age": 30}, ["name", "age"])
        (True, [])

        >>> validate_json_schema({"name": "Alice"}, ["name", "age"])
        (False, ['Missing required field: age'])

        >>> validate_json_schema({"name": "Alice", "extra": "data"}, ["name"], ["age"])
        (False, ['Unexpected field: extra'])
    """
    errors = []

    # Check required fields
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Check for unexpected fields (if optional_fields provided)
    if optional_fields is not None:
        allowed_fields = set(required_fields) | set(optional_fields)
        for field in data:
            if field not in allowed_fields:
                errors.append(f"Unexpected field: {field}")

    return len(errors) == 0, errors
