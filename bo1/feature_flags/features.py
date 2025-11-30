"""Feature flags for gradual rollout of new features.

This module provides feature flags that allow enabling/disabling experimental
features without code changes.

All feature flags are centralized here - DO NOT create feature flags in other files.
"""

import os


def _parse_bool(value: str | None, default: bool = False) -> bool:
    """Parse boolean from environment variable.

    Args:
        value: Environment variable value (or None)
        default: Default value if env var is not set

    Returns:
        Boolean value parsed from string

    Examples:
        >>> _parse_bool("true")
        True
        >>> _parse_bool("1")
        True
        >>> _parse_bool("yes")
        True
        >>> _parse_bool("false")
        False
        >>> _parse_bool("", default=True)
        True
        >>> _parse_bool(None, default=False)
        False
    """
    if value is None or value == "":
        return default
    return value.lower() in ("true", "1", "yes")


# ============================================================================
# Authentication & Authorization
# ============================================================================

# Enable SuperTokens authentication (enabled for production)
# When False, uses hardcoded test_user_1 (only allowed when DEBUG=true)
ENABLE_SUPERTOKENS_AUTH = _parse_bool(os.getenv("ENABLE_SUPERTOKENS_AUTH"), default=True)


# ============================================================================
# OAuth Providers
# ============================================================================

# Enable Google OAuth provider in SuperTokens
GOOGLE_OAUTH_ENABLED = _parse_bool(os.getenv("GOOGLE_OAUTH_ENABLED"), default=True)


# ============================================================================
# Parallel Processing
# ============================================================================

# Enable parallel sub-problem execution (independent sub-problems run concurrently)
# When False, falls back to sequential execution
# Default to False initially for safe rollout
# Expected 50-70% time reduction for problems with 2+ independent sub-problems
ENABLE_PARALLEL_SUBPROBLEMS = _parse_bool(os.getenv("ENABLE_PARALLEL_SUBPROBLEMS"), default=False)

# Enable parallel multi-expert rounds (all experts contribute simultaneously)
# When False, experts contribute sequentially
# Default to True (stable feature)
ENABLE_PARALLEL_ROUNDS = _parse_bool(os.getenv("ENABLE_PARALLEL_ROUNDS"), default=True)


# ============================================================================
# Sub-Problem Deliberation
# ============================================================================

# Use LangGraph subgraph for sub-problem deliberation
# When True, uses get_stream_writer() for real-time event streaming
# When False, uses legacy EventBridge approach
# Default to False initially for safe rollout
# Requires ENABLE_PARALLEL_SUBPROBLEMS=true to have effect
USE_SUBGRAPH_DELIBERATION = _parse_bool(os.getenv("USE_SUBGRAPH_DELIBERATION"), default=False)


# ============================================================================
# REMOVED: Unused Feature Flags (2025-11-30)
# ============================================================================
# The following flags were removed as they had no implementation:
# - ENABLE_LLM_RESPONSE_CACHE (no caching logic wired up)
# - ENABLE_PERSONA_SELECTION_CACHE (no caching logic wired up)
# - ENABLE_SEMANTIC_RESEARCH_CACHE (no caching logic wired up)
# - ENABLE_ENHANCED_QUALITY_METRICS (no quality metrics implementation)
# - ENABLE_CONTEXT_COLLECTION (no context collection implementation)
# - ENABLE_SSE_STREAMING (superseded by USE_SUBGRAPH_DELIBERATION)
# - FACILITATOR_MODEL (model selection handled via AI_OVERRIDE in config.py)
# - PERSONA_MODEL (model selection handled via AI_OVERRIDE in config.py)
#
# Model selection is now controlled via bo1/config.py:
# - AI_OVERRIDE=true/false
# - AI_OVERRIDE_MODEL=<model_alias>
# ============================================================================
