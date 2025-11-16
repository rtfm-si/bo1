"""Graph state models for LangGraph-based deliberation.

This module defines the TypedDict state for LangGraph and conversion functions
between v1 (DeliberationState) and v2 (DeliberationGraphState).
"""

from typing import Any, TypedDict

from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import (
    ContributionMessage,
    DeliberationMetrics,
    DeliberationPhase,
    DeliberationState,
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

    # Visualization
    current_node: str

    # Final outputs
    votes: list[dict[str, Any]]  # Vote objects
    synthesis: str | None


def create_initial_state(
    session_id: str,
    problem: Problem,
    personas: list[PersonaProfile] | None = None,
    max_rounds: int = 10,
) -> DeliberationGraphState:
    """Create initial graph state from a problem.

    Args:
        session_id: Unique session identifier
        problem: The problem to deliberate on
        personas: Selected personas (if already selected)
        max_rounds: Maximum rounds allowed

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
        current_node="start",
        votes=[],
        synthesis=None,
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

    # Validate max_rounds cap
    if state["max_rounds"] > 15:
        raise ValueError(f"max_rounds ({state['max_rounds']}) exceeds hard cap of 15")


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


# ============================================================================
# Conversion Functions (v1 <-> v2)
# ============================================================================


def deliberation_state_to_graph_state(v1_state: DeliberationState) -> DeliberationGraphState:
    """Convert v1 DeliberationState to v2 DeliberationGraphState.

    This allows existing v1 agent code to work with LangGraph by converting
    the state format. All v1 fields are preserved.

    Args:
        v1_state: The v1 deliberation state

    Returns:
        Equivalent v2 graph state
    """
    return DeliberationGraphState(
        session_id=v1_state.session_id,
        problem=v1_state.problem,
        current_sub_problem=v1_state.current_sub_problem,
        personas=v1_state.selected_personas,
        contributions=v1_state.contributions,
        round_summaries=v1_state.round_summaries,
        phase=v1_state.phase,
        round_number=v1_state.current_round,
        max_rounds=v1_state.max_rounds,
        metrics=v1_state.metrics,
        facilitator_decision=None,  # New field, not in v1
        should_stop=False,  # New field, calculated from convergence
        stop_reason=None,  # New field
        user_input=None,  # New field for human-in-loop
        current_node="unknown",  # New field for visualization
        votes=v1_state.votes,
        synthesis=v1_state.synthesis,
    )


def graph_state_to_deliberation_state(
    graph_state: DeliberationGraphState,
) -> DeliberationState:
    """Convert v2 DeliberationGraphState to v1 DeliberationState.

    This allows v1 agent code to receive graph state and work with it
    using the familiar v1 model.

    Args:
        graph_state: The v2 graph state

    Returns:
        Equivalent v1 deliberation state

    Raises:
        ValueError: If required fields are missing
    """
    # Validate required fields
    validate_state(graph_state)

    # Create v1 state with v2 data
    return DeliberationState(
        session_id=graph_state["session_id"],
        problem=graph_state["problem"],
        current_sub_problem=graph_state.get("current_sub_problem"),
        selected_personas=graph_state["personas"],
        contributions=graph_state["contributions"],
        round_summaries=graph_state["round_summaries"],
        phase=graph_state["phase"],
        current_round=graph_state["round_number"],
        max_rounds=graph_state["max_rounds"],
        metrics=graph_state["metrics"],
        votes=graph_state.get("votes", []),
        synthesis=graph_state.get("synthesis"),
    )
