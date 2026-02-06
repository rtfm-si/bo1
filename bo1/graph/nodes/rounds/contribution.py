"""Contribution generation for deliberation rounds.

Contains functions for generating parallel expert contributions,
building expert memory context, and retry logic.
"""

import asyncio
import logging
from typing import Any

from bo1.graph.nodes.utils import (
    get_phase_prompt,
    log_with_session,
    phase_prompt_short,
)
from bo1.graph.state import (
    DeliberationGraphState,
    get_core_state,
    get_discussion_state,
    get_participant_state,
    get_problem_state,
    get_research_state,
)
from bo1.graph.utils import ensure_metrics, track_accumulated_cost
from bo1.models.problem import SubProblem
from bo1.utils.checkpoint_helpers import get_problem_context, get_problem_description

logger = logging.getLogger(__name__)


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
    from bo1.graph.deliberation import build_dependency_context, build_subproblem_context_for_all
    from bo1.graph.nodes.rounds.quality import _handle_challenge_validation
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
                core_state = get_core_state(state)
                log_with_session(
                    logger,
                    logging.ERROR,
                    core_state.get("session_id"),
                    f"Retry FAILED for {expert.display_name}: {reason}. Using as fallback.",
                    request_id=core_state.get("request_id"),
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

    # Validate challenge phase contributions (rounds 3-4)
    if round_number in (3, 4):
        contribution_msgs = await _handle_challenge_validation(
            contribution_msgs=contribution_msgs,
            round_number=round_number,
            state=state,
            engine=engine,
            problem=problem,
            participant_list=participant_list,
            contrib_type=contrib_type,
            contributions=contributions,
            dependency_context=dependency_context,
            subproblem_context=subproblem_context,
            research_results=research_results,
            metrics=metrics,
        )

    return contribution_msgs
