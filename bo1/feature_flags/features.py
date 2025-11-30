"""Feature flags for gradual rollout of new features.

This module provides feature flags that allow enabling/disabling experimental
features without code changes.

All feature flags are centralized here - DO NOT create feature flags in other files.
"""

import os
from typing import Literal


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
# Caching & Optimization
# ============================================================================

# Enable LLM response caching with Redis backend
# Expected 60-80% cost reduction on repeated queries
ENABLE_LLM_RESPONSE_CACHE = _parse_bool(os.getenv("ENABLE_LLM_RESPONSE_CACHE"), default=False)

# Enable semantic persona selection caching
# Expected 40-60% hit rate, $200-400/month savings
ENABLE_PERSONA_SELECTION_CACHE = _parse_bool(
    os.getenv("ENABLE_PERSONA_SELECTION_CACHE"), default=False
)

# Enable semantic research cache with pgvector
ENABLE_SEMANTIC_RESEARCH_CACHE = _parse_bool(
    os.getenv("ENABLE_SEMANTIC_RESEARCH_CACHE"), default=True
)


# ============================================================================
# Quality & Analysis
# ============================================================================

# Enable enhanced quality metrics (exploration, focus, completeness)
ENABLE_ENHANCED_QUALITY_METRICS = _parse_bool(
    os.getenv("ENABLE_ENHANCED_QUALITY_METRICS"), default=True
)

# Enable business context collection and information gap analysis
# Improves recommendations by 40%
ENABLE_CONTEXT_COLLECTION = _parse_bool(os.getenv("ENABLE_CONTEXT_COLLECTION"), default=True)


# ============================================================================
# Streaming & Real-time Updates
# ============================================================================

# Enable real-time SSE streaming via LangGraph astream_events (vs polling)
# See STREAMING_IMPLEMENTATION_PLAN.md
ENABLE_SSE_STREAMING = _parse_bool(os.getenv("ENABLE_SSE_STREAMING"), default=False)


# ============================================================================
# Model Selection
# ============================================================================

# Model selection for facilitator
# Options: "haiku" (fast, cheap) or "sonnet" (slower, higher quality)
# These aliases are resolved to full model IDs in bo1/config.py
FACILITATOR_MODEL: Literal["haiku", "sonnet"] = os.getenv("FACILITATOR_MODEL", "haiku")  # type: ignore[assignment]

# Model selection for personas
PERSONA_MODEL: Literal["sonnet", "haiku"] = os.getenv("PERSONA_MODEL", "sonnet")  # type: ignore[assignment]
