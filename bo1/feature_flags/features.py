"""Feature flags for gradual rollout of new features.

This module provides feature flags that allow enabling/disabling experimental
features without code changes.
"""

import os
from typing import Literal

# ============================================================================
# Additional Feature Flags (for future use)
# ============================================================================

# Enable parallel sub-problem execution
# When False, falls back to sequential execution (current behavior)
# Default to False initially for safe rollout
ENABLE_PARALLEL_SUBPROBLEMS = os.getenv("ENABLE_PARALLEL_SUBPROBLEMS", "false").lower() in (
    "true",
    "1",
    "yes",
)

# Enable semantic research cache with pgvector
ENABLE_SEMANTIC_RESEARCH_CACHE = os.getenv("ENABLE_SEMANTIC_RESEARCH_CACHE", "true").lower() in (
    "true",
    "1",
    "yes",
)

# Enable enhanced quality metrics (exploration, focus, completeness)
ENABLE_ENHANCED_QUALITY_METRICS = os.getenv("ENABLE_ENHANCED_QUALITY_METRICS", "true").lower() in (
    "true",
    "1",
    "yes",
)

# Model selection for facilitator
# Options: "haiku" (fast, cheap) or "sonnet" (slower, higher quality)
# These aliases are resolved to full model IDs in bo1/config.py
FACILITATOR_MODEL: Literal["haiku", "sonnet"] = os.getenv("FACILITATOR_MODEL", "haiku")  # type: ignore[assignment]

# Model selection for personas
PERSONA_MODEL: Literal["sonnet", "haiku"] = os.getenv("PERSONA_MODEL", "sonnet")  # type: ignore[assignment]
