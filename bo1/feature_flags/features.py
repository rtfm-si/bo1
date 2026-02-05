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

# Enable LinkedIn OAuth provider in SuperTokens
LINKEDIN_OAUTH_ENABLED = _parse_bool(os.getenv("LINKEDIN_OAUTH_ENABLED"), default=True)

# Enable GitHub OAuth provider in SuperTokens
GITHUB_OAUTH_ENABLED = _parse_bool(os.getenv("GITHUB_OAUTH_ENABLED"), default=True)

# Enable Twitter/X OAuth provider in SuperTokens
TWITTER_OAUTH_ENABLED = _parse_bool(os.getenv("TWITTER_OAUTH_ENABLED"), default=False)

# Enable Bluesky OAuth provider (AT Protocol) in SuperTokens
BLUESKY_OAUTH_ENABLED = _parse_bool(os.getenv("BLUESKY_OAUTH_ENABLED"), default=False)

# Enable Passwordless (Magic Link) authentication in SuperTokens
MAGIC_LINK_ENABLED = _parse_bool(os.getenv("MAGIC_LINK_ENABLED"), default=True)


# ============================================================================
# Parallel Processing
# ============================================================================

# Enable parallel multi-expert rounds (all experts contribute simultaneously)
# When False, experts contribute sequentially
# Default to True (stable feature)
ENABLE_PARALLEL_ROUNDS = _parse_bool(os.getenv("ENABLE_PARALLEL_ROUNDS"), default=True)

# Enable speculative parallel execution with early context sharing
# When True, dependent sub-problems can start early (when dependencies reach round 2)
# instead of waiting for full completion. This can provide 40-60% time savings.
# When False, falls back to strict sequential batch execution
# Default to True (recommended for multi-sub-problem deliberations)
ENABLE_SPECULATIVE_PARALLELISM = _parse_bool(
    os.getenv("ENABLE_SPECULATIVE_PARALLELISM"), default=True
)

# Early start threshold: number of completed rounds before dependent SPs can start
# Lower values = more parallelism but less context available
# Recommended: 2 (after exploration phase completes)
# Range: 1-3 (1 = aggressive parallelism, 3 = conservative)
EARLY_START_THRESHOLD = int(os.getenv("EARLY_START_THRESHOLD", "2"))


# ============================================================================
# Cost Optimization
# ============================================================================

# Use Haiku for persona selection on simple/moderate problems (complexity 1-6)
# When True: Haiku for complexity 1-6, Sonnet for 7-10 (~10x cheaper for simple problems)
# When False: Always use Sonnet (legacy behavior)
USE_HAIKU_FOR_SIMPLE_PERSONAS = _parse_bool(
    os.getenv("USE_HAIKU_FOR_SIMPLE_PERSONAS"), default=True
)


# ============================================================================
# Sub-Problem Deliberation
# ============================================================================

# Use LangGraph subgraph for sub-problem deliberation
# When True, uses get_stream_writer() for real-time event streaming
# When False, uses legacy EventBridge approach
USE_SUBGRAPH_DELIBERATION = _parse_bool(os.getenv("USE_SUBGRAPH_DELIBERATION"), default=True)


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
