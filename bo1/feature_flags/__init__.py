"""Feature flags package for Board of One.

All feature flags are centralized in this package for easy management and discovery.
Import flags from here rather than directly from features.py.
"""

from .features import (
    BLUESKY_OAUTH_ENABLED,
    EARLY_START_THRESHOLD,
    ENABLE_PARALLEL_ROUNDS,
    ENABLE_PARALLEL_SUBPROBLEMS,
    ENABLE_SPECULATIVE_PARALLELISM,
    ENABLE_SUPERTOKENS_AUTH,
    GITHUB_OAUTH_ENABLED,
    GOOGLE_OAUTH_ENABLED,
    LINKEDIN_OAUTH_ENABLED,
    MAGIC_LINK_ENABLED,
    TWITTER_OAUTH_ENABLED,
    USE_SUBGRAPH_DELIBERATION,
)

__all__ = [
    # Authentication & Authorization
    "ENABLE_SUPERTOKENS_AUTH",
    "MAGIC_LINK_ENABLED",
    # OAuth Providers
    "BLUESKY_OAUTH_ENABLED",
    "GITHUB_OAUTH_ENABLED",
    "GOOGLE_OAUTH_ENABLED",
    "LINKEDIN_OAUTH_ENABLED",
    "TWITTER_OAUTH_ENABLED",
    # Parallel Processing
    "ENABLE_PARALLEL_SUBPROBLEMS",
    "ENABLE_PARALLEL_ROUNDS",
    "ENABLE_SPECULATIVE_PARALLELISM",
    "EARLY_START_THRESHOLD",
    # Sub-Problem Deliberation
    "USE_SUBGRAPH_DELIBERATION",
]
