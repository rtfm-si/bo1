"""Deliberation round nodes.

This module contains nodes for managing deliberation rounds:
- initial_round_node: First round of parallel persona contributions
- parallel_round_node: Subsequent rounds with multi-expert parallel execution
"""

import asyncio
import logging
from typing import Any

from bo1.graph.deliberation import (
    PhaseManager,
    build_dependency_context,
    build_subproblem_context_for_all,
)
from bo1.graph.deliberation import (
    select_experts_for_round as _select_experts_for_round,
)
from bo1.graph.nodes.utils import get_phase_prompt, phase_prompt_short
from bo1.graph.state import DeliberationGraphState
from bo1.graph.utils import ensure_metrics, track_accumulated_cost, track_aggregated_cost
from bo1.models.state import DeliberationPhase

logger = logging.getLogger(__name__)


async def initial_round_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Run initial round with parallel persona contributions.

    This node wraps the DeliberationEngine.run_initial_round() method
    and updates the graph state with the contributions.

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates
    """
    from bo1.orchestration.deliberation import DeliberationEngine

    logger.info("initial_round_node: Starting initial round")

    # Create deliberation engine with v2 state
    engine = DeliberationEngine(state=state)

    # Run initial round
    contributions, llm_responses = await engine.run_initial_round()

    # Track cost in metrics
    metrics = ensure_metrics(state)
    track_aggregated_cost(metrics, "initial_round", llm_responses)

    round_cost = sum(r.cost_total for r in llm_responses)

    logger.info(
        f"initial_round_node: Complete - {len(contributions)} contributions "
        f"(cost: ${round_cost:.4f})"
    )

    # Return state updates (include personas for event collection)
    # Set round_number=2 so next parallel_round will be round 2 (not duplicate round 1)
    return {
        "contributions": contributions,
        "phase": DeliberationPhase.DISCUSSION,
        "round_number": 2,  # Increment to 2 (initial round complete, next is round 2)
        "metrics": metrics,
        "current_node": "initial_round",
        "personas": state.get("personas", []),  # Include for event publishing
        "sub_problem_index": state.get("sub_problem_index", 0),  # Preserve sub_problem_index
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


async def _generate_parallel_contributions(
    experts: list[Any],  # list[PersonaProfile]
    state: DeliberationGraphState,
    phase: str,
    round_number: int,
) -> list[Any]:  # Returns list[ContributionMessage]
    """Generate contributions from multiple experts in parallel.

    Uses asyncio.gather to call all experts concurrently, reducing
    total round time from serial (n x LLM_latency) to parallel (1 x LLM_latency).

    Includes validation and retry logic for malformed responses:
    - Validates each contribution to detect meta-responses
    - Retries once with simplified prompt if validation fails
    - Falls back to placeholder if retry also fails

    Args:
        experts: List of PersonaProfile objects
        state: Current deliberation state
        phase: "exploration", "challenge", or "convergence"
        round_number: Current round number

    Returns:
        List of ContributionMessage objects
    """
    from bo1.llm.response_parser import ResponseParser
    from bo1.models.state import ContributionType
    from bo1.orchestration.deliberation import DeliberationEngine

    # Create engine with v2 state
    engine = DeliberationEngine(state=state)

    # Get problem context
    problem = state.get("problem")
    contributions = state.get("contributions", [])
    personas = state.get("personas", [])

    participant_list = ", ".join([p.name for p in personas])

    # Get phase-specific speaker prompt
    speaker_prompt = get_phase_prompt(phase, round_number)

    # Build context from sub-problem results (Phase 1.5 - Issue #22)
    sub_problem_results = state.get("sub_problem_results", [])
    current_sub_problem = state.get("current_sub_problem")  # SubProblem being deliberated

    # Build dependency context (Issue #22A - dependent sub-problems)
    dependency_context = None
    if current_sub_problem and sub_problem_results and problem:
        dependency_context = build_dependency_context(
            current_sp=current_sub_problem, sub_problem_results=sub_problem_results, problem=problem
        )

    # Build general sub-problem context (Issue #22B - all experts get context)
    subproblem_context = build_subproblem_context_for_all(sub_problem_results)

    # Get research results if available
    research_results = state.get("research_results", [])

    # Create tasks for all experts
    # NOTE: speaker_prompt is stored in expert_memory for now (until _call_persona_async is updated)
    tasks = []
    for expert in experts:
        # Build expert_memory with phase guidance + context
        memory_parts = [f"Phase Guidance: {speaker_prompt}"]

        # Add dependency context if available (for dependent sub-problems)
        if dependency_context:
            memory_parts.append(dependency_context)
            logger.debug(f"Added dependency context for {expert.display_name}")

        # Add general sub-problem context if available (for all experts)
        if subproblem_context:
            memory_parts.append(subproblem_context)
            logger.debug(f"Added sub-problem context for {expert.display_name}")

        # Add research results if available (proactive or facilitator-requested)
        if research_results:
            from bo1.agents.researcher import ResearcherAgent

            researcher = ResearcherAgent()
            research_context = researcher.format_research_context(research_results)
            memory_parts.append(research_context)
            logger.debug(
                f"Added {len(research_results)} research results to context for {expert.display_name}"
            )

        expert_memory = "\n\n".join(memory_parts)

        task = engine._call_persona_async(
            persona_profile=expert,
            problem_statement=problem.description if problem else "",
            problem_context=problem.context if problem else "",
            participant_list=participant_list,
            round_number=round_number,
            contribution_type=ContributionType.RESPONSE,
            previous_contributions=contributions,
            expert_memory=expert_memory,  # Pass phase prompt + context via memory field
        )
        tasks.append((expert, task))

    # Run all in parallel
    raw_results = await asyncio.gather(*[t[1] for t in tasks])
    expert_results = list(zip([t[0] for t in tasks], raw_results, strict=True))

    # Validate contributions and retry if needed
    contribution_msgs = []
    retry_tasks = []
    metrics = ensure_metrics(state)

    for expert, (contribution_msg, llm_response) in expert_results:
        # Validate contribution content
        is_valid, reason = ResponseParser.validate_contribution_content(
            contribution_msg.content, expert.display_name
        )

        if is_valid:
            contribution_msgs.append(contribution_msg)
            # Track cost
            phase_key = f"round_{round_number}_parallel_deliberation"
            track_accumulated_cost(metrics, phase_key, llm_response)
        else:
            # Malformed response - schedule retry
            logger.warning(
                f"Malformed contribution from {expert.display_name}: {reason}. Scheduling retry."
            )
            # Track cost for failed attempt
            phase_key = f"round_{round_number}_parallel_deliberation_retry"
            track_accumulated_cost(metrics, phase_key, llm_response)

            # Create retry task with simplified prompt + context
            retry_memory_parts = [
                f"RETRY - Please provide your expert analysis directly. "
                f"DO NOT apologize or discuss the prompt structure. "
                f"Focus on: {phase_prompt_short(phase)}"
            ]

            # Add context to retry as well (maintain consistency)
            if dependency_context:
                retry_memory_parts.append(dependency_context)
            if subproblem_context:
                retry_memory_parts.append(subproblem_context)

            # Add research results to retry context
            if research_results:
                from bo1.agents.researcher import ResearcherAgent

                researcher = ResearcherAgent()
                research_context = researcher.format_research_context(research_results)
                retry_memory_parts.append(research_context)

            retry_guidance = "\n\n".join(retry_memory_parts)

            retry_task = engine._call_persona_async(
                persona_profile=expert,
                problem_statement=problem.description if problem else "",
                problem_context=problem.context if problem else "",
                participant_list=participant_list,
                round_number=round_number,
                contribution_type=ContributionType.RESPONSE,
                previous_contributions=contributions,
                expert_memory=retry_guidance,
            )
            retry_tasks.append((expert, retry_task))

    # Execute retries if any
    if retry_tasks:
        logger.info(f"Retrying {len(retry_tasks)} malformed contributions")
        retry_results = await asyncio.gather(*[t[1] for t in retry_tasks])

        for (expert, _), (contribution_msg, llm_response) in zip(
            retry_tasks, retry_results, strict=True
        ):
            # Validate retry result
            is_valid, reason = ResponseParser.validate_contribution_content(
                contribution_msg.content, expert.display_name
            )

            if is_valid:
                logger.info(f"Retry successful for {expert.display_name}")
                contribution_msgs.append(contribution_msg)
            else:
                # Still invalid after retry - use as-is with warning
                logger.error(
                    f"Retry FAILED for {expert.display_name}: {reason}. "
                    "Using malformed contribution as fallback."
                )
                contribution_msgs.append(contribution_msg)

            # Track retry cost
            phase_key = f"round_{round_number}_parallel_deliberation_retry"
            track_accumulated_cost(metrics, phase_key, llm_response)

    # Calculate total cost
    base_cost = sum(r[1].cost_total for _, r in expert_results)
    retry_cost = sum(r[1].cost_total for r in retry_results) if retry_tasks else 0.0
    total_cost = base_cost + retry_cost
    logger.info(
        f"Parallel contributions: {len(contribution_msgs)} experts, cost: ${total_cost:.4f}"
    )

    return contribution_msgs


async def parallel_round_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Execute a round with multiple experts contributing in parallel.

    NEW PARALLEL ARCHITECTURE: Replaces serial persona_contribute_node with
    parallel multi-expert contributions per round.

    Flow:
    1. Determine phase (exploration/challenge/convergence) based on round number
    2. Select 2-5 experts based on phase, contribution balance, and novelty
    3. Generate contributions from all selected experts in parallel (asyncio.gather)
    4. Apply semantic deduplication to filter repetitive contributions
    5. Update state with filtered contributions and phase tracking

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates

    Phases:
        - Exploration (rounds 1-2): 3-5 experts, broad perspectives
        - Challenge (rounds 3-4): 2-3 experts, focused debate
        - Convergence (rounds 5+): 2-3 experts, synthesis

    Example:
        Round 1 (Exploration): 4 experts contribute in parallel
        Round 2 (Exploration): 3 experts contribute (semantic dedup filters 1)
        Round 3 (Challenge): 3 experts challenge previous points
        Round 4 (Convergence): 3 experts provide recommendations
    """
    from bo1.graph.quality.semantic_dedup import filter_duplicate_contributions

    logger.info("parallel_round_node: Starting parallel round with multiple experts")

    # Get current round and phase
    round_number = state.get("round_number", 1)
    max_rounds = state.get("max_rounds", 6)

    # Determine phase based on round number
    current_phase = _determine_phase(round_number, max_rounds)
    logger.info(f"Round {round_number}/{max_rounds}: Phase = {current_phase}")

    # Select experts for this round (phase-based selection)
    selected_experts = await _select_experts_for_round(state, current_phase, round_number)

    logger.info(
        f"parallel_round_node: {len(selected_experts)} experts selected for {current_phase} phase"
    )

    # Generate contributions in parallel
    contributions = await _generate_parallel_contributions(
        experts=selected_experts,
        state=state,
        phase=current_phase,
        round_number=round_number,
    )

    logger.info(f"parallel_round_node: {len(contributions)} contributions generated")

    # Apply semantic deduplication
    filtered_contributions = await filter_duplicate_contributions(
        contributions=contributions,
        threshold=0.80,  # 80% similarity = likely duplicate
    )

    filtered_count = len(contributions) - len(filtered_contributions)
    if filtered_count > 0:
        logger.info(
            f"parallel_round_node: Filtered {filtered_count} duplicate contributions "
            f"({filtered_count / len(contributions):.0%})"
        )

    # FAILSAFE: Ensure at least 1 contribution per round
    if not filtered_contributions and contributions:
        logger.warning(
            f"All {len(contributions)} contributions filtered as duplicates. "
            f"Keeping most novel contribution to ensure progress."
        )
        # Keep the first contribution (earliest in generation, likely most novel)
        filtered_contributions = [contributions[0]]
        logger.info(f"Failsafe: Kept contribution from {contributions[0].persona_name}")

    # Lightweight quality check after semantic deduplication
    quality_results: list[Any] = []
    facilitator_guidance = state.get("facilitator_guidance") or {}

    if filtered_contributions:
        from bo1.graph.quality.contribution_check import check_contributions_quality

        problem = state.get("problem")
        problem_context = problem.description if problem else "No problem context available"

        try:
            quality_results, quality_responses = await check_contributions_quality(
                contributions=filtered_contributions,
                problem_context=problem_context,
            )

            # Track cost for quality checks (before metrics might be used elsewhere)
            metrics = ensure_metrics(state)
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
                    f"{filtered_contributions[i].persona_name}: {quality_results[i].feedback}"
                    for i in range(len(quality_results))
                    if quality_results[i].is_shallow
                ]

                # Update facilitator guidance
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

        except Exception as e:
            logger.warning(f"Quality check failed: {e}. Continuing without quality feedback.")
            # Don't fail the round if quality check fails - it's a nice-to-have

    # Update state
    all_contributions = list(state.get("contributions", []))
    all_contributions.extend(filtered_contributions)

    # Track which experts contributed this round
    experts_per_round = list(state.get("experts_per_round", []))
    round_experts = [c.persona_code for c in filtered_contributions]
    experts_per_round.append(round_experts)

    # Track cost
    metrics = ensure_metrics(state)
    # Note: Cost tracking happens inside _generate_parallel_contributions

    # Increment round number
    next_round = round_number + 1

    # Trigger summarization for this round
    round_summaries = list(state.get("round_summaries", []))

    if round_number > 0:  # Don't summarize round 0
        from bo1.agents.summarizer import SummarizerAgent

        summarizer = SummarizerAgent()

        # Get contributions for this round only
        round_contributions = [
            {"persona": c.persona_name, "content": c.content} for c in filtered_contributions
        ]

        # Get problem statement for context
        problem = state.get("problem")
        problem_statement = problem.description if problem else None

        # Summarize the round (async)
        try:
            summary_response = await summarizer.summarize_round(
                round_number=round_number,
                contributions=round_contributions,
                problem_statement=problem_statement,
            )

            # Add summary to state
            round_summaries.append(summary_response.content)

            # Track cost
            track_accumulated_cost(metrics, "summarization", summary_response)

            logger.info(
                f"Round {round_number} summarized: {summary_response.token_usage.output_tokens} tokens, "
                f"${summary_response.cost_total:.6f}"
            )
        except Exception as e:
            logger.warning(f"Failed to summarize round {round_number}: {e}")
            # Add minimal fallback summary to preserve hierarchical mode
            expert_names = ", ".join([c.persona_name for c in filtered_contributions])
            fallback_summary = (
                f"Round {round_number} ({current_phase} phase): "
                f"{len(filtered_contributions)} contributions from {expert_names}. "
                f"(Detailed summary unavailable due to error: {str(e)[:50]})"
            )
            round_summaries.append(fallback_summary)
            logger.info(f"Added fallback summary for round {round_number}")

    # PROACTIVE RESEARCH DETECTION: Analyze contributions for research opportunities
    # This runs after deduplication but before returning, allowing research to inform next round
    pending_research_queries = []
    if filtered_contributions:
        from bo1.agents.research_detector import detect_and_trigger_research

        problem = state.get("problem")
        problem_context = problem.description if problem else "No problem context available"

        try:
            # Detect research needs in contributions (uses Haiku, ~$0.001 per contribution)
            detected_queries = await detect_and_trigger_research(
                contributions=filtered_contributions,
                problem_context=problem_context,
                min_confidence=0.75,  # Only trigger for high-confidence detections
            )

            if detected_queries:
                logger.info(
                    f"Proactive research detected: {len(detected_queries)} queries from "
                    f"{len(filtered_contributions)} contributions"
                )
                pending_research_queries = detected_queries

                # Track detection cost (approximate)
                detection_cost = len(filtered_contributions) * 0.001  # ~$0.001 per contribution
                metrics.total_cost += detection_cost
                logger.debug(f"Research detection cost: ${detection_cost:.4f}")
            else:
                logger.debug("No proactive research triggers detected in this round")

        except Exception as e:
            logger.warning(
                f"Proactive research detection failed: {e}. Continuing without detection."
            )
            # Don't fail the round if detection fails - it's a nice-to-have

    # Log quality metrics if available
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

    # Prepare return dict with updated state
    return_dict = {
        "contributions": all_contributions,
        "round_number": next_round,
        "current_phase": current_phase,
        "experts_per_round": experts_per_round,
        "round_summaries": round_summaries,
        "metrics": metrics,
        "current_node": "parallel_round",
        "personas": state.get("personas", []),  # Include for event publishing (archetype lookup)
        "sub_problem_index": state.get("sub_problem_index", 0),
        "pending_research_queries": pending_research_queries,  # Proactive research from this round
        "facilitator_guidance": facilitator_guidance,  # Include updated guidance
    }

    return return_dict
