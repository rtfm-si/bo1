"""Synthesis and sub-problem routing for LangGraph conditional edges.

Routes for synthesis, next sub-problem transitions, and parallel execution.
"""

import logging
from typing import Literal

from bo1.graph.router_utils import (
    get_problem_attr,
    get_subproblem_attr,
    log_routing_decision,
    validate_state_field,
)
from bo1.graph.state import DeliberationGraphState
from bo1.logging import ErrorCode, log_error
from bo1.models.state import SubProblemResult

logger = logging.getLogger(__name__)


@log_routing_decision("route_after_synthesis")
def route_after_synthesis(
    state: DeliberationGraphState,
) -> Literal["next_subproblem", "END"]:
    """Route after sub-problem synthesis.

    This router determines whether to:
    - Move to next_subproblem node (always for multi-SP) to save result
    - End directly (if only 1 sub-problem - atomic problem)

    RACE CONDITION FIX: Previously this router tried to validate all results
    before routing to meta_synthesis. However, the CURRENT sub-problem's result
    isn't added until next_subproblem_node runs. This caused the last SP to
    always "fail" (saw N-1 results when N expected).

    Solution: Always route to next_subproblem for multi-SP problems.
    The next_subproblem_node saves the result, then route_after_next_subproblem
    decides whether to continue to select_personas or meta_synthesis.

    Args:
        state: Current graph state

    Returns:
        - "next_subproblem" for multi-SP problems (saves result first)
        - "END" if atomic problem (only 1 sub-problem)
    """
    problem = validate_state_field(state, "problem", "route_after_synthesis")
    if not problem:
        return "END"

    sub_problems = get_problem_attr(problem, "sub_problems", [])
    total_sub_problems = len(sub_problems)

    # Atomic optimization: If only 1 sub-problem, skip meta-synthesis
    if total_sub_problems == 1:
        return "END"

    # For multi-SP: ALWAYS go through next_subproblem to save the result
    return "next_subproblem"


@log_routing_decision("route_after_next_subproblem")
def route_after_next_subproblem(
    state: DeliberationGraphState,
) -> Literal["select_personas", "meta_synthesis", "END"]:
    """Route after next_subproblem node saves the sub-problem result.

    This router runs AFTER next_subproblem_node has:
    1. Saved the current sub-problem result to sub_problem_results
    2. Either set current_sub_problem to next SP, or None if all complete

    Note: Sub-problem failure detection is handled by EventCollector which checks
    the final state for incomplete results and publishes the meeting_failed event.
    This keeps the router as a pure function without API layer dependencies.

    Args:
        state: Current graph state (result already saved)

    Returns:
        - "select_personas" if more sub-problems to process
        - "meta_synthesis" if all sub-problems complete
        - "END" if validation fails or sub-problems incomplete
    """
    problem = validate_state_field(state, "problem", "route_after_next_subproblem")
    if not problem:
        return "END"

    current_sub_problem = state.get("current_sub_problem")
    sub_problem_results = state.get("sub_problem_results", [])
    sub_problems = get_problem_attr(problem, "sub_problems", [])
    total_sub_problems = len(sub_problems)

    # If current_sub_problem is None, all sub-problems are complete
    if current_sub_problem is None:
        # Validate we have all results before proceeding to meta-synthesis
        if len(sub_problem_results) < total_sub_problems:
            failed_count = total_sub_problems - len(sub_problem_results)
            completed_ids = {
                r.sub_problem_id if isinstance(r, SubProblemResult) else r.get("sub_problem_id")
                for r in sub_problem_results
            }
            expected_ids = [get_subproblem_attr(sp, "id") for sp in sub_problems]
            failed_ids = [sp_id for sp_id in expected_ids if sp_id not in completed_ids]

            log_error(
                logger,
                ErrorCode.GRAPH_EXECUTION_ERROR,
                f"route_after_next_subproblem: Cannot proceed to meta-synthesis - "
                f"{failed_count} sub-problem(s) failed. "
                f"Failed IDs: {failed_ids}. "
                f"Expected {total_sub_problems} results, got {len(sub_problem_results)}.",
            )

            # Note: meeting_failed event is published by EventCollector._handle_completion
            # when it detects incomplete sub_problem_results in the final state.
            # This avoids importing API layer dependencies in the graph router.

            return "END"

        # All results present → meta-synthesis
        return "meta_synthesis"

    # More sub-problems to process → continue loop
    return "select_personas"


@log_routing_decision("route_subproblem_execution")
def route_subproblem_execution(
    state: DeliberationGraphState,
) -> Literal["parallel_subproblems", "select_personas"]:
    """Route after dependency analysis to parallel or sequential execution.

    This router checks the parallel_mode flag set by analyze_dependencies_node:
    - If parallel_mode=True: Route to parallel_subproblems for concurrent execution
    - If parallel_mode=False: Route to select_personas for sequential execution

    Note: context_collection now happens BEFORE decomposition (Issue #3 fix),
    so sequential mode goes directly to select_personas.

    Args:
        state: Current graph state (must have parallel_mode set)

    Returns:
        - "parallel_subproblems" if parallel execution enabled
        - "select_personas" if sequential execution
    """
    parallel_mode = state.get("parallel_mode", False)

    if parallel_mode:
        return "parallel_subproblems"
    else:
        return "select_personas"


@log_routing_decision("route_on_resume")
def route_on_resume(
    state: DeliberationGraphState,
) -> Literal["select_personas", "decompose", "END"]:
    """Route based on resume state from checkpoint.

    This router handles session resume after crash/disconnect:
    - If sub_problem_results exist AND current_sub_problem is None:
      Restore current_sub_problem from problem.sub_problems and route to select_personas
    - If no sub_problem_results: Normal start via decompose
    - If is_resumed_session is True: Skip decomposition, go to select_personas

    Args:
        state: Current graph state (potentially restored from checkpoint)

    Returns:
        - "select_personas" if resuming mid-session
        - "decompose" for fresh start
        - "END" if validation fails
    """
    is_resumed = state.get("is_resumed_session", False)
    sub_problem_results = state.get("sub_problem_results", [])
    current_sub_problem = state.get("current_sub_problem")

    # Fresh start - no resume needed
    if not is_resumed and not sub_problem_results:
        return "decompose"

    # Resume case: has completed SPs but current_sub_problem not set
    if sub_problem_results and current_sub_problem is None:
        problem = validate_state_field(state, "problem", "route_on_resume")
        if not problem:
            return "END"

        sub_problems = get_problem_attr(problem, "sub_problems", [])
        total_sub_problems = len(sub_problems)

        # Determine next sub-problem index (one after last completed)
        next_index = len(sub_problem_results)

        if next_index >= total_sub_problems:
            # All complete - should go to meta-synthesis
            return "END"

        return "select_personas"

    # Resume with current_sub_problem already set
    if is_resumed and current_sub_problem:
        return "select_personas"

    # Default: fresh start
    return "decompose"
