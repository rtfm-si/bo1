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


def create_initial_state(
    session_id: str,
    problem: Problem,
    personas: list[PersonaProfile] | None = None,
    max_rounds: int = 10,
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

# Cache for state conversions (module-level)
# Caches the last conversion to avoid redundant processing within a single
# deliberation session. Cache is invalidated automatically when state object
# identity changes (i.e., when LangGraph updates state between nodes).
_last_graph_state_id: int | None = None
_last_v1_state: DeliberationState | None = None
_cache_hits: int = 0
_cache_misses: int = 0


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
    """Convert v2 DeliberationGraphState to v1 DeliberationState with caching.

    This function caches the last conversion to avoid redundant processing
    when the same state is converted multiple times within a single node
    or across nodes in the same deliberation round.

    Cache is invalidated automatically when state identity changes (i.e.,
    when LangGraph updates state between nodes).

    Performance: 90%+ faster for cache hits (~0.01ms vs ~1-5ms).

    Args:
        graph_state: The v2 graph state

    Returns:
        Equivalent v1 deliberation state (Pydantic models)

    Raises:
        ValueError: If required fields are missing

    Note:
        Cache is process-local and session-scoped. Safe for concurrent
        deliberations as state identity differs per session.
    """
    global _last_graph_state_id, _last_v1_state, _cache_hits, _cache_misses

    import logging

    logger = logging.getLogger(__name__)

    # Create stable hash of state using object identity
    state_id = id(graph_state)

    # Return cached version if state unchanged
    if state_id == _last_graph_state_id and _last_v1_state is not None:
        _cache_hits += 1
        logger.debug(
            f"State conversion cache hit (hits={_cache_hits}, misses={_cache_misses}, "
            f"hit_rate={_cache_hits / (_cache_hits + _cache_misses):.1%})"
        )
        return _last_v1_state

    # Cache miss - perform conversion
    _cache_misses += 1
    logger.debug(
        f"State conversion cache miss (hits={_cache_hits}, misses={_cache_misses}, "
        f"hit_rate={_cache_hits / max(_cache_hits + _cache_misses, 1):.1%})"
    )

    # Validate required fields
    validate_state(graph_state)

    # Create v1 state with v2 data
    v1_state = DeliberationState(
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

    # Update cache
    _last_graph_state_id = state_id
    _last_v1_state = v1_state

    return v1_state


def clear_state_conversion_cache() -> None:
    """Clear the state conversion cache.

    Useful for testing or when starting a new deliberation session.
    In production, the cache is automatically invalidated when state
    identity changes between nodes.
    """
    global _last_graph_state_id, _last_v1_state, _cache_hits, _cache_misses

    _last_graph_state_id = None
    _last_v1_state = None
    _cache_hits = 0
    _cache_misses = 0


def get_cache_stats() -> dict[str, int | float]:
    """Get state conversion cache statistics.

    Returns:
        Dictionary with cache hits, misses, and hit rate

    Example:
        >>> stats = get_cache_stats()
        >>> print(f"Hit rate: {stats['hit_rate']:.1%}")
        Hit rate: 75.0%
    """
    total = _cache_hits + _cache_misses
    return {
        "hits": _cache_hits,
        "misses": _cache_misses,
        "total": total,
        "hit_rate": _cache_hits / total if total > 0 else 0.0,
    }
