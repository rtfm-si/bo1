"""Security module for Board of One.

Provides security utilities for:
- Prompt injection detection and prevention (pattern-based and LLM-based)
- Input validation and sanitization
- Security logging and monitoring

Two layers of prompt injection detection:
1. Pattern-based (fast, synchronous) - detect_prompt_injection(), sanitize_user_input()
2. LLM-based (thorough, async) - prompt_injection_auditor.check(), check_for_injection()
"""

from bo1.security.prompt_injection import (
    AuditResult,
    CategoryResult,
    PromptInjectionAuditor,
    check_for_injection,
    prompt_injection_auditor,
)
from bo1.security.prompt_validation import (
    PromptInjectionError,
    detect_prompt_injection,
    sanitize_user_input,
    validate_context_input,
    validate_problem_statement,
)

__all__ = [
    # Pattern-based (fast, sync)
    "detect_prompt_injection",
    "sanitize_user_input",
    "validate_problem_statement",
    "validate_context_input",
    "PromptInjectionError",
    # LLM-based (thorough, async)
    "prompt_injection_auditor",
    "check_for_injection",
    "PromptInjectionAuditor",
    "AuditResult",
    "CategoryResult",
]
