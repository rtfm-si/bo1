"""State management models for Board of One.

Defines the deliberation state and contribution tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .types import OptionalScore


class AspectCoverage(BaseModel):
    """Coverage level for a critical decision aspect.

    Used to track exploration depth across 8 critical aspects:
    - problem_clarity, objectives, options_alternatives, key_assumptions
    - risks_failure_modes, constraints, stakeholders_impact, dependencies_unknowns
    """

    name: str = Field(..., description="Aspect name (e.g., 'risks_failure_modes')")
    level: str = Field(
        ...,
        description="Coverage level: 'none', 'shallow', or 'deep'",
        pattern="^(none|shallow|deep)$",
    )
    notes: str = Field(default="", description="Explanation of coverage assessment")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "risks_failure_modes",
                    "level": "deep",
                    "notes": "Maria identified 3 major risks with mitigation strategies",
                },
                {
                    "name": "stakeholders_impact",
                    "level": "shallow",
                    "notes": "Mentioned stakeholders but no detailed impact analysis",
                },
            ]
        }
    )


class SubProblemResult(BaseModel):
    """Result of deliberating a single sub-problem."""

    sub_problem_id: str = Field(..., description="Sub-problem ID")
    sub_problem_goal: str = Field(..., description="Sub-problem goal statement")
    synthesis: str = Field(..., description="Final synthesis report for this sub-problem")
    votes: list[Any] = Field(default_factory=list, description="Votes from personas (Vote objects)")
    contribution_count: int = Field(..., description="Number of contributions made")
    cost: float = Field(..., description="Total cost for this sub-problem deliberation (USD)")
    duration_seconds: float = Field(..., description="Duration of deliberation in seconds")
    expert_panel: list[str] = Field(
        default_factory=list, description="Persona codes of experts who deliberated"
    )
    expert_summaries: dict[str, str] = Field(
        default_factory=dict,
        description="Per-expert contribution summaries for memory (persona_code → 50-100 token summary)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "sub_problem_id": "sp_001",
                    "sub_problem_goal": "Determine target CAC for acquisition channels",
                    "synthesis": "Based on deliberation, target CAC should be <$150...",
                    "votes": [],
                    "contribution_count": 15,
                    "cost": 0.12,
                    "duration_seconds": 180.5,
                    "expert_panel": ["maria", "zara", "chen"],
                    "expert_summaries": {
                        "maria": "Maria recommended CAC <$150 based on $40 MRR...",
                        "zara": "Zara emphasized testing paid channels first...",
                    },
                }
            ]
        }
    )


class DeliberationPhase(str, Enum):
    """Current phase of the deliberation process."""

    INTAKE = "intake"  # Problem intake and clarification
    DECOMPOSITION = "decomposition"  # Breaking down the problem
    SELECTION = "selection"  # Selecting expert personas
    INITIAL_ROUND = "initial_round"  # First round of contributions
    DISCUSSION = "discussion"  # Multi-round debate
    VOTING = "voting"  # Voting phase
    SYNTHESIS = "synthesis"  # Final synthesis
    COMPLETE = "complete"  # Deliberation finished


class ContributionType(str, Enum):
    """Type of contribution in the deliberation."""

    INITIAL = "initial"  # Initial contribution (first round)
    RESPONSE = "response"  # Response to previous contributions
    MODERATOR = "moderator"  # Moderator intervention
    FACILITATOR = "facilitator"  # Facilitator guidance
    RESEARCH = "research"  # Research findings
    VOTE = "vote"  # Vote contribution


class ContributionMessage(BaseModel):
    """A single contribution from a persona in the deliberation."""

    persona_code: str = Field(..., description="Code of the persona making this contribution")
    persona_name: str = Field(..., description="Display name of the persona")
    content: str = Field(..., description="The contribution content (markdown)")
    thinking: str | None = Field(
        None, description="Internal thinking process (from <thinking> tag)"
    )
    contribution_type: ContributionType = Field(
        default=ContributionType.INITIAL, description="Type of contribution"
    )
    round_number: int = Field(..., ge=0, description="Round number (0 = initial)")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this was created")
    token_count: int | None = Field(None, description="Token count for this contribution")
    cost: float | None = Field(None, description="Cost in USD for generating this contribution")

    @property
    def tokens_used(self) -> int:
        """Alias for token_count for backward compatibility."""
        return self.token_count or 0

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "persona_code": "growth_hacker",
                    "persona_name": "Zara",
                    "content": "I recommend focusing on product-led growth...",
                    "thinking": "Let me analyze the growth channels...",
                    "contribution_type": "initial",
                    "round_number": 0,
                    "timestamp": "2024-01-15T10:30:00",
                    "token_count": 250,
                    "cost": 0.0015,
                }
            ]
        }
    )


class DeliberationMetrics(BaseModel):
    """Metrics tracking for the deliberation.

    Includes both existing metrics (convergence, novelty, conflict) and new quality metrics:
    - exploration_score: Coverage of 8 critical decision aspects (0-1)
    - focus_score: Continuous on-topic ratio (0-1)
    - meeting_completeness_index: Composite quality metric (0-1, 70%+ = high quality)
    """

    total_cost: float = Field(default=0.0, description="Total cost in USD")
    total_tokens: int = Field(default=0, description="Total tokens used")
    cache_hits: int = Field(default=0, description="Number of cache hits")
    cache_creation_tokens: int = Field(default=0, description="Tokens used to create cache")
    cache_read_tokens: int = Field(default=0, description="Tokens read from cache")
    phase_costs: dict[str, float] = Field(
        default_factory=dict,
        description="Cost breakdown by phase (e.g., problem_decomposition, persona_selection)",
    )
    convergence_score: OptionalScore = Field(
        default=None, description="Semantic convergence score (0-1)"
    )
    novelty_score: OptionalScore = Field(
        default=None, description="Average novelty of recent contributions (0-1)"
    )
    conflict_score: OptionalScore = Field(default=None, description="Level of disagreement (0-1)")
    drift_events: int = Field(default=0, description="Number of problem drift events detected")

    # New quality metrics (Meeting Quality Enhancement)
    exploration_score: OptionalScore = Field(
        default=None,
        description="Exploration coverage score (0-1). Measures depth of coverage across 8 critical aspects. 0.6+ required to end, 0.7+ = well explored",
    )
    focus_score: OptionalScore = Field(
        default=None,
        description="Focus score (0-1). Continuous on-topic ratio. >0.80 = core focus, 0.60-0.80 = context, <0.60 = drift",
    )
    meeting_completeness_index: OptionalScore = Field(
        default=None,
        description="Meeting completeness index (0-1). Composite quality metric: M_r = wE*E_r + wC*C_r + wF*F_r + wN*(1-N_r). 0.7+ = high quality, can recommend ending",
    )
    aspect_coverage: list[AspectCoverage] = Field(
        default_factory=list,
        description="Detailed coverage assessment for each of the 8 critical aspects",
    )
