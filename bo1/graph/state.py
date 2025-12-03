"""Graph state models for LangGraph-based deliberation.

This module defines the TypedDict state for LangGraph (DeliberationGraphState).
"""

from typing import Any, TypedDict

from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import (
    ContributionMessage,
    DeliberationMetrics,
    DeliberationPhase,
    SubProblemResult,
)


class DeliberationGraphState(TypedDict, total=False):
    """Graph state for LangGraph-based deliberation.

    This state is used by LangGraph nodes and represents the complete
    deliberation state at any point in the execution graph.

    Note: TypedDict with total=False allows optional fields while maintaining
    type safety for LangGraph's state management.
    """

    # Core identifiers
    session_id: str

    # Problem context
    problem: Problem
    current_sub_problem: SubProblem | None

    # Participants
    personas: list[PersonaProfile]

    # Discussion state
    contributions: list[ContributionMessage]
    round_summaries: list[str]

    # Phase tracking
    phase: DeliberationPhase
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

    # NEW FIELDS FOR PARALLEL ARCHITECTURE (Day 38)
    current_phase: str  # "exploration", "challenge", "convergence"
    experts_per_round: list[list[str]]  # Track which experts contributed each round
    semantic_novelty_scores: dict[str, float]  # Per-contribution novelty scores
    exploration_score: float  # From quality metrics (0.0-1.0)
    focus_score: float  # From quality metrics (0.0-1.0)

    # PARALLEL SUB-PROBLEMS (Day 38.5 - Phases 1-2)
    execution_batches: list[list[int]]  # Sub-problem execution batches (list of index lists)
    parallel_mode: bool  # Whether parallel sub-problem execution is active
    dependency_error: str | None  # Error message if circular dependencies detected


def create_initial_state(
    session_id: str,
    problem: Problem,
    personas: list[PersonaProfile] | None = None,
    max_rounds: int = 6,  # NEW DEFAULT: 6 rounds for parallel architecture
    user_id: str | None = None,
    collect_context: bool = True,
) -> DeliberationGraphState:
    """Create initial graph state from a problem.

    Args:
        session_id: Unique session identifier
        problem: The problem to deliberate on
        personas: Selected personas (if already selected)
        max_rounds: Maximum rounds allowed
        user_id: Optional user ID for context persistence
        collect_context: Whether to collect business context (default: True)

    Returns:
        Initial DeliberationGraphState ready for graph execution
    """
    return DeliberationGraphState(
        session_id=session_id,
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
        current_node="start",
        votes=[],
        synthesis=None,
        sub_problem_results=[],
        sub_problem_index=0,
        collect_context=collect_context,
        business_context=None,
        pending_clarification=None,
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


def state_to_dict(state: DeliberationGraphState) -> dict[str, Any]:
    """Convert graph state to dictionary for checkpointing.

    Args:
        state: The graph state to serialize

    Returns:
        Dictionary representation suitable for JSON serialization
    """
    # Convert to dict and handle Pydantic models
    result = dict(state)

    # Convert Pydantic models to dicts
    if "problem" in result and result["problem"] is not None:
        result["problem"] = result["problem"].model_dump()  # type: ignore[attr-defined]

    if "current_sub_problem" in result and result["current_sub_problem"] is not None:
        result["current_sub_problem"] = result["current_sub_problem"].model_dump()  # type: ignore[attr-defined]

    if "personas" in result:
        result["personas"] = [p.model_dump() for p in result["personas"]]  # type: ignore[attr-defined]

    if "contributions" in result:
        result["contributions"] = [c.model_dump() for c in result["contributions"]]  # type: ignore[attr-defined]

    if "metrics" in result and result["metrics"] is not None:
        result["metrics"] = result["metrics"].model_dump()  # type: ignore[attr-defined]

    # facilitator_decision is already a dict (converted in node using asdict())
    # No conversion needed

    return result
