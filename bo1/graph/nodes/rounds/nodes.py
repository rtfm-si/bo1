"""Main deliberation round node functions.

Contains the primary graph nodes (initial_round_node, parallel_round_node)
and their direct helpers.
"""

import logging
import time
from typing import Any

from bo1.graph.deliberation import PhaseManager
from bo1.graph.deliberation import (
    select_experts_for_round as _select_experts_for_round,
)
from bo1.graph.nodes.rounds.contribution import _generate_parallel_contributions
from bo1.graph.nodes.rounds.quality import (
    _apply_semantic_deduplication,
    _check_contribution_quality,
)
from bo1.graph.nodes.rounds.summarization import _detect_research_needs, _summarize_round
from bo1.graph.nodes.utils import emit_node_duration
from bo1.graph.quality.stopping_rules import update_stalled_disagreement_counter
from bo1.graph.state import (
    DeliberationGraphState,
    get_control_state,
    get_core_state,
    get_discussion_state,
    get_metrics_state,
    get_participant_state,
    get_phase_state,
    get_problem_state,
    get_research_state,
    prune_contributions_after_round,
)
from bo1.graph.utils import ensure_metrics
from bo1.models.state import DeliberationPhase
from bo1.utils.checkpoint_helpers import get_problem_description
from bo1.utils.deliberation_logger import get_deliberation_logger

logger = logging.getLogger(__name__)


def _build_cross_subproblem_memories(
    personas: list[Any],
    sub_problem_results: list[Any],
) -> dict[str, str]:
    """Build cross-sub-problem memory for each expert.

    For experts who contributed to previous sub-problems, collects their
    positions to provide continuity across sub-problems.

    Args:
        personas: List of PersonaProfile objects
        sub_problem_results: Results from previous sub-problems

    Returns:
        Dict mapping expert code to memory string
    """
    expert_memories: dict[str, str] = {}

    if not sub_problem_results:
        return expert_memories

    for persona in personas:
        memory_parts = []
        for result in sub_problem_results:
            if hasattr(result, "expert_summaries") and persona.code in result.expert_summaries:
                prev_summary = result.expert_summaries[persona.code]
                prev_goal = result.sub_problem_goal
                memory_parts.append(f"Sub-problem: {prev_goal}\nYour position: {prev_summary}")

        if memory_parts:
            expert_memories[persona.code] = "\n\n".join(memory_parts)
            logger.debug(
                f"Expert {persona.display_name} has memory from {len(memory_parts)} sub-problems"
            )

    return expert_memories


async def initial_round_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Run initial round with parallel persona contributions.

    Orchestrates the first round of expert contributions through these steps:
    1. Check for double-contribution (skip if round 1 already has contributions)
    2. Build cross-sub-problem memories for experts
    3. Generate contributions from all personas in parallel
    4. Apply semantic deduplication to filter repetitive contributions
    5. Check contribution quality and set facilitator guidance
    6. Summarize the round for hierarchical context
    7. Build and return state update

    This mirrors the parallel_round_node pattern for consistency and enables
    60-70% latency reduction through unified parallel execution.

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates
    """
    _start_time = time.perf_counter()

    # Use nested state accessors for grouped field access
    core_state = get_core_state(state)
    discussion_state = get_discussion_state(state)
    participant_state = get_participant_state(state)
    phase_state = get_phase_state(state)
    problem_state = get_problem_state(state)

    session_id = core_state.get("session_id")
    user_id = core_state.get("user_id")
    request_id = core_state.get("request_id")
    round_number = 1  # Initial round is always round 1
    dlog = get_deliberation_logger(session_id, user_id, "initial_round_node")
    dlog.info("Starting initial round", request_id=request_id)

    # GUARD: Check if round 1 already has contributions (prevents double-contribution bug)
    existing_contributions = discussion_state.get("contributions", [])
    round_contributions = []
    for c in existing_contributions:
        c_round = (
            c.round_number
            if hasattr(c, "round_number")
            else c.get("round_number")
            if hasattr(c, "get")
            else None
        )
        if c_round == round_number:
            round_contributions.append(c)
    if round_contributions:
        dlog.warning(
            "Round 1 already has contributions - skipping to avoid double contribution",
            existing_contributions=len(round_contributions),
        )
        emit_node_duration("initial_round_node", (time.perf_counter() - _start_time) * 1000)
        return {
            "round_number": 2,
            "current_node": "initial_round_skipped",
            "phase": DeliberationPhase.DISCUSSION,
        }

    # Get personas and sub-problem results from accessors
    personas = participant_state.get("personas", [])
    sub_problem_results = problem_state.get("sub_problem_results", [])
    max_rounds = phase_state.get("max_rounds", 6)
    problem = problem_state.get("problem")

    # Build cross-sub-problem memories for experts
    expert_memories = _build_cross_subproblem_memories(personas, sub_problem_results)
    if expert_memories:
        dlog.info(
            "Built cross-sub-problem memories",
            experts_with_memory=len(expert_memories),
        )

    # Generate contributions in parallel using exploration phase
    phase = _determine_phase(round_number, max_rounds)
    contributions = await _generate_parallel_contributions(
        experts=personas,
        state=state,
        phase=phase,
        round_number=round_number,
        contribution_type="initial",
        expert_memories=expert_memories if expert_memories else None,
    )
    dlog.info("Contributions generated", contributions=len(contributions))

    # Apply semantic deduplication
    filtered_contributions = await _apply_semantic_deduplication(contributions)

    # Get problem context for quality check
    problem_description = get_problem_description(problem)
    problem_context = problem_description or "No problem context available"

    # Initialize metrics and facilitator guidance
    metrics = ensure_metrics(state)
    facilitator_guidance: dict[str, Any] = {}

    # Check contribution quality
    quality_results, facilitator_guidance = await _check_contribution_quality(
        contributions=filtered_contributions,
        problem_context=problem_context,
        round_number=round_number,
        metrics=metrics,
        facilitator_guidance=facilitator_guidance,
    )

    # Summarize the round
    round_summaries: list[str] = []
    summary = await _summarize_round(
        contributions=filtered_contributions,
        round_number=round_number,
        current_phase=phase,
        problem_statement=problem_description,
        metrics=metrics,
    )
    if summary:
        round_summaries.append(summary)

    # Detect research needs from initial contributions
    pending_research_queries = await _detect_research_needs(
        contributions=filtered_contributions,
        problem_context=problem_context,
        metrics=metrics,
    )

    # Log quality summary
    if quality_results:
        shallow_count = sum(1 for r in quality_results if r.is_shallow)
        avg_quality = sum(r.quality_score for r in quality_results) / len(quality_results)
        dlog.info(
            "Initial round complete",
            contributions=len(filtered_contributions),
            quality=f"{avg_quality:.2f}",
            shallow=shallow_count,
        )
    else:
        dlog.info(
            "Initial round complete",
            contributions=len(filtered_contributions),
        )

    # Build state update with all enrichments
    emit_node_duration("initial_round_node", (time.perf_counter() - _start_time) * 1000)
    return {
        "contributions": filtered_contributions,
        "phase": DeliberationPhase.DISCUSSION,
        "round_number": 2,  # Next round to execute
        "metrics": metrics,
        "current_node": "initial_round",
        "personas": personas,
        "sub_problem_index": problem_state.get("sub_problem_index", 0),
        "round_summaries": round_summaries,
        "facilitator_guidance": facilitator_guidance,
        "pending_research_queries": pending_research_queries,
        "experts_per_round": [[c.persona_code for c in filtered_contributions]],
    }


def _determine_phase(round_number: int, max_rounds: int) -> str:
    """Determine deliberation phase based on round number.

    Delegates to bo1.graph.deliberation.phases.PhaseManager.determine_phase.

    Phase allocation for 6-round max:
    - Exploration: Rounds 1-2 (33% of deliberation)
    - Challenge: Rounds 3-4 (33% of deliberation)
    - Convergence: Rounds 5+ (33% of deliberation)

    Args:
        round_number: Current round (1-indexed)
        max_rounds: Maximum rounds configured

    Returns:
        Phase name: "exploration", "challenge", or "convergence"
    """
    return PhaseManager.determine_phase(round_number, max_rounds)


def _build_round_state_update(
    state: DeliberationGraphState,
    filtered_contributions: list[Any],
    round_number: int,
    current_phase: str,
    round_summaries: list[str],
    metrics: Any,
    pending_research_queries: list[Any],
    facilitator_guidance: dict[str, Any],
    quality_results: list[Any],
) -> dict[str, Any]:
    """Build the state update dictionary for a round.

    Args:
        state: Current graph state
        filtered_contributions: Contributions after deduplication
        round_number: Current round number
        current_phase: Current deliberation phase
        round_summaries: List of round summaries
        metrics: Metrics object
        pending_research_queries: Detected research queries
        facilitator_guidance: Updated facilitator guidance
        quality_results: Quality check results

    Returns:
        Dictionary with state updates
    """
    from bo1.llm.response_parser import ResponseParser

    # Use nested state accessors for grouped field access
    discussion_state = get_discussion_state(state)
    participant_state = get_participant_state(state)
    research_state = get_research_state(state)

    # Get metrics state for tracking fields
    metrics_state = get_metrics_state(state)

    # Update contributions
    all_contributions = list(discussion_state.get("contributions", []))
    all_contributions.extend(filtered_contributions)

    # Track which experts contributed this round
    experts_per_round = list(participant_state.get("experts_per_round", []))
    round_experts = [c.persona_code for c in filtered_contributions]
    experts_per_round.append(round_experts)

    next_round = round_number + 1

    # Prune old contributions after round summary is generated (memory optimization)
    core_state = get_core_state(state)
    all_contributions, pruned_count = prune_contributions_after_round(
        contributions=all_contributions,
        round_summaries=round_summaries,
        current_round=round_number,
        session_id=core_state.get("session_id"),
    )
    if pruned_count > 0:
        from backend.api.middleware.metrics import record_contributions_pruned

        record_contributions_pruned(
            session_id=core_state.get("session_id") or "",
            round_number=round_number,
            pruned_count=pruned_count,
        )

    # Count meta-discussion contributions for context sufficiency detection
    meta_discussion_count = metrics_state.get("meta_discussion_count", 0)
    total_contributions_checked = metrics_state.get("total_contributions_checked", 0)

    for contrib in filtered_contributions:
        total_contributions_checked += 1
        if ResponseParser.is_context_insufficient_discussion(contrib.content):
            meta_discussion_count += 1
            logger.warning(
                f"Meta-discussion detected from {contrib.persona_code} in round {round_number}: "
                f"'{contrib.content[:80]}...'"
            )

    # Calculate and log meta-discussion ratio
    # Also track research loop counter for loop prevention
    consecutive_research_without_improvement = metrics_state.get(
        "consecutive_research_without_improvement", 0
    )
    research_results = research_state.get("research_results", [])

    if total_contributions_checked > 0:
        meta_ratio = meta_discussion_count / total_contributions_checked
        if meta_ratio > 0.3:  # Log if >30% are meta-discussion
            logger.warning(
                f"High meta-discussion ratio: {meta_discussion_count}/{total_contributions_checked} "
                f"({meta_ratio:.0%}) contributions indicate insufficient context"
            )

            # RESEARCH LOOP PREVENTION (Option D+E Hybrid - Phase 7)
            # If we have research results but meta-discussion is still high,
            # the research didn't help - increment the counter
            if research_results and len(research_results) > 0:
                consecutive_research_without_improvement += 1
                logger.warning(
                    f"🔄 Research loop counter incremented to {consecutive_research_without_improvement} "
                    f"(research results: {len(research_results)}, but meta-discussion still high: {meta_ratio:.0%})"
                )
        else:
            # Meta-discussion is acceptable - reset the counter if research helped
            if (
                research_results
                and len(research_results) > 0
                and consecutive_research_without_improvement > 0
            ):
                logger.info(
                    f"✅ Research helped! Meta-discussion ratio improved to {meta_ratio:.0%}. "
                    f"Resetting research loop counter."
                )
                consecutive_research_without_improvement = 0

    # Log completion
    if quality_results:
        shallow_count = sum(1 for r in quality_results if r.is_shallow)
        avg_quality = sum(r.quality_score for r in quality_results) / len(quality_results)
        logger.info(
            f"parallel_round_node: Complete - Round {round_number} -> {next_round}, "
            f"{len(filtered_contributions)} contributions added "
            f"(quality: {avg_quality:.2f}, {shallow_count} shallow)"
        )
    else:
        logger.info(
            f"parallel_round_node: Complete - Round {round_number} -> {next_round}, "
            f"{len(filtered_contributions)} contributions added"
        )

    # Get problem state for sub_problem_index
    problem_state = get_problem_state(state)

    return {
        "contributions": all_contributions,
        "round_number": next_round,
        "current_phase": current_phase,
        "experts_per_round": experts_per_round,
        "round_summaries": round_summaries,
        "metrics": metrics,
        "current_node": "parallel_round",
        "personas": participant_state.get("personas", []),
        "sub_problem_index": problem_state.get("sub_problem_index", 0),
        "pending_research_queries": pending_research_queries,
        "facilitator_guidance": facilitator_guidance,
        # NEW: Context sufficiency tracking
        "meta_discussion_count": meta_discussion_count,
        "total_contributions_checked": total_contributions_checked,
        # Research loop prevention counter
        "consecutive_research_without_improvement": consecutive_research_without_improvement,
        # Stalled disagreement counter (updated based on current metrics)
        "high_conflict_low_novelty_rounds": update_stalled_disagreement_counter(state),
    }


async def parallel_round_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Execute a round with multiple experts contributing in parallel.

    Orchestrates a parallel round of expert contributions through these steps:
    1. Determine phase (exploration/challenge/convergence) based on round number
    2. Select experts based on phase, contribution balance, and novelty
    3. Generate contributions from all selected experts in parallel
    4. Apply semantic deduplication to filter repetitive contributions
    5. Check contribution quality and update guidance
    6. Summarize the round for hierarchical context
    7. Detect research needs for proactive research
    8. Build and return state update

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates
    """
    _start_time = time.perf_counter()

    # Use nested state accessors for grouped field access
    core_state = get_core_state(state)
    phase_state = get_phase_state(state)
    discussion_state = get_discussion_state(state)

    session_id = core_state.get("session_id")
    user_id = core_state.get("user_id")
    request_id = core_state.get("request_id")
    dlog = get_deliberation_logger(session_id, user_id, "parallel_round_node")
    dlog.info("Starting parallel round with multiple experts", request_id=request_id)

    # Get current round and phase from accessor
    round_number = phase_state.get("round_number", 1)

    # GUARD: Check if this round already has contributions (prevents double-contribution bug)
    # This can happen due to graph retries or checkpoint edge cases
    existing_contributions = discussion_state.get("contributions", [])
    round_contributions = []
    for c in existing_contributions:
        # Handle both ContributionMessage objects and dicts (from checkpoint deserialization)
        c_round = (
            c.round_number
            if hasattr(c, "round_number")
            else c.get("round_number")
            if hasattr(c, "get")
            else None
        )
        if c_round == round_number:
            round_contributions.append(c)
    if round_contributions:
        dlog.warning(
            "Round already has contributions - skipping to avoid double contribution",
            round_number=round_number,
            existing_contributions=len(round_contributions),
            next_round=round_number + 1,
        )
        # Return minimal state update that advances to next round
        return {
            "round_number": round_number + 1,
            "current_node": "parallel_round_skipped",
        }
    max_rounds = phase_state.get("max_rounds", 6)
    current_phase = _determine_phase(round_number, max_rounds)
    dlog.info(
        "Round phase determined",
        round_number=round_number,
        max_rounds=max_rounds,
        phase=current_phase,
    )

    # Select experts for this round
    selected_experts = await _select_experts_for_round(state, current_phase, round_number)
    dlog.info(
        "Experts selected",
        experts=len(selected_experts),
        phase=current_phase,
    )

    # Generate contributions in parallel
    contributions = await _generate_parallel_contributions(
        experts=selected_experts,
        state=state,
        phase=current_phase,
        round_number=round_number,
    )
    dlog.info("Contributions generated", contributions=len(contributions))

    # Apply semantic deduplication
    filtered_contributions = await _apply_semantic_deduplication(contributions)

    # Get problem context using accessor (handle dict from checkpoint deserialization)
    problem_state = get_problem_state(state)
    problem = problem_state.get("problem")
    problem_description = get_problem_description(problem)
    problem_context = problem_description or "No problem context available"
    problem_statement = problem_description or None

    # Initialize tracking objects
    metrics = ensure_metrics(state)
    _ = get_control_state(state)  # Validate state has control_state
    # Note: facilitator_guidance is not in ControlState, access directly from state
    facilitator_guidance = state.get("facilitator_guidance") or {}

    # Create quality check cache for this round (avoids re-checking duplicate content)
    from bo1.graph.quality.contribution_check import QualityCheckCache

    quality_cache = QualityCheckCache()

    # Check contribution quality
    quality_results, facilitator_guidance = await _check_contribution_quality(
        contributions=filtered_contributions,
        problem_context=problem_context,
        round_number=round_number,
        metrics=metrics,
        facilitator_guidance=facilitator_guidance,
        quality_cache=quality_cache,
    )

    # Summarize the round
    discussion_state_for_summaries = get_discussion_state(state)
    round_summaries = list(discussion_state_for_summaries.get("round_summaries", []))
    summary = await _summarize_round(
        contributions=filtered_contributions,
        round_number=round_number,
        current_phase=current_phase,
        problem_statement=problem_statement,
        metrics=metrics,
    )
    if summary:
        round_summaries.append(summary)

    # Detect research needs
    pending_research_queries = await _detect_research_needs(
        contributions=filtered_contributions,
        problem_context=problem_context,
        metrics=metrics,
    )

    # Build and return state update
    emit_node_duration("parallel_round_node", (time.perf_counter() - _start_time) * 1000)
    return _build_round_state_update(
        state=state,
        filtered_contributions=filtered_contributions,
        round_number=round_number,
        current_phase=current_phase,
        round_summaries=round_summaries,
        metrics=metrics,
        pending_research_queries=pending_research_queries,
        facilitator_guidance=facilitator_guidance,
        quality_results=quality_results,
    )
