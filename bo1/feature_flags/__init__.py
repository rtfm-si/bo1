"""Feature flags package for Board of One.

All feature flags are centralized in this package for easy management and discovery.
Import flags from here rather than directly from features.py.
"""

from .features import (
    ENABLE_PARALLEL_ROUNDS,
    ENABLE_PARALLEL_SUBPROBLEMS,
    ENABLE_SUPERTOKENS_AUTH,
    GOOGLE_OAUTH_ENABLED,
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
]
