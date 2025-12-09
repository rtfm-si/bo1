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


class DeliberationPhaseType(str, Enum):
    """Phase of the deliberation within a round.

    These map to the DB `phase` column in the contributions table.
    Distinct from ContributionType (what kind) and DeliberationPhase (workflow stage).
    """

    EXPLORATION = "exploration"  # Initial exploration of the problem space
    CHALLENGE = "challenge"  # Critical examination and debate
    CONVERGENCE = "convergence"  # Moving toward consensus


class ContributionMessage(BaseModel):
    """A single contribution from a persona in the deliberation.

    Aligned with DB contributions table schema. New fields are optional
    for backward compatibility.
    """

    # Core fields (required)
    persona_code: str = Field(..., description="Code of the persona making this contribution")
    persona_name: str = Field(..., description="Display name of the persona")
    content: str = Field(..., description="The contribution content (markdown)")
    round_number: int = Field(..., ge=0, description="Round number (0 = initial)")

    # Optional fields from original model
    thinking: str | None = Field(
        None, description="Internal thinking process (from <thinking> tag)"
    )
    contribution_type: ContributionType = Field(
        default=ContributionType.INITIAL, description="Type of contribution"
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="When this was created")
    token_count: int | None = Field(None, description="Token count for this contribution")
    cost: float | None = Field(None, description="Cost in USD for generating this contribution")

    # New fields aligned with DB schema
    id: int | None = Field(default=None, description="DB row ID (assigned by database)")
    session_id: str | None = Field(default=None, description="Session FK (set on persist)")
    model: str | None = Field(
        default=None, description="LLM model used (e.g., claude-sonnet-4-20250514)"
    )
    phase: DeliberationPhaseType | str | None = Field(
        default=None, description="Deliberation phase (exploration/challenge/convergence)"
    )
    embedding: list[float] | None = Field(
        default=None, description="Voyage embedding vector (1024 dims)", exclude=True
    )

    @property
    def tokens_used(self) -> int:
        """Alias for token_count for backward compatibility."""
        return self.token_count or 0

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "ContributionMessage":
        """Create ContributionMessage from database row dict.

        Args:
            row: Dict from psycopg2 cursor with contributions table columns

        Returns:
            ContributionMessage instance with mapped fields

        Example:
            >>> row = {"id": 1, "session_id": "bo1_123", "persona_code": "ceo", ...}
            >>> msg = ContributionMessage.from_db_row(row)
        """
        # Convert phase string to enum if present
        phase_str = row.get("phase")
        phase_enum: DeliberationPhaseType | None = None
        if phase_str:
            try:
                phase_enum = DeliberationPhaseType(phase_str)
            except ValueError:
                pass  # Keep as None if invalid phase value

        return cls(
            id=row.get("id"),
            session_id=row.get("session_id"),
            persona_code=row["persona_code"],
            persona_name=row.get("persona_name", row["persona_code"]),  # Fallback to code
            content=row["content"],
            round_number=row["round_number"],
            thinking=row.get("thinking"),
            phase=phase_enum,
            cost=float(row.get("cost", 0)) if row.get("cost") is not None else None,
            token_count=row.get("tokens"),  # DB column is 'tokens', model is 'token_count'
            model=row.get("model"),
            embedding=row.get("embedding"),
            # contribution_type not in DB, default to RESPONSE for existing data
            contribution_type=ContributionType.RESPONSE,
            timestamp=row.get("created_at", datetime.now()),
        )

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
    # P2 FIX: Judge feedback for next round - enables exploration score improvement
    next_round_focus_prompts: list[str] = Field(
        default_factory=list,
        description="Targeted prompts from Judge for aspects needing deeper exploration",
    )
    missing_critical_aspects: list[str] = Field(
        default_factory=list,
        description="Aspect names with 'none' or 'shallow' coverage that need attention",
    )

    # Complexity scoring (Adaptive deliberation parameters)
    complexity_score: OptionalScore = Field(
        default=None,
        description="Overall problem complexity (0-1). Drives adaptive round limits and expert selection.",
    )
    scope_breadth: OptionalScore = Field(
        default=None,
        description="Scope breadth dimension (0-1). How many distinct domains involved?",
    )
    dependencies: OptionalScore = Field(
        default=None, description="Dependencies dimension (0-1). How interconnected are factors?"
    )
    ambiguity: OptionalScore = Field(
        default=None, description="Ambiguity dimension (0-1). How clear are requirements?"
    )
    stakeholders_complexity: OptionalScore = Field(
        default=None, description="Stakeholders dimension (0-1). How many parties affected?"
    )
    novelty: OptionalScore = Field(
        default=None, description="Novelty dimension (0-1). How novel/unprecedented is the problem?"
    )
    recommended_rounds: int | None = Field(
        default=None, description="Recommended max rounds based on complexity (3-6)"
    )
    recommended_experts: int | None = Field(
        default=None, description="Recommended experts per round based on complexity (3-5)"
    )
    complexity_reasoning: str | None = Field(
        default=None, description="Brief explanation of complexity assessment"
    )
