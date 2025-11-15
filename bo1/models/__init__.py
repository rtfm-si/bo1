"""Domain models for Board of One."""

from .persona import (
    PersonaCategory,
    PersonaProfile,
    PersonaTraits,
    PersonaType,
    ResponseStyle,
)
from .problem import Constraint, ConstraintType, Problem, SubProblem
from .recommendations import (
    ConsensusLevel,
    Recommendation,
    RecommendationAggregation,
)
from .state import (
    ContributionMessage,
    ContributionType,
    DeliberationMetrics,
    DeliberationPhase,
    DeliberationState,
)

# Legacy aliases
from .votes import Vote, VoteAggregation

__all__ = [
    # Persona models
    "PersonaProfile",
    "PersonaTraits",
    "PersonaType",
    "PersonaCategory",
    "ResponseStyle",
    # Problem models
    "Problem",
    "SubProblem",
    "Constraint",
    "ConstraintType",
    # State models
    "DeliberationState",
    "DeliberationPhase",
    "DeliberationMetrics",
    "ContributionMessage",
    "ContributionType",
    # Recommendation models
    "Recommendation",
    "RecommendationAggregation",
    "ConsensusLevel",
    # Legacy aliases
    "Vote",
    "VoteAggregation",
]
