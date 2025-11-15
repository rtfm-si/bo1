"""Voting models for Board of One.

DEPRECATED: Use bo1.models.recommendations instead.
This file is kept only for backward compatibility with old imports.
"""

# Re-export everything from recommendations
from bo1.models.recommendations import (
    ConsensusLevel,
    Recommendation,
    RecommendationAggregation,
)

# Legacy aliases - use Recommendation directly instead
Vote = Recommendation
VoteAggregation = RecommendationAggregation

__all__ = [
    "Vote",
    "VoteAggregation",
    "ConsensusLevel",
    "Recommendation",
    "RecommendationAggregation",
]
