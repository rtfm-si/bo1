"""Deliberation round nodes.

This module contains nodes for managing deliberation rounds:
- initial_round_node: First round of parallel persona contributions
- parallel_round_node: Subsequent rounds with multi-expert parallel execution
"""

import asyncio
import logging
import time
from typing import Any

from bo1.graph.deliberation import (
    PhaseManager,
    build_dependency_context,
    build_subproblem_context_for_all,
)
from bo1.graph.deliberation import (
    select_experts_for_round as _select_experts_for_round,
)
from bo1.graph.nodes.utils import (
    emit_node_duration,
    get_phase_prompt,
    log_with_session,
    phase_prompt_short,
)
from bo1.graph.quality.stopping_rules import update_stalled_disagreement_counter
from bo1.graph.state import (
    DeliberationGraphState,
    get_discussion_state,
    get_participant_state,
    get_phase_state,
    get_problem_state,
    get_research_state,
)
from bo1.graph.utils import ensure_metrics, track_accumulated_cost
from bo1.models.problem import SubProblem
from bo1.models.state import DeliberationPhase
from bo1.prompts.sanitizer import sanitize_user_input
from bo1.utils.checkpoint_helpers import get_problem_context, get_problem_description
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
    session_id = state.get("session_id")
    user_id = state.get("user_id")
    round_number = 1  # Initial round is always round 1
    dlog = get_deliberation_logger(session_id, user_id, "initial_round_node")
    dlog.info("Starting initial round")

    # Use nested state accessors for grouped field access
    discussion_state = get_discussion_state(state)
    participant_state = get_participant_state(state)
    phase_state = get_phase_state(state)
    problem_state = get_problem_state(state)

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
        "sub_problem_index": state.get("sub_problem_index", 0),
        "round_summaries": round_summaries,
        "facilitator_guidance": facilitator_guidance,
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


def _build_expert_memory(
    expert: Any,
    speaker_prompt: str,
    dependency_context: str | None,
    subproblem_context: str | None,
    research_results: list[Any],
) -> str:
    """Build context memory for a single expert.

    Args:
        expert: PersonaProfile object
        speaker_prompt: Phase-specific guidance
        dependency_context: Context from dependent sub-problems (optional)
        subproblem_context: General sub-problem context (optional)
        research_results: Research results to include (optional)

    Returns:
        Combined memory string for the expert
    """
    memory_parts = [f"Phase Guidance: {speaker_prompt}"]

    if dependency_context:
        memory_parts.append(dependency_context)
        logger.debug(f"Added dependency context for {expert.display_name}")

    if subproblem_context:
        memory_parts.append(subproblem_context)
        logger.debug(f"Added sub-problem context for {expert.display_name}")

    if research_results:
        from bo1.agents.researcher import ResearcherAgent

        researcher = ResearcherAgent()
        research_context = researcher.format_research_context(research_results)
        memory_parts.append(research_context)
        logger.debug(f"Added {len(research_results)} research results for {expert.display_name}")

    return "\n\n".join(memory_parts)


def _build_retry_memory(
    phase: str,
    dependency_context: str | None,
    subproblem_context: str | None,
    research_results: list[Any],
) -> str:
    """Build simplified retry memory for a failed contribution.

    Args:
        phase: Current phase name
        dependency_context: Context from dependent sub-problems (optional)
        subproblem_context: General sub-problem context (optional)
        research_results: Research results to include (optional)

    Returns:
        Combined retry guidance string
    """
    retry_parts = [
        f"RETRY - Please provide your expert analysis directly. "
        f"DO NOT apologize or discuss the prompt structure. "
        f"Focus on: {phase_prompt_short(phase)}"
    ]

    if dependency_context:
        retry_parts.append(dependency_context)
    if subproblem_context:
        retry_parts.append(subproblem_context)

    if research_results:
        from bo1.agents.researcher import ResearcherAgent

        researcher = ResearcherAgent()
        research_context = researcher.format_research_context(research_results)
        retry_parts.append(research_context)

    return "\n\n".join(retry_parts)


async def _generate_parallel_contributions(
    experts: list[Any],  # list[PersonaProfile]
    state: DeliberationGraphState,
    phase: str,
    round_number: int,
    contribution_type: str | None = None,  # "initial" or "response", defaults to "response"
    expert_memories: dict[str, str] | None = None,  # Per-expert memory overrides
) -> list[Any]:  # Returns list[ContributionMessage]
    """Generate contributions from multiple experts in parallel.

    Uses asyncio.gather to call all experts concurrently, reducing
    total round time from serial (n x LLM_latency) to parallel (1 x LLM_latency).

    Args:
        experts: List of PersonaProfile objects
        state: Current deliberation state
        phase: "exploration", "challenge", or "convergence"
        round_number: Current round number
        contribution_type: Type of contribution ("initial" or "response"), defaults to "response"
        expert_memories: Optional dict mapping expert code to memory string (for cross-sub-problem context)

    Returns:
        List of ContributionMessage objects
    """
    from bo1.llm.response_parser import ResponseParser
    from bo1.models.state import ContributionType
    from bo1.orchestration.deliberation import DeliberationEngine

    engine = DeliberationEngine(state=state)

    # Use nested state accessors for grouped field access
    problem_state = get_problem_state(state)
    discussion_state = get_discussion_state(state)
    participant_state = get_participant_state(state)
    research_state = get_research_state(state)

    problem = problem_state.get("problem")
    contributions = discussion_state.get("contributions", [])
    personas = participant_state.get("personas", [])
    participant_list = ", ".join([p.name for p in personas])
    speaker_prompt = get_phase_prompt(phase, round_number)

    # Determine contribution type
    contrib_type = (
        ContributionType.INITIAL if contribution_type == "initial" else ContributionType.RESPONSE
    )

    # Build context from accessors
    sub_problem_results = problem_state.get("sub_problem_results", [])
    current_sub_problem_raw = problem_state.get("current_sub_problem")
    research_results = research_state.get("research_results", [])

    # Validate current_sub_problem - may be dict after checkpoint restore
    current_sub_problem = None
    if current_sub_problem_raw:
        if isinstance(current_sub_problem_raw, dict):
            current_sub_problem = SubProblem.model_validate(current_sub_problem_raw)
        else:
            current_sub_problem = current_sub_problem_raw

    dependency_context = None
    if current_sub_problem and sub_problem_results and problem:
        dependency_context = build_dependency_context(
            current_sp=current_sub_problem, sub_problem_results=sub_problem_results, problem=problem
        )
    subproblem_context = build_subproblem_context_for_all(sub_problem_results)

    # Create and run tasks for all experts
    tasks = []
    for expert in experts:
        # Use per-expert memory override if provided, otherwise build standard memory
        if expert_memories and expert.code in expert_memories:
            expert_memory = expert_memories[expert.code]
            # Append phase guidance
            if speaker_prompt:
                expert_memory = f"Phase Guidance: {speaker_prompt}\n\n{expert_memory}"
        else:
            expert_memory = _build_expert_memory(
                expert, speaker_prompt, dependency_context, subproblem_context, research_results
            )
        task = engine._call_persona_async(
            persona_profile=expert,
            problem_statement=get_problem_description(problem),
            problem_context=get_problem_context(problem),
            participant_list=participant_list,
            round_number=round_number,
            contribution_type=contrib_type,
            previous_contributions=contributions,
            expert_memory=expert_memory,
        )
        tasks.append((expert, task))

    raw_results = await asyncio.gather(*[t[1] for t in tasks])
    expert_results = list(zip([t[0] for t in tasks], raw_results, strict=True))

    # Validate and collect results
    contribution_msgs = []
    retry_tasks = []
    metrics = ensure_metrics(state)

    for expert, (contribution_msg, llm_response) in expert_results:
        is_valid, reason = ResponseParser.validate_contribution_content(
            contribution_msg.content, expert.display_name
        )

        if is_valid:
            contribution_msgs.append(contribution_msg)
            track_accumulated_cost(
                metrics, f"round_{round_number}_parallel_deliberation", llm_response
            )
        else:
            logger.warning(
                f"Malformed contribution from {expert.display_name}: {reason}. Retrying."
            )
            track_accumulated_cost(
                metrics, f"round_{round_number}_parallel_deliberation_retry", llm_response
            )

            retry_memory = _build_retry_memory(
                phase, dependency_context, subproblem_context, research_results
            )
            retry_task = engine._call_persona_async(
                persona_profile=expert,
                problem_statement=get_problem_description(problem),
                problem_context=get_problem_context(problem),
                participant_list=participant_list,
                round_number=round_number,
                contribution_type=contrib_type,
                previous_contributions=contributions,
                expert_memory=retry_memory,
            )
            retry_tasks.append((expert, retry_task))

    # Execute retries
    if retry_tasks:
        logger.info(f"Retrying {len(retry_tasks)} malformed contributions")
        retry_results = await asyncio.gather(*[t[1] for t in retry_tasks])

        for (expert, _), (contribution_msg, llm_response) in zip(
            retry_tasks, retry_results, strict=True
        ):
            is_valid, reason = ResponseParser.validate_contribution_content(
                contribution_msg.content, expert.display_name
            )
            if is_valid:
                logger.info(f"Retry successful for {expert.display_name}")
            else:
                session_id = state.get("session_id")
                request_id = state.get("request_id")
                log_with_session(
                    logger,
                    logging.ERROR,
                    session_id,
                    f"Retry FAILED for {expert.display_name}: {reason}. Using as fallback.",
                    request_id=request_id,
                )
            contribution_msgs.append(contribution_msg)
            track_accumulated_cost(
                metrics, f"round_{round_number}_parallel_deliberation_retry", llm_response
            )

    # Log cost summary
    base_cost = sum(r[1].cost_total for _, r in expert_results)
    retry_cost = sum(r[1].cost_total for r in retry_results) if retry_tasks else 0.0
    logger.info(
        f"Parallel contributions: {len(contribution_msgs)} experts, cost: ${base_cost + retry_cost:.4f}"
    )

    return contribution_msgs


async def _apply_semantic_deduplication(
    contributions: list[Any],
) -> list[Any]:
    """Apply semantic deduplication to filter repetitive contributions.

    Uses embedding similarity to identify and filter duplicate contributions,
    ensuring at least one contribution survives for progress.

    Args:
        contributions: List of ContributionMessage objects

    Returns:
        Filtered list of contributions with duplicates removed
    """
    from bo1.graph.quality.semantic_dedup import filter_duplicate_contributions

    if not contributions:
        return []

    filtered = await filter_duplicate_contributions(
        contributions=contributions,
        threshold=0.80,  # 80% similarity = likely duplicate
    )

    filtered_count = len(contributions) - len(filtered)
    if filtered_count > 0:
        logger.info(
            f"Filtered {filtered_count} duplicate contributions "
            f"({filtered_count / len(contributions):.0%})"
        )

    # FAILSAFE: Ensure at least 1 contribution per round
    if not filtered and contributions:
        logger.warning(
            f"All {len(contributions)} contributions filtered as duplicates. "
            f"Keeping most novel contribution to ensure progress."
        )
        filtered = [contributions[0]]
        logger.info(f"Failsafe: Kept contribution from {contributions[0].persona_name}")

    return filtered


async def _check_contribution_quality(
    contributions: list[Any],
    problem_context: str,
    round_number: int,
    metrics: Any,
    facilitator_guidance: dict[str, Any],
    quality_cache: Any | None = None,
) -> tuple[list[Any], dict[str, Any]]:
    """Check quality of contributions and update facilitator guidance.

    Runs lightweight quality checks on contributions and adds guidance
    for the next round if shallow contributions are detected.

    Args:
        contributions: List of ContributionMessage objects
        problem_context: Problem description for context
        round_number: Current round number
        metrics: Metrics object for cost tracking
        facilitator_guidance: Existing facilitator guidance dict
        quality_cache: Optional QualityCheckCache for caching results

    Returns:
        Tuple of (quality_results, updated_facilitator_guidance)
    """
    from bo1.graph.quality.contribution_check import check_contributions_quality

    if not contributions:
        return [], facilitator_guidance

    try:
        quality_results, quality_responses = await check_contributions_quality(
            contributions=contributions,
            problem_context=problem_context,
            cache=quality_cache,
            round_number=round_number,
        )

        # Track cost for quality checks
        for response in quality_responses:
            if response:  # Skip None responses (heuristic fallbacks)
                track_accumulated_cost(metrics, f"round_{round_number}_quality_check", response)

        # Track quality metrics
        shallow_count = sum(1 for r in quality_results if r.is_shallow)
        avg_quality = sum(r.quality_score for r in quality_results) / len(quality_results)

        logger.info(
            f"Quality check: {shallow_count}/{len(quality_results)} shallow, "
            f"avg score: {avg_quality:.2f}"
        )

        # If any contributions are shallow, add guidance for next round
        if shallow_count > 0:
            shallow_feedback = [
                f"{contributions[i].persona_name}: {quality_results[i].feedback}"
                for i in range(len(quality_results))
                if quality_results[i].is_shallow
            ]

            if "quality_issues" not in facilitator_guidance:
                facilitator_guidance["quality_issues"] = []

            facilitator_guidance["quality_issues"].append(
                {
                    "round": round_number,
                    "shallow_count": shallow_count,
                    "total_count": len(quality_results),
                    "feedback": shallow_feedback,
                    "guidance": (
                        f"Round {round_number} had {shallow_count} shallow contributions. "
                        f"Next round: emphasize concrete details, evidence, and actionable steps."
                    ),
                }
            )

            logger.info(
                f"Added quality guidance for next round: {shallow_count} shallow contributions"
            )

        return quality_results, facilitator_guidance

    except Exception as e:
        logger.warning(f"Quality check failed: {e}. Continuing without quality feedback.")
        return [], facilitator_guidance


async def _summarize_round(
    contributions: list[Any],
    round_number: int,
    current_phase: str,
    problem_statement: str | None,
    metrics: Any,
) -> str | None:
    """Summarize contributions from a round.

    Creates a summary of the round's contributions for hierarchical context.

    Args:
        contributions: List of ContributionMessage objects
        round_number: Current round number
        current_phase: Current deliberation phase
        problem_statement: Problem description for context
        metrics: Metrics object for cost tracking

    Returns:
        Summary string or fallback summary on error
    """
    from bo1.agents.summarizer import SummarizerAgent

    if round_number <= 0 or not contributions:
        return None

    summarizer = SummarizerAgent()
    round_contributions = [{"persona": c.persona_name, "content": c.content} for c in contributions]

    try:
        summary_response = await summarizer.summarize_round(
            round_number=round_number,
            contributions=round_contributions,
            problem_statement=problem_statement,
        )

        track_accumulated_cost(metrics, "summarization", summary_response)

        logger.info(
            f"Round {round_number} summarized: {summary_response.token_usage.output_tokens} tokens, "
            f"${summary_response.cost_total:.6f}"
        )
        # Sanitize summary before re-injection into subsequent prompts
        return sanitize_user_input(summary_response.content, context="round_summary")

    except Exception as e:
        logger.warning(f"Failed to summarize round {round_number}: {e}")
        expert_names = ", ".join([c.persona_name for c in contributions])
        fallback_summary = (
            f"Round {round_number} ({current_phase} phase): "
            f"{len(contributions)} contributions from {expert_names}. "
            f"(Detailed summary unavailable due to error: {str(e)[:50]})"
        )
        logger.info(f"Added fallback summary for round {round_number}")
        return fallback_summary


async def _detect_research_needs(
    contributions: list[Any],
    problem_context: str,
    metrics: Any,
) -> list[Any]:
    """Detect research needs in contributions.

    Analyzes contributions for research opportunities and returns
    queries for proactive research.

    Args:
        contributions: List of ContributionMessage objects
        problem_context: Problem description for context
        metrics: Metrics object for cost tracking

    Returns:
        List of detected research queries
    """
    from bo1.agents.research_detector import detect_and_trigger_research

    if not contributions:
        return []

    try:
        detected_queries = await detect_and_trigger_research(
            contributions=contributions,
            problem_context=problem_context,
            min_confidence=0.75,  # Only trigger for high-confidence detections
        )

        if detected_queries:
            logger.info(
                f"Proactive research detected: {len(detected_queries)} queries from "
                f"{len(contributions)} contributions"
            )
            # Track detection cost (approximate)
            detection_cost = len(contributions) * 0.001  # ~$0.001 per contribution
            metrics.total_cost += detection_cost
            logger.debug(f"Research detection cost: ${detection_cost:.4f}")
        else:
            logger.debug("No proactive research triggers detected in this round")

        return detected_queries

    except Exception as e:
        logger.warning(f"Proactive research detection failed: {e}. Continuing without detection.")
        return []


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

    # Update contributions
    all_contributions = list(discussion_state.get("contributions", []))
    all_contributions.extend(filtered_contributions)

    # Track which experts contributed this round
    experts_per_round = list(participant_state.get("experts_per_round", []))
    round_experts = [c.persona_code for c in filtered_contributions]
    experts_per_round.append(round_experts)

    next_round = round_number + 1

    # Count meta-discussion contributions for context sufficiency detection
    meta_discussion_count = state.get("meta_discussion_count", 0)
    total_contributions_checked = state.get("total_contributions_checked", 0)

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
    consecutive_research_without_improvement = state.get(
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

    return {
        "contributions": all_contributions,
        "round_number": next_round,
        "current_phase": current_phase,
        "experts_per_round": experts_per_round,
        "round_summaries": round_summaries,
        "metrics": metrics,
        "current_node": "parallel_round",
        "personas": state.get("personas", []),
        "sub_problem_index": state.get("sub_problem_index", 0),
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
    session_id = state.get("session_id")
    user_id = state.get("user_id")
    dlog = get_deliberation_logger(session_id, user_id, "parallel_round_node")
    dlog.info("Starting parallel round with multiple experts")

    # Use nested state accessors for grouped field access
    phase_state = get_phase_state(state)
    discussion_state = get_discussion_state(state)

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
    round_summaries = list(state.get("round_summaries", []))
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
