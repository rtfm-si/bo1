"""Graph state models for LangGraph-based deliberation.

This module defines the TypedDict state for LangGraph (DeliberationGraphState).

State is organized into logical groups:
- ProblemState: Problem context and sub-problem tracking
- PhaseState: Deliberation phase and round tracking
- ParticipantState: Personas and expert assignments
- DiscussionState: Contributions, summaries, votes, synthesis
- ResearchState: Research queries and results
- ComparisonState: X vs Y comparison detection
- ContextState: Business context and clarification handling
- ControlState: Termination and stop signals
- MetricsState: Quality metrics and cost tracking
- ParallelState: Parallel sub-problem execution
- DataState: Dataset attachments and analysis results
"""

import logging
from typing import Any, TypedDict

from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import (
    ContributionMessage,
    DeliberationMetrics,
    DeliberationPhase,
    SubProblemResult,
)

logger = logging.getLogger(__name__)

# =============================================================================
# NESTED STATE TYPEDDICTS
# =============================================================================


class ProblemState(TypedDict, total=False):
    """Problem context and sub-problem tracking."""

    problem: Problem
    current_sub_problem: SubProblem | None
    sub_problem_results: list[SubProblemResult]
    sub_problem_index: int


class PhaseState(TypedDict, total=False):
    """Deliberation phase and round tracking.

    Note on phase vs current_phase:
    - phase (DeliberationPhase): Graph lifecycle enum (INTAKE→DECOMPOSITION→DISCUSSION→
      SYNTHESIS→COMPLETE). Set by nodes/routers, consumed by routers for edge decisions.
    - current_phase (str): Within-round prompt phase ("exploration"/"challenge"/"convergence").
      Set by PhaseManager in quality/metrics.py, consumed by prompt builders for tone guidance.
    """

    phase: DeliberationPhase  # Producer: nodes/routers | Consumer: routers, event_collector
    current_phase: str  # Producer: PhaseManager | Consumer: prompt builders
    round_number: int  # Producer: facilitator_decide, check_convergence | Consumer: most nodes
    max_rounds: int  # Producer: create_initial_state | Consumer: facilitator, convergence
    current_node: str  # Producer: each node | Consumer: event_collector, resume logic


class ParticipantState(TypedDict, total=False):
    """Personas and expert assignments."""

    personas: list[PersonaProfile]
    experts_per_round: list[list[str]]


class DiscussionState(TypedDict, total=False):
    """Contributions, summaries, votes, synthesis."""

    contributions: list[ContributionMessage]
    round_summaries: list[str]
    votes: list[dict[str, Any]]
    synthesis: str | None


class ResearchState(TypedDict, total=False):
    """Research queries and results."""

    completed_research_queries: list[dict[str, Any]]  # {"query": str, "embedding": list[float]}
    pending_research_queries: list[dict[str, Any]]
    research_results: list[dict[str, Any]]


class ComparisonState(TypedDict, total=False):
    """X vs Y comparison detection."""

    comparison_detected: bool
    comparison_options: list[str]
    comparison_type: str


class ContextState(TypedDict, total=False):
    """Business context and clarification handling."""

    collect_context: bool
    business_context: dict[str, Any] | None
    pending_clarification: dict[str, Any] | None
    clarification_answers: dict[str, str] | None
    context_ids: dict[str, list[str]] | None  # {meetings: [...], actions: [...], datasets: [...]}
    context_insufficient_emitted: bool
    context_insufficiency_info: dict[str, Any] | None
    user_context_choice: str | None  # "continue" | "provide_more" | "end"
    limited_context_mode: bool
    best_effort_prompt_injected: bool


class ControlState(TypedDict, total=False):
    """Termination and stop signals."""

    should_stop: bool
    stop_reason: str | None
    termination_requested: bool
    termination_type: str | None  # blocker_identified, user_cancelled, continue_best_effort
    termination_reason: str | None
    skip_clarification: bool
    # User interjection ("raise hand") during deliberation
    user_interjection: str | None  # User's interjection message
    interjection_responses: list[dict[str, Any]]  # Expert responses to interjection
    needs_interjection_response: bool  # Flag for processing in next round


class MetricsState(TypedDict, total=False):
    """Quality metrics and cost tracking."""

    metrics: DeliberationMetrics
    phase_costs: dict[str, float]
    semantic_novelty_scores: dict[str, float]
    exploration_score: float
    focus_score: float
    consecutive_research_without_improvement: int
    meta_discussion_count: int
    total_contributions_checked: int
    high_conflict_low_novelty_rounds: int


class ParallelState(TypedDict, total=False):
    """Parallel sub-problem execution."""

    execution_batches: list[list[int]]
    parallel_mode: bool
    dependency_error: str | None


class DataState(TypedDict, total=False):
    """Dataset attachments and analysis results."""

    attached_datasets: list[str]
    data_analysis_results: list[dict[str, Any]]


class SubproblemFailure(TypedDict, total=False):
    """Failure tracking for sub-problems that failed to complete.

    Used by routers to signal failures to EventCollector without
    importing API layer dependencies.
    """

    failed_ids: list[str]  # IDs of sub-problems that failed
    failed_goals: list[str]  # Goal descriptions of failed sub-problems
    failed_count: int  # Number of failed sub-problems
    total_count: int  # Total sub-problems expected
    reason: str  # Human-readable failure reason


class CoreState(TypedDict, total=False):
    """Core identity fields for session tracking and access control."""

    session_id: str
    request_id: str | None  # HTTP request ID for log correlation
    user_id: str | None  # For context persistence and user-specific data
    subscription_tier: str | None  # For cost limit enforcement
    research_sharing_consented: bool  # For cross-user research sharing


# =============================================================================
# MAIN STATE CLASS
# =============================================================================


class DeliberationGraphState(TypedDict, total=False):
    """Graph state for LangGraph-based deliberation.

    This state is used by LangGraph nodes and represents the complete
    deliberation state at any point in the execution graph.

    Note: TypedDict with total=False allows optional fields while maintaining
    type safety for LangGraph's state management.

    Field Persistence Matrix
    ========================

    Each field is classified by where it's persisted and what's recoverable on resume/crash:

    REDIS CHECKPOINT (full state, via serialize_state_for_checkpoint):
    +-------------------------+------------------+----------------------------------+
    | Field                   | Type             | Notes                            |
    +-------------------------+------------------+----------------------------------+
    | session_id              | str              | Primary key                      |
    | problem                 | Problem          | Pydantic → dict on serialize     |
    | current_sub_problem     | SubProblem|None  | Pydantic → dict on serialize     |
    | personas                | list[Persona]    | Pydantic → dict on serialize     |
    | contributions           | list[Contrib]    | Pydantic → dict on serialize     |
    | round_summaries         | list[str]        | Pass-through                     |
    | phase                   | DeliberationPhase| Pass-through                     |
    | round_number            | int              | Pass-through                     |
    | max_rounds              | int              | Pass-through                     |
    | metrics                 | DelibMetrics     | Pydantic → dict on serialize     |
    | sub_problem_results     | list[SPResult]   | Pydantic → dict on serialize     |
    | votes                   | list[dict]       | Pass-through                     |
    | synthesis               | str|None         | Pass-through                     |
    | All other fields        | various          | Pass-through (primitives/dicts)  |
    +-------------------------+------------------+----------------------------------+

    POSTGRESQL FALLBACK (partial recovery via save_metadata when Redis down):
    +-------------------------+------------------+----------------------------------+
    | Field                   | DB Column        | Notes                            |
    +-------------------------+------------------+----------------------------------+
    | phase/current_phase     | sessions.phase   | str                              |
    | round_number            | sessions.round_number | int                         |
    | current_node            | sessions.phase   | fallback if phase not set        |
    | len(personas)           | sessions.expert_count | derived count               |
    | len(contributions)      | sessions.contribution_count | derived count          |
    | len(sub_problems)       | sessions.focus_area_count | derived count            |
    | sub_problem_index       | sessions.problem_context | JSONB                     |
    | synthesis               | sessions.synthesis_text | via save_synthesis()       |
    | (via events)            | session_events   | event log for replay             |
    +-------------------------+------------------+----------------------------------+

    EPHEMERAL (runtime-only, lost on crash/restart):
    +-------------------------+------------------+----------------------------------+
    | Field                   | Type             | Why Ephemeral                    |
    +-------------------------+------------------+----------------------------------+
    | request_id              | str|None         | Per-HTTP-request correlation     |
    | current_node            | str              | Graph execution position         |
    | pending_clarification   | dict|None        | Transient UI state               |
    | facilitator_decision    | dict|None        | Intermediate decision            |
    | user_input              | str|None         | Transient user input             |
    | facilitator_guidance    | dict|None        | Inter-node guidance              |
    | context_insufficient_*  | bool/dict        | Flow control flags               |
    | user_context_choice     | str|None         | Transient user choice            |
    | best_effort_prompt_*    | bool             | Flow control flags               |
    | needs_interjection_*    | bool             | Flow control flags               |
    +-------------------------+------------------+----------------------------------+

    Recovery Semantics
    ==================

    On Redis AVAILABLE (normal path):
    - Full state restored via deserialize_state_from_checkpoint()
    - Resume from exact checkpoint with all data intact

    On Redis DOWN (fallback path):
    - PostgreSQL has: phase, round_number, counts, synthesis, events
    - Can reconstruct partial state via _reconstruct_state_from_postgres()
    - Contributions reconstructed from session_events (event_type='contribution')
    - Synthesis preserved; may lose intermediate deliberation state

    On CRASH during execution:
    - Ephemeral fields lost (request_id, pending_clarification, etc.)
    - Last checkpoint state is recoverable (Redis or Postgres)
    - Clarifications in progress may need re-submission

    See Also:
    - serialize_state_for_checkpoint(): State → Redis serialization
    - deserialize_state_from_checkpoint(): Redis → State deserialization
    - session_repository.save_metadata(): PostgreSQL fallback persistence
    - extract_session_metadata(): State → PostgreSQL field extraction
    """

    # Core identifiers
    session_id: str
    request_id: str | None  # HTTP request ID for log correlation across graph nodes

    # Problem context
    problem: Problem
    current_sub_problem: SubProblem | None

    # Participants
    personas: list[PersonaProfile]

    # Discussion state
    contributions: list[ContributionMessage]
    round_summaries: list[str]

    # Phase tracking (see PhaseState docstring for phase vs current_phase distinction)
    phase: DeliberationPhase  # Graph lifecycle: INTAKE→DISCUSSION→SYNTHESIS→COMPLETE
    round_number: int
    max_rounds: int

    # Metrics
    metrics: DeliberationMetrics

    # Decision tracking (stored as dict for serializability)
    facilitator_decision: dict[str, Any] | None

    # Control flags
    should_stop: bool
    stop_reason: str | None

    # Human-in-the-loop
    user_input: str | None
    user_id: str | None  # For context persistence
    subscription_tier: str | None  # For cost limit enforcement
    research_sharing_consented: bool  # For cross-user research sharing

    # Visualization
    current_node: str

    # Final outputs
    votes: list[dict[str, Any]]  # Vote objects
    synthesis: str | None

    # Multi-sub-problem tracking (Day 36.5)
    sub_problem_results: list[SubProblemResult]
    sub_problem_index: int

    # Context collection (Day 37)
    collect_context: bool  # Whether to collect business context
    business_context: dict[str, Any] | None  # Collected business context from user
    pending_clarification: dict[str, Any] | None  # Clarification question waiting for answer
    clarification_answers: dict[str, str] | None  # Answers to clarification questions (for resume)
    phase_costs: dict[str, float]  # Cost tracking by phase

    # Meeting quality guidance
    facilitator_guidance: dict[str, Any] | None  # Guidance for facilitator on next steps

    # Research tracking (prevent infinite research loops with semantic similarity)
    completed_research_queries: list[
        dict[str, Any]
    ]  # List of {"query": str, "embedding": list[float]}
    pending_research_queries: list[
        dict[str, Any]
    ]  # Proactive research queries from contribution analysis
    research_results: list[dict[str, Any]]  # Research results from completed queries

    # Proactive comparison detection (from ComparisonDetector)
    comparison_detected: bool  # Whether a "X vs Y" comparison question was detected
    comparison_options: list[str]  # The options being compared (e.g., ["React", "Svelte"])
    comparison_type: str  # Type of comparison (timing, build_vs_buy, technology, market, etc.)

    # Within-round prompt phase (distinct from `phase` — see PhaseState docstring)
    current_phase: str  # "exploration"/"challenge"/"convergence" — set by PhaseManager
    experts_per_round: list[list[str]]  # Track which experts contributed each round
    semantic_novelty_scores: dict[str, float]  # Per-contribution novelty scores
    exploration_score: float  # From quality metrics (0.0-1.0)
    focus_score: float  # From quality metrics (0.0-1.0)

    # PARALLEL SUB-PROBLEMS (Day 38.5 - Phases 1-2)
    execution_batches: list[list[int]]  # Sub-problem execution batches (list of index lists)
    parallel_mode: bool  # Whether parallel sub-problem execution is active
    dependency_error: str | None  # Error message if circular dependencies detected

    # CONTEXT SUFFICIENCY (Option D+E Hybrid)
    limited_context_mode: bool  # True if user provided partial/incomplete clarification answers
    context_insufficient_emitted: bool  # Track if context_insufficient event was already emitted
    context_insufficiency_info: dict[str, Any] | None  # Info about detected context insufficiency
    user_context_choice: str | None  # "continue" | "provide_more" | "end" | None
    best_effort_prompt_injected: bool  # Track if best effort prompt has been injected
    consecutive_research_without_improvement: int  # Counter for research loop prevention
    meta_discussion_count: int  # Count of meta-discussion contributions in current sub-problem
    total_contributions_checked: int  # Total contributions checked for meta-discussion ratio

    # STALLED DISAGREEMENT DETECTION (Productive Disagreement fix)
    high_conflict_low_novelty_rounds: (
        int  # Consecutive rounds with conflict > 0.7 AND novelty < 0.40
    )

    # DATA ANALYSIS INTEGRATION (EPIC 4)
    attached_datasets: list[str]  # Dataset IDs attached to this session
    data_analysis_results: list[dict[str, Any]]  # Results from data analysis during deliberation

    # USER-SELECTED CONTEXT (Meeting Context Selector)
    context_ids: dict[str, list[str]] | None  # {meetings: [...], actions: [...], datasets: [...]}

    # USER PREFERENCES (Clarification Toggle)
    skip_clarification: bool  # User preference to skip pre-meeting clarifying questions

    # EARLY TERMINATION (Meeting Termination)
    termination_requested: bool  # True if user requested early termination
    termination_type: str | None  # blocker_identified, user_cancelled, continue_best_effort
    termination_reason: str | None  # User-provided reason for termination

    # USER INTERJECTION ("Raise Hand" feature)
    user_interjection: str | None  # User's interjection message during deliberation
    interjection_responses: list[dict[str, Any]]  # Expert responses to the interjection
    needs_interjection_response: bool  # Flag indicating interjection needs processing

    # A/B TEST: Persona count experiment
    persona_count_variant: int | None  # 3 or 5 personas (A/B test for cost optimization)

    # RESUME SUPPORT: Prior expert summaries from completed sub-problems
    prior_expert_summaries: dict[str, str] | None  # {persona_code: summary} from previous SPs

    # RESUME SUPPORT: Flag indicating this is a resumed session from checkpoint
    is_resumed_session: bool

    # SUBPROBLEM FAILURE TRACKING (for EventCollector to publish meeting_failed event)
    subproblem_failures: SubproblemFailure | None  # Set by router when sub-problems fail


def create_initial_state(
    session_id: str,
    problem: Problem,
    personas: list[PersonaProfile] | None = None,
    max_rounds: int = 6,  # NEW DEFAULT: 6 rounds for parallel architecture
    user_id: str | None = None,
    collect_context: bool = True,
    skip_clarification: bool = False,
    context_ids: dict[str, list[str]] | None = None,
    subscription_tier: str | None = None,
    research_sharing_consented: bool = False,
    request_id: str | None = None,
    persona_count_variant: int | None = None,
) -> DeliberationGraphState:
    """Create initial graph state from a problem.

    Args:
        session_id: Unique session identifier
        problem: The problem to deliberate on
        personas: Selected personas (if already selected)
        max_rounds: Maximum rounds allowed
        user_id: Optional user ID for context persistence
        collect_context: Whether to collect business context (default: True)
        skip_clarification: Whether to skip pre-meeting clarifying questions (default: False)
        context_ids: Optional user-selected context {meetings: [...], actions: [...], datasets: [...]}
        subscription_tier: User's subscription tier for cost limit enforcement (default: "free")
        research_sharing_consented: Whether user consented to share research (default: False)
        request_id: HTTP request ID for log correlation across graph nodes
        persona_count_variant: A/B test variant (3 or 5 personas)

    Returns:
        Initial DeliberationGraphState ready for graph execution
    """
    return DeliberationGraphState(
        session_id=session_id,
        request_id=request_id,
        problem=problem,
        current_sub_problem=None,
        personas=personas or [],
        contributions=[],
        round_summaries=[],
        phase=DeliberationPhase.INTAKE,
        round_number=0,
        max_rounds=max_rounds,
        metrics=DeliberationMetrics(),
        facilitator_decision=None,
        should_stop=False,
        stop_reason=None,
        user_input=None,
        completed_research_queries=[],  # Track completed research
        pending_research_queries=[],  # Proactive research from contribution analysis
        research_results=[],  # Research results from completed queries
        # Proactive comparison detection (will be set by decompose_node if detected)
        comparison_detected=False,
        comparison_options=[],
        comparison_type="",
        user_id=user_id,
        subscription_tier=subscription_tier or "free",  # Default to free tier
        research_sharing_consented=research_sharing_consented,
        current_node="start",
        votes=[],
        synthesis=None,
        sub_problem_results=[],
        sub_problem_index=0,
        collect_context=collect_context,
        business_context=None,
        pending_clarification=None,
        clarification_answers=None,
        phase_costs={},
        # NEW FIELDS FOR PARALLEL ARCHITECTURE
        current_phase="exploration",  # Start with exploration phase
        experts_per_round=[],  # Will track experts per round
        semantic_novelty_scores={},  # Will track novelty per contribution
        exploration_score=0.0,  # Will be calculated during deliberation
        focus_score=1.0,  # Start at 1.0 (assume focused until proven otherwise)
        # PARALLEL SUB-PROBLEMS
        execution_batches=[],  # Will be populated by analyze_dependencies_node
        parallel_mode=False,  # Will be set based on dependency analysis
        dependency_error=None,  # Will be set if circular dependencies detected
        # CONTEXT SUFFICIENCY (Option D+E Hybrid)
        limited_context_mode=False,  # Will be set if user provides partial answers
        context_insufficient_emitted=False,  # Track if event was emitted
        context_insufficiency_info=None,  # Info about detected context insufficiency
        user_context_choice=None,  # User's choice: continue/provide_more/end
        best_effort_prompt_injected=False,  # Track if best effort prompt used
        consecutive_research_without_improvement=0,  # Research loop counter
        meta_discussion_count=0,  # Count of meta-discussion contributions
        total_contributions_checked=0,  # Total contributions checked for ratio
        # STALLED DISAGREEMENT DETECTION
        high_conflict_low_novelty_rounds=0,  # Consecutive rounds with conflict > 0.7 AND novelty < 0.40
        # DATA ANALYSIS INTEGRATION (EPIC 4)
        attached_datasets=[],  # Dataset IDs attached to this session
        data_analysis_results=[],  # Results from data analysis during deliberation
        # USER-SELECTED CONTEXT
        context_ids=context_ids,  # User-selected meetings/actions/datasets
        # USER PREFERENCES
        skip_clarification=skip_clarification,  # Skip pre-meeting clarifying questions
        # EARLY TERMINATION
        termination_requested=False,  # Will be set if user requests early termination
        termination_type=None,  # Type of termination
        termination_reason=None,  # User-provided reason
        # USER INTERJECTION ("Raise Hand")
        user_interjection=None,  # User's interjection message
        interjection_responses=[],  # Expert responses to interjection
        needs_interjection_response=False,  # Flag for interjection processing
        # A/B TEST: Persona count experiment
        persona_count_variant=persona_count_variant,
        # RESUME SUPPORT
        prior_expert_summaries=None,  # Will be populated on resume
        is_resumed_session=False,  # Will be set to True on resume
        # SUBPROBLEM FAILURE TRACKING
        subproblem_failures=None,  # Set by router when sub-problems fail
    )


def validate_state(state: DeliberationGraphState) -> None:
    """Validate graph state has all required fields.

    Args:
        state: The state to validate

    Raises:
        ValueError: If required fields are missing or invalid
    """
    required_fields = [
        "session_id",
        "problem",
        "personas",
        "contributions",
        "round_summaries",
        "phase",
        "round_number",
        "max_rounds",
        "metrics",
    ]

    for field in required_fields:
        if field not in state:
            raise ValueError(f"Missing required field: {field}")

    # Validate round numbers
    if state["round_number"] < 0:
        raise ValueError(f"Invalid round_number: {state['round_number']}")

    if state["round_number"] > state["max_rounds"]:
        raise ValueError(
            f"round_number ({state['round_number']}) exceeds max_rounds ({state['max_rounds']})"
        )

    # Validate max_rounds cap - NEW PARALLEL ARCHITECTURE: 6 rounds max
    # (with 3-5 experts per round = 18-30 contributions, equivalent to old 15-round serial model)
    if state["max_rounds"] > 6:
        raise ValueError(
            f"max_rounds ({state['max_rounds']}) exceeds hard cap of 6 for parallel architecture"
        )


# Re-export serialization functions (extracted to state_serialization.py)
from bo1.graph.state_serialization import (
    deserialize_state_from_checkpoint as deserialize_state_from_checkpoint,
    serialize_state_for_checkpoint as serialize_state_for_checkpoint,
)

# =============================================================================
# STATE ACCESSOR HELPERS (for gradual migration to nested structure)
# =============================================================================


def get_problem_state(state: DeliberationGraphState) -> ProblemState:
    """Extract problem-related fields as ProblemState.

    Use this helper to access problem fields in a grouped way,
    preparing for future migration to nested state structure.
    """
    return ProblemState(
        problem=state.get("problem"),  # type: ignore[typeddict-item]
        current_sub_problem=state.get("current_sub_problem"),
        sub_problem_results=state.get("sub_problem_results", []),
        sub_problem_index=state.get("sub_problem_index", 0),
    )


def get_phase_state(state: DeliberationGraphState) -> PhaseState:
    """Extract phase-related fields as PhaseState."""
    return PhaseState(
        phase=state.get("phase"),  # type: ignore[typeddict-item]
        current_phase=state.get("current_phase", "exploration"),
        round_number=state.get("round_number", 0),
        max_rounds=state.get("max_rounds", 6),
        current_node=state.get("current_node", "start"),
    )


def get_participant_state(state: DeliberationGraphState) -> ParticipantState:
    """Extract participant-related fields as ParticipantState."""
    return ParticipantState(
        personas=state.get("personas", []),
        experts_per_round=state.get("experts_per_round", []),
    )


def get_discussion_state(state: DeliberationGraphState) -> DiscussionState:
    """Extract discussion-related fields as DiscussionState."""
    return DiscussionState(
        contributions=state.get("contributions", []),
        round_summaries=state.get("round_summaries", []),
        votes=state.get("votes", []),
        synthesis=state.get("synthesis"),
    )


def get_research_state(state: DeliberationGraphState) -> ResearchState:
    """Extract research-related fields as ResearchState."""
    return ResearchState(
        completed_research_queries=state.get("completed_research_queries", []),
        pending_research_queries=state.get("pending_research_queries", []),
        research_results=state.get("research_results", []),
    )


def get_comparison_state(state: DeliberationGraphState) -> ComparisonState:
    """Extract comparison-related fields as ComparisonState."""
    return ComparisonState(
        comparison_detected=state.get("comparison_detected", False),
        comparison_options=state.get("comparison_options", []),
        comparison_type=state.get("comparison_type", ""),
    )


def get_context_state(state: DeliberationGraphState) -> ContextState:
    """Extract context-related fields as ContextState."""
    return ContextState(
        collect_context=state.get("collect_context", True),
        business_context=state.get("business_context"),
        pending_clarification=state.get("pending_clarification"),
        clarification_answers=state.get("clarification_answers"),
        context_ids=state.get("context_ids"),
        context_insufficient_emitted=state.get("context_insufficient_emitted", False),
        context_insufficiency_info=state.get("context_insufficiency_info"),
        user_context_choice=state.get("user_context_choice"),
        limited_context_mode=state.get("limited_context_mode", False),
        best_effort_prompt_injected=state.get("best_effort_prompt_injected", False),
    )


def get_control_state(state: DeliberationGraphState) -> ControlState:
    """Extract control-related fields as ControlState."""
    return ControlState(
        should_stop=state.get("should_stop", False),
        stop_reason=state.get("stop_reason"),
        termination_requested=state.get("termination_requested", False),
        termination_type=state.get("termination_type"),
        termination_reason=state.get("termination_reason"),
        skip_clarification=state.get("skip_clarification", False),
        user_interjection=state.get("user_interjection"),
        interjection_responses=state.get("interjection_responses", []),
        needs_interjection_response=state.get("needs_interjection_response", False),
    )


def get_metrics_state(state: DeliberationGraphState) -> MetricsState:
    """Extract metrics-related fields as MetricsState."""
    return MetricsState(
        metrics=state.get("metrics"),  # type: ignore[typeddict-item]
        phase_costs=state.get("phase_costs", {}),
        semantic_novelty_scores=state.get("semantic_novelty_scores", {}),
        exploration_score=state.get("exploration_score", 0.0),
        focus_score=state.get("focus_score", 1.0),
        consecutive_research_without_improvement=state.get(
            "consecutive_research_without_improvement", 0
        ),
        meta_discussion_count=state.get("meta_discussion_count", 0),
        total_contributions_checked=state.get("total_contributions_checked", 0),
        high_conflict_low_novelty_rounds=state.get("high_conflict_low_novelty_rounds", 0),
    )


def get_parallel_state(state: DeliberationGraphState) -> ParallelState:
    """Extract parallel execution fields as ParallelState."""
    return ParallelState(
        execution_batches=state.get("execution_batches", []),
        parallel_mode=state.get("parallel_mode", False),
        dependency_error=state.get("dependency_error"),
    )


def get_data_state(state: DeliberationGraphState) -> DataState:
    """Extract data-related fields as DataState."""
    return DataState(
        attached_datasets=state.get("attached_datasets", []),
        data_analysis_results=state.get("data_analysis_results", []),
    )


def get_core_state(state: DeliberationGraphState) -> CoreState:
    """Extract core identity fields as CoreState.

    Use this helper to access session identity and access control fields
    in a grouped way, preparing for future migration to nested state structure.
    """
    return CoreState(
        session_id=state.get("session_id"),  # type: ignore[typeddict-item]
        request_id=state.get("request_id"),
        user_id=state.get("user_id"),
        subscription_tier=state.get("subscription_tier"),
        research_sharing_consented=state.get("research_sharing_consented", False),
    )


# Re-export pruning functions (extracted to contribution_pruning.py)
from bo1.graph.contribution_pruning import (
    prune_contributions_after_round as prune_contributions_after_round,
    prune_contributions_for_phase as prune_contributions_for_phase,
)
