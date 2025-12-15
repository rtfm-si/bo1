"""Prompt injection sanitization for user-provided inputs.

This module provides sanitization functions to prevent prompt injection attacks
when user-provided text (e.g., problem_statement) is interpolated into LLM prompts.
"""

import logging
import re

logger = logging.getLogger(__name__)

# XML-like tags that could override prompt structure
DANGEROUS_XML_TAGS = [
    "system",
    "assistant",
    "user",
    "instruction",
    "instructions",
    "prompt",
    "role",
    "context",
    "override",
    "ignore",
    "command",
    "execute",
]

# Instruction override patterns (case-insensitive)
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"ignore\s+(all\s+)?above\s+instructions?",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"you\s+are\s+now\s+(?:a|an|the)",
    r"new\s+instruction[s]?\s*:",
    r"system\s*:\s*",
    r"###\s*(?:system|instruction|override)",
    r"\[system\]",
    r"\[instruction[s]?\]",
]

# SQL injection patterns (case-insensitive) - targets advanced SQL attacks
# Uses word boundaries to avoid false positives on legitimate text
SQL_INJECTION_PATTERNS = [
    # Command execution
    r"\bEXEC\s*\(",
    r"\bEXECUTE\s*\(",
    # Extended stored procedures (SQL Server)
    r"\bxp_cmdshell\b",
    r"\bxp_regread\b",
    r"\bxp_regwrite\b",
    r"\bxp_fileexist\b",
    # System stored procedures
    r"\bsp_executesql\b",
    r"\bsp_makewebtask\b",
    r"\bsp_oacreate\b",
    # Time-based injection
    r"\bWAITFOR\s+DELAY\b",
    r"\bWAITFOR\s+TIME\b",
    # File operations
    r"\bBULK\s+INSERT\b",
    r"\bOPENROWSET\b",
    r"\bOPENDATASOURCE\b",
    r"\bINTO\s+OUTFILE\b",
    r"\bLOAD_FILE\s*\(",
]


def detect_sql_injection(text: str) -> str | None:
    """Detect SQL injection patterns in text.

    Scans for advanced SQL injection patterns including command execution,
    extended stored procedures, time-based attacks, and file operations.

    Args:
        text: Text to scan for SQL injection patterns

    Returns:
        Description of detected pattern, or None if no patterns found
    """
    if not text:
        return None

    for pattern in SQL_INJECTION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"SQL injection pattern detected: {match.group(0)}"

    return None


def sanitize_user_input(text: str, context: str = "user input") -> str:
    """Sanitize user-provided text to prevent prompt injection.

    Escapes XML-like tags and neutralizes instruction override patterns
    that could manipulate LLM behavior when interpolated into prompts.

    Args:
        text: User-provided text to sanitize
        context: Description of input source for logging

    Returns:
        Sanitized text safe for prompt interpolation
    """
    if not text:
        return text

    original = text
    modifications = []

    # 1. Escape dangerous XML-like tags by converting < > to unicode lookalikes
    for tag in DANGEROUS_XML_TAGS:
        # Match opening tags: <tag> or <tag ...>
        pattern_open = rf"<\s*{tag}(?:\s[^>]*)?\s*>"
        if re.search(pattern_open, text, re.IGNORECASE):
            text = re.sub(
                pattern_open,
                lambda m: str(m.group(0)).replace("<", "‹").replace(">", "›"),
                text,
                flags=re.IGNORECASE,
            )
            modifications.append(f"escaped <{tag}> tag")

        # Match closing tags: </tag>
        pattern_close = rf"<\s*/\s*{tag}\s*>"
        if re.search(pattern_close, text, re.IGNORECASE):
            text = re.sub(
                pattern_close,
                lambda m: str(m.group(0)).replace("<", "‹").replace(">", "›"),
                text,
                flags=re.IGNORECASE,
            )
            modifications.append(f"escaped </{tag}> tag")

    # 2. Neutralize instruction override patterns
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            # Wrap detected pattern in brackets to neutralize it
            text = re.sub(
                pattern,
                lambda m: f"[SANITIZED: {m.group(0)}]",
                text,
                flags=re.IGNORECASE,
            )
            modifications.append("neutralized injection pattern")

    # 3. Neutralize SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            text = re.sub(
                pattern,
                lambda m: f"[SQL_SANITIZED: {m.group(0)}]",
                text,
                flags=re.IGNORECASE,
            )
            modifications.append("neutralized SQL injection pattern")

    # 4. Log if any modifications were made
    if modifications and text != original:
        logger.warning(
            f"Sanitized {context}: {', '.join(set(modifications))}. "
            f"Original length: {len(original)}, sanitized length: {len(text)}"
        )

    return text


# XML tags that may leak from prompts into LLM outputs
PROMPT_ARTIFACT_TAGS = [
    "best_effort_mode",
    "thinking",
    "contribution",
    "debate_phase",
    "phase_goals",
    "critical_thinking_protocol",
    "forbidden_patterns",
    "critical_instruction",
]


def strip_prompt_artifacts(text: str) -> str:
    """Strip prompt scaffolding tags from LLM output.

    Removes XML-like tags that may leak from system prompts into model responses.
    Preserves the content inside tags while removing the tags themselves.

    Args:
        text: LLM output text that may contain leaked prompt artifacts

    Returns:
        Cleaned text with prompt artifacts removed
    """
    if not text:
        return text

    result = text

    # Remove XML-like prompt tags (preserve content inside)
    for tag in PROMPT_ARTIFACT_TAGS:
        # Remove opening tags: <tag> or <tag ...>
        result = re.sub(rf"<\s*{tag}(?:\s[^>]*)?\s*>", "", result, flags=re.IGNORECASE)
        # Remove closing tags: </tag>
        result = re.sub(rf"<\s*/\s*{tag}\s*>", "", result, flags=re.IGNORECASE)

    # Clean up excessive whitespace from tag removal
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = result.strip()

    if result != text.strip():
        logger.debug("Stripped prompt artifacts from LLM output")

    return result
