"""Typed Pydantic schemas for all Board of One SSE events.

These schemas mirror the TypeScript interfaces in frontend/src/lib/api/sse-events.ts
and provide runtime validation for event data.

Usage:
    >>> from bo1.events import SubProblemStartedEvent
    >>> event = SubProblemStartedEvent(
    ...     session_id="bo1_abc123",
    ...     sub_problem_index=0,
    ...     sub_problem_id="sp1",
    ...     goal="Analyze market opportunity",
    ...     total_sub_problems=3,
    ... )
    >>> event.model_dump()
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BaseEvent(BaseModel):
    """Base class for all SSE events."""

    event_type: str = Field(..., description="Event type identifier")
    session_id: str = Field(..., description="Session identifier")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 timestamp",
    )
    sub_problem_index: int | None = Field(
        default=None, description="Sub-problem index (0-based) if applicable"
    )

    model_config = ConfigDict(
        extra="allow",  # Allow additional fields for extensibility
    )


# ============================================================================
# Session Events
# ============================================================================


class SessionStartedEvent(BaseEvent):
    """Emitted when a deliberation session starts."""

    event_type: Literal["session_started"] = "session_started"
    problem_statement: str = Field(..., description="The problem being deliberated")
    max_rounds: int = Field(..., ge=1, le=10, description="Maximum rounds allowed")
    user_id: str = Field(..., description="User who started the session")


# ============================================================================
# Decomposition Events
# ============================================================================


class SubProblemSchema(BaseModel):
    """Schema for sub-problem data in events."""

    id: str
    goal: str
    rationale: str = ""
    complexity_score: int = Field(ge=1, le=10)
    dependencies: list[str] = Field(default_factory=list)


class DecompositionCompleteEvent(BaseEvent):
    """Emitted when problem decomposition completes."""

    event_type: Literal["decomposition_complete"] = "decomposition_complete"
    sub_problems: list[SubProblemSchema] = Field(..., description="Decomposed sub-problems")
    count: int = Field(..., ge=0, description="Number of sub-problems")


# ============================================================================
# Persona Selection Events
# ============================================================================


class PersonaSchema(BaseModel):
    """Schema for persona data in events."""

    code: str
    name: str
    display_name: str = ""
    archetype: str = ""
    domain_expertise: list[str] = Field(default_factory=list)


class PersonaSelectedEvent(BaseEvent):
    """Emitted when a persona is selected for deliberation."""

    event_type: Literal["persona_selected"] = "persona_selected"
    persona: PersonaSchema = Field(..., description="Selected persona")
    rationale: str = Field(..., description="Why this persona was selected")
    order: int = Field(..., ge=1, description="Selection order (1-based)")


class PersonaSelectionCompleteEvent(BaseEvent):
    """Emitted when all personas have been selected."""

    event_type: Literal["persona_selection_complete"] = "persona_selection_complete"
    personas: list[PersonaSchema] = Field(..., description="All selected personas")
    count: int = Field(..., ge=0, description="Number of personas selected")


# ============================================================================
# Sub-Problem Events
# ============================================================================


class SubProblemStartedEvent(BaseEvent):
    """Emitted when a sub-problem deliberation begins.

    CRITICAL: This event must be emitted immediately when parallel sub-problem
    execution starts, so the frontend knows deliberation is in progress.
    """

    event_type: Literal["subproblem_started"] = "subproblem_started"
    sub_problem_index: int = Field(..., ge=0, description="Sub-problem index (0-based)")
    sub_problem_id: str = Field(..., description="Sub-problem unique ID")
    goal: str = Field(..., description="Goal of this sub-problem")
    total_sub_problems: int = Field(..., ge=1, description="Total number of sub-problems")


class SubProblemCompleteEvent(BaseEvent):
    """Emitted when a sub-problem deliberation completes."""

    event_type: Literal["subproblem_complete"] = "subproblem_complete"
    sub_problem_index: int = Field(..., ge=0, description="Sub-problem index (0-based)")
    sub_problem_id: str = Field(default="", description="Sub-problem unique ID")
    goal: str = Field(..., description="Goal of this sub-problem")
    synthesis: str = Field(..., description="Synthesis for this sub-problem")
    cost: float = Field(..., ge=0, description="Cost in USD")
    duration_seconds: float = Field(..., ge=0, description="Duration in seconds")
    expert_panel: list[str] = Field(default_factory=list, description="Expert codes")
    contribution_count: int = Field(..., ge=0, description="Number of contributions")


# ============================================================================
# Round Events
# ============================================================================


class RoundStartedEvent(BaseEvent):
    """Emitted when a deliberation round begins."""

    event_type: Literal["round_started"] = "round_started"
    round_number: int = Field(..., ge=1, description="Round number (1-based)")


class ContributionSummary(BaseModel):
    """Structured summary of a contribution."""

    concise: str = Field(default="", description="One-sentence summary")
    looking_for: str = Field(default="", description="What the expert is looking for")
    value_added: str = Field(default="", description="Value this contribution adds")
    concerns: list[str] = Field(default_factory=list, description="Key concerns raised")
    questions: list[str] = Field(default_factory=list, description="Questions posed")


class ContributionEvent(BaseEvent):
    """Emitted when an expert makes a contribution."""

    event_type: Literal["contribution"] = "contribution"
    persona_code: str = Field(..., description="Expert persona code")
    persona_name: str = Field(..., description="Expert display name")
    content: str = Field(..., description="Full contribution content")
    round: int = Field(..., ge=1, description="Round number")
    contribution_type: Literal["initial", "followup"] = Field(
        ..., description="Type of contribution"
    )
    archetype: str = Field(default="", description="Expert archetype")
    domain_expertise: list[str] = Field(default_factory=list, description="Expert domains")
    summary: ContributionSummary | None = Field(
        default=None, description="Structured summary (optional)"
    )


# ============================================================================
# Convergence Events
# ============================================================================


class ConvergenceEvent(BaseEvent):
    """Emitted when convergence is checked."""

    event_type: Literal["convergence"] = "convergence"
    converged: bool = Field(..., description="Whether convergence was reached")
    score: float = Field(..., ge=0, le=1, description="Convergence score")
    threshold: float = Field(..., ge=0, le=1, description="Convergence threshold")
    should_stop: bool = Field(..., description="Whether deliberation should stop")
    stop_reason: str | None = Field(default=None, description="Reason for stopping")
    round: int = Field(..., ge=1, description="Current round")
    max_rounds: int = Field(..., ge=1, description="Maximum rounds")
    novelty_score: float | None = Field(default=None, description="Novelty score")
    conflict_score: float | None = Field(default=None, description="Conflict score")
    drift_events: int = Field(default=0, ge=0, description="Number of drift events")


# ============================================================================
# Voting Events
# ============================================================================


class VotingStartedEvent(BaseEvent):
    """Emitted when voting begins."""

    event_type: Literal["voting_started"] = "voting_started"
    experts: list[str] = Field(..., description="Expert codes participating")
    count: int = Field(..., ge=0, description="Number of experts")


class VotingCompleteEvent(BaseEvent):
    """Emitted when voting completes."""

    event_type: Literal["voting_complete"] = "voting_complete"
    votes_count: int = Field(..., ge=0, description="Number of votes cast")
    consensus_level: Literal["strong", "moderate", "weak"] = Field(
        ..., description="Level of consensus"
    )


# ============================================================================
# Synthesis Events
# ============================================================================


class SynthesisCompleteEvent(BaseEvent):
    """Emitted when synthesis completes for a sub-problem."""

    event_type: Literal["synthesis_complete"] = "synthesis_complete"
    synthesis: str = Field(..., description="Synthesis content")
    word_count: int = Field(..., ge=0, description="Word count of synthesis")


class MetaSynthesisCompleteEvent(BaseEvent):
    """Emitted when meta-synthesis (across all sub-problems) completes."""

    event_type: Literal["meta_synthesis_complete"] = "meta_synthesis_complete"
    synthesis: str = Field(..., description="Final meta-synthesis content")
    word_count: int = Field(..., ge=0, description="Word count of synthesis")


# ============================================================================
# Error Events
# ============================================================================


class ErrorEvent(BaseEvent):
    """Emitted when an error occurs during deliberation."""

    event_type: Literal["error"] = "error"
    error: str = Field(..., description="Error message")
    error_type: str = Field(default="UnknownError", description="Error type/class name")
    node: str | None = Field(default=None, description="Graph node where error occurred")
    recoverable: bool = Field(default=False, description="Whether the error is recoverable")
    sub_problem_goal: str | None = Field(
        default=None, description="Goal of failed sub-problem if applicable"
    )


# ============================================================================
# Type Union
# ============================================================================

DeliberationEvent = (
    SessionStartedEvent
    | DecompositionCompleteEvent
    | PersonaSelectedEvent
    | PersonaSelectionCompleteEvent
    | SubProblemStartedEvent
    | SubProblemCompleteEvent
    | RoundStartedEvent
    | ContributionEvent
    | ConvergenceEvent
    | VotingStartedEvent
    | VotingCompleteEvent
    | SynthesisCompleteEvent
    | MetaSynthesisCompleteEvent
    | ErrorEvent
)
