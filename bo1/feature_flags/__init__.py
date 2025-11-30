"""Feature flags package for Board of One.

All feature flags are centralized in this package for easy management and discovery.
Import flags from here rather than directly from features.py.
"""

from .features import (
    ENABLE_CONTEXT_COLLECTION,
    ENABLE_ENHANCED_QUALITY_METRICS,
    ENABLE_LLM_RESPONSE_CACHE,
    ENABLE_PARALLEL_ROUNDS,
    ENABLE_PARALLEL_SUBPROBLEMS,
    ENABLE_PERSONA_SELECTION_CACHE,
    ENABLE_SEMANTIC_RESEARCH_CACHE,
    ENABLE_SSE_STREAMING,
    ENABLE_SUPERTOKENS_AUTH,
    FACILITATOR_MODEL,
    GOOGLE_OAUTH_ENABLED,
    PERSONA_MODEL,
    USE_SUBGRAPH_DELIBERATION,
)

__all__ = [
    # Authentication & Authorization
    "ENABLE_SUPERTOKENS_AUTH",
    # OAuth Providers
    "GOOGLE_OAUTH_ENABLED",
    # Parallel Processing
    "ENABLE_PARALLEL_SUBPROBLEMS",
    "ENABLE_PARALLEL_ROUNDS",
    # Sub-Problem Deliberation
    "USE_SUBGRAPH_DELIBERATION",
    # Caching & Optimization
    "ENABLE_LLM_RESPONSE_CACHE",
    "ENABLE_PERSONA_SELECTION_CACHE",
    "ENABLE_SEMANTIC_RESEARCH_CACHE",
    # Quality & Analysis
    "ENABLE_ENHANCED_QUALITY_METRICS",
    "ENABLE_CONTEXT_COLLECTION",
    # Streaming & Real-time Updates
    "ENABLE_SSE_STREAMING",
    # Model Selection
    "FACILITATOR_MODEL",
    "PERSONA_MODEL",
]
