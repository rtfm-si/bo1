"""State definition for sub-problem deliberation subgraph.

This module defines the focused state type for sub-problem deliberation,
along with transformation helpers for data flow between parent graph and subgraph.
"""

from typing import Any

from typing_extensions import TypedDict

from bo1.graph.safety.loop_prevention import get_adaptive_max_rounds
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import ContributionMessage, DeliberationMetrics, SubProblemResult
from bo1.utils.checkpoint_helpers import get_sub_problem_goal_safe, get_sub_problem_id_safe


class SubProblemGraphState(TypedDict, total=False):
    """State for sub-problem deliberation subgraph.

    This is a focused subset of DeliberationGraphState, containing only
    the fields needed for deliberating a single sub-problem. This enables:
    - Cleaner separation of concerns
    - Smaller checkpoint sizes
    - Easier testing in isolation
    """

    # Identifiers
    session_id: str
    sub_problem_index: int

    # Problem context
    sub_problem: SubProblem
    parent_problem: Problem  # For context only

    # Participants
    personas: list[PersonaProfile]
    all_available_personas: list[PersonaProfile]  # For selection

    # Discussion
    contributions: list[ContributionMessage]
    round_summaries: list[str]
    round_number: int
    max_rounds: int

    # Control
    should_stop: bool
    stop_reason: str | None
    facilitator_decision: dict[str, Any] | None

    # Metrics
    metrics: DeliberationMetrics

    # Phase tracking
    current_phase: str  # "exploration", "challenge", "convergence"
    experts_per_round: list[list[str]]  # Track which experts per round

    # Expert memory (from previous sub-problems)
    expert_memory: dict[str, str]

    # P2 FIX: Judge feedback for next round - enables exploration score improvement
    next_round_focus_prompts: list[str]
    missing_critical_aspects: list[str]

    # Outputs
    votes: list[dict[str, Any]]
    synthesis: str | None
    expert_summaries: dict[str, str]

    # User context
    user_id: str | None


def create_subproblem_initial_state(
    session_id: str,
    sub_problem: SubProblem,
    sub_problem_index: int,
    parent_problem: Problem,
    all_available_personas: list[PersonaProfile],
    expert_memory: dict[str, str],
    user_id: str | None = None,
) -> SubProblemGraphState:
    """Transform parent state into subgraph initial state.

    This creates the initial state for a sub-problem deliberation subgraph
    from the parent graph's context.

    Args:
        session_id: Session ID from parent graph
        sub_problem: The sub-problem to deliberate
        sub_problem_index: Index of this sub-problem (0-based)
        parent_problem: The parent problem for context
        all_available_personas: All personas available for selection
        expert_memory: Memory from previous sub-problems (persona_code -> summary)
        user_id: Optional user ID for context

    Returns:
        Initial SubProblemGraphState ready for subgraph execution
    """
    max_rounds = get_adaptive_max_rounds(sub_problem.complexity_score)

    return SubProblemGraphState(
        session_id=session_id,
        sub_problem_index=sub_problem_index,
        sub_problem=sub_problem,
        parent_problem=parent_problem,
        personas=[],  # Will be selected by first node
        all_available_personas=all_available_personas,
        contributions=[],
        round_summaries=[],
        round_number=0,
        max_rounds=max_rounds,
        should_stop=False,
        stop_reason=None,
        facilitator_decision=None,
        metrics=DeliberationMetrics(),
        current_phase="exploration",
        experts_per_round=[],
        expert_memory=expert_memory,
        # P2 FIX: Initialize judge feedback fields
        next_round_focus_prompts=[],
        missing_critical_aspects=[],
        votes=[],
        synthesis=None,
        expert_summaries={},
        user_id=user_id,
    )


def result_from_subgraph_state(state: SubProblemGraphState) -> SubProblemResult:
    """Extract SubProblemResult from final subgraph state.

    This transforms the completed subgraph state back into a SubProblemResult
    that can be stored in the parent graph state.

    Args:
        state: Final state from subgraph execution

    Returns:
        SubProblemResult with synthesis, votes, costs, and expert summaries
    """
    # Use safe accessors to handle corrupted checkpoint data
    sub_problem = state.get("sub_problem")
    return SubProblemResult(
        sub_problem_id=get_sub_problem_id_safe(sub_problem),
        sub_problem_goal=get_sub_problem_goal_safe(sub_problem),
        synthesis=state.get("synthesis") or "",
        votes=state.get("votes", []),
        contribution_count=len(state.get("contributions", [])),
        cost=state.get("metrics", DeliberationMetrics()).total_cost,
        duration_seconds=0.0,  # Will be set by caller based on timing
        expert_panel=[p.code for p in state.get("personas", [])],
        expert_summaries=state.get("expert_summaries", {}),
    )


def build_expert_memory(previous_results: list[SubProblemResult]) -> dict[str, str]:
    """Build expert memory from previous sub-problem results.

    This aggregates expert summaries from all previous sub-problems
    to provide context continuity for sequential dependencies.

    Args:
        previous_results: Results from previously completed sub-problems

    Returns:
        Dict mapping persona_code to aggregated memory string
    """
    if not previous_results:
        return {}

    # Build memory parts first
    memory_parts: dict[str, list[str]] = {}
    for result in previous_results:
        for expert_code, summary in result.expert_summaries.items():
            if expert_code not in memory_parts:
                memory_parts[expert_code] = []
            memory_parts[expert_code].append(
                f"Sub-problem: {result.sub_problem_goal}\nYour position: {summary}"
            )

    # Join memory parts for each expert
    return {code: "\n\n".join(parts) for code, parts in memory_parts.items() if parts}
