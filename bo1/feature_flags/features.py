"""Feature flags for gradual rollout of new features.

This module provides feature flags that allow enabling/disabling experimental
features without code changes.

Usage:
    from bo1.config.features import ENABLE_PARALLEL_ROUNDS

    if ENABLE_PARALLEL_ROUNDS:
        # Use new parallel architecture
        workflow.add_node("parallel_round", parallel_round_node)
    else:
        # Use legacy serial architecture
        workflow.add_node("persona_contribute", persona_contribute_node)
"""

import os
from typing import Literal

# ============================================================================
# Parallel Multi-Expert Architecture (Day 38)
# ============================================================================

# Enable parallel multi-expert rounds (vs serial 1-expert-per-round)
# Set ENABLE_PARALLEL_ROUNDS=false in environment to disable (for debugging)
ENABLE_PARALLEL_ROUNDS = os.getenv("ENABLE_PARALLEL_ROUNDS", "true").lower() in (
    "true",
    "1",
    "yes",
)

# Log feature flag status on import
if ENABLE_PARALLEL_ROUNDS:
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Feature flag: ENABLE_PARALLEL_ROUNDS = true (NEW parallel architecture)")
else:
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Feature flag: ENABLE_PARALLEL_ROUNDS = false (legacy serial architecture)")


# ============================================================================
# Additional Feature Flags (for future use)
# ============================================================================

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
# Options: "haiku-4.5" (fast, cheap) or "sonnet-4.5" (slower, higher quality)
FACILITATOR_MODEL: Literal["haiku-4.5", "sonnet-4.5"] = os.getenv("FACILITATOR_MODEL", "haiku-4.5")  # type: ignore[assignment]

# Model selection for personas
PERSONA_MODEL: Literal["sonnet-4.5", "haiku-4.5"] = os.getenv("PERSONA_MODEL", "sonnet-4.5")  # type: ignore[assignment]
