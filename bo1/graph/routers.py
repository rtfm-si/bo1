"""Router functions for LangGraph conditional edges.

Routers determine the next node to execute based on the current state.
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


# Re-export for backwards compatibility (private names)
_validate_state_field = validate_state_field
_get_problem_attr = get_problem_attr
_get_subproblem_attr = get_subproblem_attr


@log_routing_decision("route_phase")
def route_phase(
    state: DeliberationGraphState,
) -> Literal["select_personas", "initial_round", "facilitator_decide", "END"]:
    """Route based on current deliberation phase.

    Updated in Week 5 to route to facilitator after initial round.

    Args:
        state: Current graph state

    Returns:
        Next node name to execute
    """
    phase = state.get("phase")

    if phase == "decomposition":
        return "select_personas"
    elif phase == "selection":
        return "initial_round"
    elif phase == "discussion":
        return "facilitator_decide"
    else:
        logger.warning(f"route_phase: Unknown phase {phase}")
        return "END"


@log_routing_decision("route_facilitator_decision")
def route_facilitator_decision(
    state: DeliberationGraphState,
) -> Literal[
    "vote",
    "persona_contribute",
    "research",
    "moderator_intervene",
    "clarification",
    "data_analysis",
    "END",
]:
    """Route based on facilitator's decision.

    Routes to different nodes based on the facilitator's action:
    - "vote" → Move to voting phase
    - "continue" → Persona contributes next round
    - "research" → Execute external research
    - "moderator" → Moderator intervenes (premature consensus only)
    - "clarify" → Request clarification from user
    - "analyze_data" → Execute dataset analysis

    Args:
        state: Current graph state with facilitator_decision

    Returns:
        Next node name to execute
    """
    decision = validate_state_field(state, "facilitator_decision", "route_facilitator_decision")
    if not decision:
        return "END"

    action = decision["action"]

    if action == "vote":
        return "vote"
    elif action == "continue":
        return "persona_contribute"
    elif action == "research":
        return "research"
    elif action == "moderator":
        return "moderator_intervene"
    elif action == "clarify":
        return "clarification"
    elif action == "analyze_data":
        return "data_analysis"
    else:
        log_error(
            logger,
            ErrorCode.GRAPH_STATE_ERROR,
            f"route_facilitator_decision: Unknown action {action}, falling back to persona_contribute",
        )
        return "persona_contribute"


@log_routing_decision("route_convergence_check")
def route_convergence_check(
    state: DeliberationGraphState,
) -> Literal["facilitator_decide", "vote"]:
    """Route after convergence check based on should_stop flag.

    This router is called after persona_contribute or moderator_intervene nodes.
    It checks if convergence has been reached or round limits exceeded.

    Args:
        state: Current graph state with should_stop flag

    Returns:
        - "facilitator_decide" if deliberation should continue
        - "vote" if stopping condition met (max rounds, convergence, etc.) - Day 31
    """
    should_stop = state.get("should_stop", False)

    if should_stop:
        return "vote"
    else:
        return "facilitator_decide"


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

    Args:
        state: Current graph state (result already saved)

    Returns:
        - "select_personas" if more sub-problems to process
        - "meta_synthesis" if all sub-problems complete
        - "END" if validation fails
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

            # Emit error event to UI
            from backend.api.dependencies import get_event_publisher

            try:
                event_publisher = get_event_publisher()
                session_id = state.get("session_id")

                if event_publisher and session_id:
                    failed_goals = [
                        get_subproblem_attr(sp, "goal")
                        for sp in sub_problems
                        if get_subproblem_attr(sp, "id") in failed_ids
                    ]
                    event_publisher.publish_event(
                        session_id,
                        "meeting_failed",
                        {
                            "reason": f"{failed_count} sub-problem(s) failed to complete",
                            "failed_count": failed_count,
                            "failed_ids": failed_ids,
                            "failed_goals": failed_goals,
                            "completed_count": len(sub_problem_results),
                            "total_count": total_sub_problems,
                        },
                    )
            except Exception as e:
                log_error(
                    logger,
                    ErrorCode.SERVICE_EXECUTION_ERROR,
                    f"Failed to publish meeting_failed event: {e}",
                )

            return "END"

        # All results present → meta-synthesis
        return "meta_synthesis"

    # More sub-problems to process → continue loop
    return "select_personas"


@log_routing_decision("route_clarification")
def route_clarification(
    state: DeliberationGraphState,
) -> Literal["persona_contribute", "END"]:
    """Route after clarification based on should_stop flag.

    This router determines whether to:
    - Continue deliberation (if clarification answered or skipped)
    - Pause session (if user requested pause)

    Args:
        state: Current graph state

    Returns:
        - "persona_contribute" if continuing deliberation
        - "END" if session paused
    """
    should_stop = state.get("should_stop", False)

    if should_stop:
        return "END"
    else:
        return "persona_contribute"


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


@log_routing_decision("route_after_identify_gaps")
def route_after_identify_gaps(state: DeliberationGraphState) -> Literal["END", "continue"]:
    """Route based on whether critical information gaps require user input.

    After clarification answers are submitted, the checkpoint is updated with:
    - clarification_answers: dict of question->answer pairs
    - should_stop: False (reset to continue)
    - stop_reason: None (cleared)

    The router then sees should_stop=False and routes to "continue".

    Args:
        state: Current graph state

    Returns:
        - "END" if clarification needed (pause for Q&A)
        - "continue" if ready to proceed with deliberation
    """
    should_stop = state.get("should_stop")
    stop_reason = state.get("stop_reason")

    if should_stop and stop_reason == "clarification_needed":
        return "END"

    return "continue"
