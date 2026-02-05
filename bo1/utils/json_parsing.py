"""Utilities for parsing JSON from LLM responses with fallback strategies.

This module consolidates JSON parsing logic that was previously duplicated
across multiple files (voting.py, decomposer.py, selector.py, facilitator.py).
"""

import json
import logging
import re
from collections.abc import Callable
from typing import Any

from bo1.llm.response import LLMResponse


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

    # Strategy 2: Markdown code block extraction (objects or arrays)
    if "```" in content:
        code_block_pattern = r"```(?:json)?\s*([\{\[].*?[\}\]])\s*```"
        match = re.search(code_block_pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                data = json.loads(match.group(1))
                if logger:
                    logger.warning(f"JSON extracted from markdown code block ({context})")
                return data, errors
            except json.JSONDecodeError as e:
                errors.append(f"Strategy 2 (markdown block): {e}")

    # Strategy 3: Regex extraction of first JSON object or array
    # Try object first, then array
    for pattern in [r"\{.*\}", r"\[.*\]"]:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if logger:
                    logger.warning(f"JSON extracted via regex ({context})")
                return data, errors
            except json.JSONDecodeError as e:
                errors.append(f"Strategy 3 (regex extraction {pattern}): {e}")

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


def parse_and_validate_json_response(
    response: LLMResponse,
    required_fields: list[str],
    fallback_factory: Callable[[], dict[str, Any]],
    context: str,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Parse JSON response with validation and fallback handling.

    This function consolidates the pattern of:
    1. Parse JSON from LLM response
    2. Validate required fields exist
    3. Fall back to factory function if parsing/validation fails
    4. Log success/failure appropriately

    Args:
        response: LLM response containing JSON content
        required_fields: List of required field names
        fallback_factory: Function that creates fallback dict if parsing fails
        context: Context string for logging (e.g., "vote parsing")
        logger: Logger for info/error messages

    Returns:
        Parsed and validated dict (or fallback dict if parsing failed)

    Example:
        >>> def create_fallback():
        ...     return {"sub_problems": [], "is_atomic": True}
        >>> data = parse_and_validate_json_response(
        ...     response=llm_response,
        ...     required_fields=["sub_problems", "is_atomic"],
        ...     fallback_factory=create_fallback,
        ...     context="decomposition",
        ...     logger=logger
        ... )
    """
    try:
        data = json.loads(response.content)

        # Validate required fields
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        logger.info(f"✓ Successfully parsed {context}")
        return data  # type: ignore[no-any-return]

    except json.JSONDecodeError as e:
        logger.error(f"⚠️ FALLBACK: Failed to parse {context} JSON. Error: {e}")
        return fallback_factory()
    except Exception:
        logger.error(f"⚠️ FALLBACK: Unexpected error in {context}. Re-raising...")
        raise


def extract_json_with_fallback(
    content: str,
    fallback_factory: Callable[[], dict[str, Any]],
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Robust JSON parsing with multiple fallback strategies.

    This function consolidates the brace-counting JSON extraction pattern
    used in decompose_node and other locations. It tries multiple strategies:
    1. Direct JSON parse
    2. Extract JSON block using brace counting
    3. Fallback to factory function

    Args:
        content: Content to parse (may contain JSON mixed with other text)
        fallback_factory: Function that creates fallback dict if all parsing fails
        logger: Optional logger for warnings

    Returns:
        Parsed dict or fallback dict

    Example:
        >>> def create_fallback():
        ...     return {"sub_problems": [], "is_atomic": True}
        >>> data = extract_json_with_fallback(
        ...     content='Some text {"key": "value"} more text',
        ...     fallback_factory=create_fallback,
        ...     logger=logger
        ... )
    """
    # Strategy 1: Direct parse
    try:
        return json.loads(content)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract JSON block with brace counting
    try:
        start = content.find("{")
        if start == -1:
            raise ValueError("No JSON object found")

        brace_count = 0
        end = start
        for i in range(start, len(content)):
            if content[i] == "{":
                brace_count += 1
            elif content[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break

        json_str = content[start:end]
        return json.loads(json_str)  # type: ignore[no-any-return]
    except (ValueError, json.JSONDecodeError):
        if logger:
            logger.warning("⚠️ All JSON parsing strategies failed, using fallback")
        return fallback_factory()
