"""Synthesis and voting nodes.

This module contains nodes for the final stages of deliberation:
- vote_node: Collects recommendations from all personas
- synthesize_node: Creates synthesis from deliberation
- next_subproblem_node: Handles transition between sub-problems
- meta_synthesize_node: Creates cross-sub-problem meta-synthesis
"""

import asyncio
import json
import logging
import time
from typing import Any

from bo1.config import get_model_for_role
from bo1.graph.nodes.utils import emit_node_duration, log_with_session
from bo1.graph.state import DeliberationGraphState, prune_contributions_for_phase
from bo1.graph.utils import ensure_metrics, track_aggregated_cost, track_phase_cost
from bo1.models.state import DeliberationPhase, SubProblemResult
from bo1.prompts.synthesis import (
    META_SYNTHESIS_MAX_TOKENS,
    SYNTHESIS_MAX_TOKENS,
    SYNTHESIS_TOKEN_WARNING_THRESHOLD,
    compose_continuation_prompt,
    detect_overflow,
    strip_continuation_marker,
)
from bo1.utils.checkpoint_helpers import get_sub_problem_goal_safe, get_sub_problem_id_safe
from bo1.utils.deliberation_logger import get_deliberation_logger

logger = logging.getLogger(__name__)


def _get_problem_attr(problem: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute from problem (handles both dict and object).

    After checkpoint restoration, Problem objects may be deserialized as dicts.
    This helper handles both cases.
    """
    if problem is None:
        return default
    if isinstance(problem, dict):
        return problem.get(attr, default)
    return getattr(problem, attr, default)


def _get_subproblem_attr(sp: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute from sub-problem (handles both dict and object).

    After checkpoint restoration, SubProblem objects may be deserialized as dicts.
    This helper handles both cases.

    For 'id' and 'goal' attributes, uses safe helpers that detect and handle
    corrupted values (e.g., type annotation lists like ['bo1', 'models', ...]).
    """
    if sp is None:
        return default

    # Use safe accessors for id and goal to handle corruption
    if attr == "id":
        result = get_sub_problem_id_safe(sp, logger)
        return result if result else default
    if attr == "goal":
        result = get_sub_problem_goal_safe(sp, logger)
        return result if result else default

    # Standard access for other attributes
    if isinstance(sp, dict):
        return sp.get(attr, default)
    return getattr(sp, attr, default)


async def vote_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Collect recommendations from all personas.

    This node wraps the collect_recommendations() function from voting.py
    and updates the graph state with the collected recommendations.

    IMPORTANT: Recommendation System (NOT Voting)
    - Uses free-form text recommendations, NOT binary votes
    - Legacy "votes" key retained for backward compatibility
    - Recommendation model: persona_code, persona_name, recommendation (string),
      reasoning, confidence (0-1), conditions (list), weight
    - See bo1/models/recommendations.py for Recommendation model
    - See bo1/orchestration/voting.py:collect_recommendations() for implementation

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates (votes, recommendations, metrics)
    """
    from bo1.llm.broker import PromptBroker
    from bo1.orchestration.voting import collect_recommendations

    _start_time = time.perf_counter()
    session_id = state.get("session_id")
    user_id = state.get("user_id")
    dlog = get_deliberation_logger(session_id, user_id, "vote_node")
    dlog.info("Starting recommendation collection phase")

    # Create broker for LLM calls
    broker = PromptBroker()

    # Collect recommendations from all personas with v2 state
    recommendations, llm_responses = await collect_recommendations(state=state, broker=broker)

    # Track cost in metrics
    metrics = ensure_metrics(state)
    track_aggregated_cost(metrics, "voting", llm_responses)

    rec_cost = sum(r.cost_total for r in llm_responses)

    dlog.info(
        "Recommendations collected",
        recommendations=len(recommendations),
        cost=f"${rec_cost:.4f}",
    )

    # Convert Recommendation objects to dicts for state storage
    recommendations_dicts = [
        {
            "persona_code": r.persona_code,
            "persona_name": r.persona_name,
            "recommendation": r.recommendation,
            "reasoning": r.reasoning,
            "confidence": r.confidence,
            "conditions": r.conditions,
            "weight": r.weight,
        }
        for r in recommendations
    ]

    # Return state updates
    # Keep "votes" key for backward compatibility during migration
    emit_node_duration("vote_node", (time.perf_counter() - _start_time) * 1000)
    return {
        "votes": recommendations_dicts,
        "recommendations": recommendations_dicts,
        "phase": DeliberationPhase.VOTING,
        "metrics": metrics,
        "current_node": "vote",
        "sub_problem_index": state.get("sub_problem_index", 0),  # Preserve sub_problem_index
    }


async def synthesize_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Synthesize final recommendation from deliberation using lean McKinsey-style template.

    Uses hierarchical summarization + lean output format for complete, premium results:
    - Round summaries provide deliberation evolution (already condensed)
    - Final round contributions provide detail
    - Output follows Pyramid Principle: answer first, then support
    - Structured sections: Bottom Line, Why It Matters, Next Steps, Risks, Confidence
    - Expected output: ~800-1000 tokens (fits within 1500 limit with headroom)

    Args:
        state: Current graph state (must have votes and contributions)

    Returns:
        Dictionary with state updates (synthesis report, phase=COMPLETE)
    """
    from bo1.llm.broker import PromptBroker, PromptRequest
    from bo1.prompts import SYNTHESIS_HIERARCHICAL_TEMPLATE, get_limited_context_sections

    _start_time = time.perf_counter()
    session_id = state.get("session_id")
    user_id = state.get("user_id")
    request_id = state.get("request_id")
    dlog = get_deliberation_logger(session_id, user_id, "synthesize_node")
    dlog.info("Starting synthesis with hierarchical template")

    log_with_session(
        logger, logging.INFO, session_id, "synthesize_node: Starting", request_id=request_id
    )

    # Prune contributions to reduce token usage (post-convergence)
    # Safe: synthesis uses round_summaries for context, not raw contributions
    pruned_contributions = prune_contributions_for_phase(state)

    # Get problem and contributions
    problem = state.get("problem")
    contributions = pruned_contributions
    votes = state.get("votes", [])
    round_summaries = state.get("round_summaries", [])
    current_round = state.get("round_number", 1)

    if not problem:
        raise ValueError("synthesize_node called without problem in state")

    # AUDIT FIX (Priority 3, Task 3.1): Hierarchical context composition
    # Build round summaries section (rounds 1 to N-1)
    round_summaries_text = []
    if round_summaries:
        for i, summary in enumerate(round_summaries, start=1):
            round_summaries_text.append(f"Round {i}: {summary}")
    else:
        round_summaries_text.append("(No round summaries available)")

    # Build final round contributions (only contributions from final round)
    final_round_contributions = []
    final_round_num = current_round  # Current round is the final one

    # Get contributions from final round only
    final_round_contribs = [c for c in contributions if c.round_number == final_round_num]

    if final_round_contribs:
        for contrib in final_round_contribs:
            final_round_contributions.append(f"{contrib.persona_name}:\n{contrib.content}\n")
    else:
        # Fallback: if no final round contributions, use last 3 contributions
        logger.warning("synthesize_node: No final round contributions found, using last 3")
        for contrib in contributions[-3:]:
            final_round_contributions.append(
                f"Round {contrib.round_number} - {contrib.persona_name}:\n{contrib.content}\n"
            )

    # Format votes/recommendations
    votes_text = []
    for vote in votes:
        votes_text.append(
            f"{vote['persona_name']}: {vote['recommendation']} "
            f"(confidence: {vote['confidence']:.2f})\n"
            f"Reasoning: {vote['reasoning']}\n"
        )
        conditions = vote.get("conditions")
        if conditions and isinstance(conditions, list):
            votes_text.append(f"Conditions: {', '.join(str(c) for c in conditions)}\n")
        votes_text.append("\n")

    # Check for limited context mode (Option D+E Hybrid - Phase 8)
    limited_context_mode = state.get("limited_context_mode", False)
    prompt_section, output_section = get_limited_context_sections(limited_context_mode)

    if limited_context_mode:
        logger.info("synthesize_node: Limited context mode active - including assumptions section")

    # Compose synthesis prompt using hierarchical template
    synthesis_prompt = SYNTHESIS_HIERARCHICAL_TEMPLATE.format(
        problem_statement=_get_problem_attr(problem, "description", ""),
        round_summaries="\n".join(round_summaries_text),
        final_round_contributions="\n".join(final_round_contributions),
        votes="\n".join(votes_text),
        limited_context_section=prompt_section,
        limited_context_output_section=output_section,
    )

    logger.info(
        f"synthesize_node: Context built - {len(round_summaries)} round summaries, "
        f"{len(final_round_contribs)} final round contributions, {len(votes)} votes"
    )

    # Create broker and request
    broker = PromptBroker()

    # Initialize metrics early (needed for overflow continuation tracking)
    metrics = ensure_metrics(state)

    # Centralized model selection (respects experiment overrides and TASK_MODEL_DEFAULTS)
    synthesis_model = get_model_for_role("synthesis")
    log_with_session(
        logger,
        logging.INFO,
        session_id,
        f"synthesize_node: Using model={synthesis_model}",
    )

    request = PromptRequest(
        system=synthesis_prompt,
        user_message="Generate the synthesis report now. Follow the XML output format exactly.",
        prefill="<synthesis_report>\n<executive_summary>",
        model=synthesis_model,
        temperature=0.7,
        max_tokens=2000,  # Hierarchical template produces ~800-1200 tokens, leaving headroom
        phase="synthesis",
        agent_type="synthesizer",
        cache_system=True,  # Enable prompt caching (system prompt = static template)
    )

    # Call LLM
    response = await broker.call(request)

    # TOKEN BUDGET WARNING: Check if output tokens approach/exceed budget
    if response.token_usage:
        output_tokens = response.token_usage.output_tokens
        warning_threshold = int(SYNTHESIS_MAX_TOKENS * SYNTHESIS_TOKEN_WARNING_THRESHOLD)
        if output_tokens >= warning_threshold:
            log_with_session(
                logger,
                logging.WARNING,
                session_id,
                f"[TOKEN_BUDGET] Synthesis output tokens ({output_tokens}) "
                f">= {int(SYNTHESIS_TOKEN_WARNING_THRESHOLD * 100)}% of budget ({SYNTHESIS_MAX_TOKENS}). "
                f"Sub-problem: {state.get('sub_problem_index', 0)}",
            )

    # Clean up response - prepend the prefill since it's not included in response
    raw_content = response.content.strip()
    synthesis_report = "<synthesis_report>\n<executive_summary>" + raw_content

    # OVERFLOW HANDLING: Check for truncation or continuation markers
    overflow_status = detect_overflow(synthesis_report, is_truncated=response.is_truncated)

    if overflow_status.needs_continuation:
        log_with_session(
            logger,
            logging.WARNING,
            session_id,
            f"[OVERFLOW] Synthesis truncated, initiating continuation. "
            f"cursor={overflow_status.cursor}, is_truncated={response.is_truncated}",
        )

        # Build continuation prompt
        continuation_prompt = compose_continuation_prompt(
            previous_output=synthesis_report,
            cursor=overflow_status.cursor,
        )

        continuation_request = PromptRequest(
            system=synthesis_prompt,
            user_message=continuation_prompt,
            model=synthesis_model,
            temperature=0.7,
            max_tokens=1500,  # Smaller budget for continuation
            phase="synthesis_continuation",
            agent_type="synthesizer",
            cache_system=True,
        )

        continuation_response = await broker.call(continuation_request)

        # Merge outputs: strip marker from original, append continuation
        clean_original = strip_continuation_marker(synthesis_report)
        synthesis_report = clean_original + "\n" + continuation_response.content.strip()

        # Track continuation cost
        track_phase_cost(metrics, "synthesis_continuation", continuation_response)

        log_with_session(
            logger,
            logging.INFO,
            session_id,
            f"[OVERFLOW] Continuation complete. Added {len(continuation_response.content)} chars. "
            f"Total synthesis: {len(synthesis_report)} chars",
        )

    # ISSUE #2 FIX: Validate synthesis is not empty/suspiciously short
    synthesis_length = len(synthesis_report)
    if synthesis_length < 100:
        logger.warning(
            f"synthesize_node: SYNTHESIS WARNING - Suspiciously short synthesis "
            f"({synthesis_length} chars). This may indicate extraction issues. "
            f"Content preview: {synthesis_report[:200]}"
        )

    # Add AI-generated content disclaimer
    disclaimer = (
        "\n\n---\n\n"
        "Warning: This content is AI-generated for learning and knowledge purposes only, "
        "not professional advisory.\n\n"
        "Always verify recommendations using licensed legal/financial professionals "
        "for your location."
    )
    synthesis_report_with_disclaimer = synthesis_report + disclaimer

    # Track cost in metrics (metrics already initialized earlier for overflow handling)
    track_phase_cost(metrics, "synthesis", response)

    logger.info(
        f"synthesize_node: Complete - synthesis generated "
        f"({synthesis_length} chars, cost: ${response.cost_total:.4f})"
    )

    # Return state updates (include pruned contributions to reduce checkpoint size)
    emit_node_duration("synthesize_node", (time.perf_counter() - _start_time) * 1000)
    return {
        "synthesis": synthesis_report_with_disclaimer,
        "phase": DeliberationPhase.SYNTHESIS,  # Don't set COMPLETE yet - may have more sub-problems
        "metrics": metrics,
        "current_node": "synthesize",
        "sub_problem_index": state.get("sub_problem_index", 0),  # Preserve sub_problem_index
        "contributions": contributions,  # Pruned contributions (reduces Redis payload)
    }


async def next_subproblem_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Move to next sub-problem after synthesis.

    This node:
    1. Saves the current sub-problem result (synthesis, votes, costs)
    2. Generates per-expert summaries for memory
    3. Increments sub_problem_index
    4. If more sub-problems: resets deliberation state and sets next sub-problem
    5. If all complete: triggers meta-synthesis by setting current_sub_problem=None

    GUARD: Checks if result already exists for current sub_problem_index to prevent
    double-processing on graph retry (atomicity fix).

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates
    """
    from bo1.agents.summarizer import SummarizerAgent

    # Extract current sub-problem data
    current_sp = state.get("current_sub_problem")
    problem = state.get("problem")
    sub_problem_index = state.get("sub_problem_index", 0)
    previous_results = state.get("sub_problem_results", [])

    # Debug logging to trace state corruption after checkpoint restore
    session_id = state.get("session_id")
    log_with_session(
        logger,
        logging.DEBUG,
        session_id,
        f"next_subproblem_node: current_sub_problem type={type(current_sp).__name__}, "
        f"value={current_sp if isinstance(current_sp, dict) else repr(current_sp)[:200]}",
    )

    # GUARD: Check if result already exists for current index (prevents double-processing)
    # This can happen on graph retry or checkpoint edge cases
    current_sp_id = _get_subproblem_attr(current_sp, "id", None) if current_sp else None

    # Guard: Ensure current_sp_id is hashable (string expected)
    # State corruption after checkpoint restore can cause id to be a list
    if current_sp_id and not isinstance(current_sp_id, str):
        session_id = state.get("session_id")
        log_with_session(
            logger,
            logging.ERROR,
            session_id,
            f"next_subproblem_node: current_sub_problem.id is not a string! "
            f"Got type={type(current_sp_id).__name__}, value={current_sp_id}. "
            f"This indicates state corruption. Skipping guard check.",
        )
        current_sp_id = None  # Skip guard check, proceed with normal flow

    if current_sp_id:
        # Build set of existing result IDs, handling both object and dict forms
        existing_result_ids: set[str] = set()
        for r in previous_results:
            sp_id = (
                r.get("sub_problem_id")
                if isinstance(r, dict)
                else getattr(r, "sub_problem_id", None)
            )
            if isinstance(sp_id, str):
                existing_result_ids.add(sp_id)

        if current_sp_id in existing_result_ids:
            session_id = state.get("session_id")
            log_with_session(
                logger,
                logging.WARNING,
                session_id,
                f"next_subproblem_node: Result already exists for sub-problem {current_sp_id} "
                f"(index {sub_problem_index}) - skipping to avoid double-processing",
            )
            # Return minimal update - don't add duplicate result
            sub_problems = _get_problem_attr(problem, "sub_problems", [])
            next_index = sub_problem_index + 1
            if next_index < len(sub_problems):
                return {
                    "current_sub_problem": sub_problems[next_index],
                    "sub_problem_index": next_index,
                    "current_node": "next_subproblem_skipped",
                }
            else:
                return {
                    "current_sub_problem": None,
                    "current_node": "next_subproblem_skipped",
                }
    contributions = state.get("contributions", [])
    votes = state.get("votes", [])
    personas = state.get("personas", [])
    synthesis = state.get("synthesis", "")
    metrics = state.get("metrics")
    # sub_problem_index and previous_results already declared above (for guard check)

    # Enhanced logging for sub-problem progression (Bug #3 fix)
    session_id = state.get("session_id")
    sub_problems = _get_problem_attr(problem, "sub_problems", [])
    total_sub_problems = len(sub_problems) if sub_problems else 0
    log_with_session(
        logger,
        logging.INFO,
        session_id,
        f"next_subproblem_node: Saving result for sub-problem {sub_problem_index + 1}/{total_sub_problems}: "
        f"{_get_subproblem_attr(current_sp, 'goal', 'unknown')}",
    )

    if not current_sp:
        raise ValueError("next_subproblem_node called without current_sub_problem")

    if not problem:
        raise ValueError("next_subproblem_node called without problem")

    # Calculate cost for this sub-problem (all phase costs accumulated)
    # For simplicity, use total_cost - sum of previous sub-problem costs
    total_cost_so_far = metrics.total_cost if metrics else 0.0
    # previous_results already declared above (for guard check)
    previous_cost: float = sum(
        (
            float(r.cost if hasattr(r, "cost") else r.get("cost", 0.0))  # type: ignore[attr-defined]
            for r in previous_results
        ),
        0.0,
    )
    sub_problem_cost = total_cost_so_far - previous_cost

    # Track duration (placeholder - could enhance with actual timing)
    duration_seconds = 0.0

    # Generate per-expert summaries for memory (if there are contributions)
    expert_summaries: dict[str, str] = {}

    if contributions:
        summarizer = SummarizerAgent()

        # P2 BATCH FIX: Run all expert summarizations in PARALLEL using asyncio.gather
        # This reduces latency by 60-80% (from sequential N*200ms to parallel ~200ms)
        async def summarize_expert(persona: Any) -> tuple[str, str, Any] | None:
            """Summarize a single expert's contributions."""
            expert_contributions = [c for c in contributions if c.persona_code == persona.code]
            if not expert_contributions:
                return None

            # Convert contributions to dict format for summarizer
            contribution_dicts = [
                {"persona": c.persona_name, "content": c.content} for c in expert_contributions
            ]

            # Summarize expert's contributions
            response = await summarizer.summarize_round(
                round_number=state.get("round_number", 1),
                contributions=contribution_dicts,
                problem_statement=_get_subproblem_attr(current_sp, "goal", ""),
                target_tokens=75,  # Concise summary for memory
            )

            return (persona.code, persona.display_name, response)

        # Run all summarizations in parallel
        logger.info(f"Running {len(personas)} expert summarizations in parallel (BATCH)")
        results = await asyncio.gather(
            *[summarize_expert(p) for p in personas],
            return_exceptions=True,
        )

        # Process results
        total_memory_cost = 0.0
        for gather_result in results:
            if gather_result is None:
                continue  # No contributions for this expert
            if isinstance(gather_result, BaseException):
                logger.warning(f"Expert summarization failed: {gather_result}")
                continue

            persona_code, display_name, response = gather_result
            expert_summaries[persona_code] = response.content
            total_memory_cost += response.cost_total

            logger.info(
                f"Generated memory summary for {display_name}: "
                f"{response.token_usage.output_tokens} tokens, ${response.cost_total:.6f}"
            )

        # Track total cost once (not per-expert)
        if metrics and total_memory_cost > 0:
            phase_costs = metrics.phase_costs
            phase_costs["expert_memory"] = phase_costs.get("expert_memory", 0.0) + total_memory_cost

    # Create SubProblemResult
    result = SubProblemResult(
        sub_problem_id=_get_subproblem_attr(current_sp, "id", ""),
        sub_problem_goal=_get_subproblem_attr(current_sp, "goal", ""),
        synthesis=synthesis or "",  # Ensure not None
        votes=votes,
        contribution_count=len(contributions),
        cost=sub_problem_cost,
        duration_seconds=duration_seconds,
        expert_panel=[p.code for p in personas],
        expert_summaries=expert_summaries,
    )

    # Add to results
    sub_problem_results = list(previous_results)
    sub_problem_results.append(result)

    # Save SP boundary checkpoint to PostgreSQL for resume capability
    if session_id:
        try:
            from bo1.state.repositories.session_repository import session_repository

            # Determine if this is the first SP (need to set total_sub_problems)
            is_first_sp = sub_problem_index == 0
            session_repository.update_sp_checkpoint(
                session_id=session_id,
                last_completed_sp_index=sub_problem_index,
                total_sub_problems=total_sub_problems if is_first_sp else None,
            )
            log_with_session(
                logger,
                logging.INFO,
                session_id,
                f"next_subproblem_node: Saved SP checkpoint {sub_problem_index + 1}/{total_sub_problems}",
            )
        except Exception as e:
            # Non-blocking: checkpoint failure shouldn't stop deliberation
            log_with_session(
                logger,
                logging.WARNING,
                session_id,
                f"next_subproblem_node: Failed to save SP checkpoint: {e}",
            )

    # Increment index
    next_index = sub_problem_index + 1

    # Check if more sub-problems
    if next_index < len(sub_problems):
        next_sp = sub_problems[next_index]

        logger.info(
            f"Moving to sub-problem {next_index + 1}/{len(sub_problems)}: {_get_subproblem_attr(next_sp, 'goal', 'unknown')}"
        )

        return {
            "current_sub_problem": next_sp,
            "sub_problem_index": next_index,
            "sub_problem_results": sub_problem_results,
            "round_number": 0,  # Will be set to 1 by initial_round_node
            "contributions": [],
            "votes": [],
            "synthesis": None,
            "facilitator_decision": None,
            "should_stop": False,
            "stop_reason": None,
            "round_summaries": [],  # Reset for new sub-problem
            "personas": [],  # Will be re-selected by select_personas_node
            "phase": DeliberationPhase.DECOMPOSITION,  # Ready for new sub-problem
            "metrics": metrics,  # Keep metrics (accumulates across sub-problems)
            "current_node": "next_subproblem",
            "completed_research_queries": [],  # Reset research tracking for new sub-problem
        }
    else:
        # All complete -> meta-synthesis
        logger.info("All sub-problems complete, proceeding to meta-synthesis")
        return {
            "current_sub_problem": None,
            "sub_problem_results": sub_problem_results,
            "phase": DeliberationPhase.SYNTHESIS,  # Meta-synthesis phase
            "current_node": "next_subproblem",
        }


async def meta_synthesize_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Create cross-sub-problem meta-synthesis with structured action plan.

    This node integrates insights from ALL sub-problem deliberations into
    a unified, actionable recommendation in JSON format.

    Args:
        state: Current graph state (must have sub_problem_results)

    Returns:
        Dictionary with state updates (meta-synthesis JSON action plan, phase=COMPLETE)
    """
    from bo1.llm.broker import PromptBroker, PromptRequest
    from bo1.prompts import META_SYNTHESIS_ACTION_PLAN_PROMPT

    _start_time = time.perf_counter()
    session_id = state.get("session_id")
    log_with_session(
        logger,
        logging.INFO,
        session_id,
        "meta_synthesize_node: Starting meta-synthesis (structured JSON)",
    )

    # Get problem and sub-problem results
    problem = state.get("problem")
    sub_problem_results_raw = state.get("sub_problem_results", [])

    if not problem:
        raise ValueError("meta_synthesize_node called without problem")

    if not sub_problem_results_raw:
        raise ValueError("meta_synthesize_node called without sub_problem_results")

    # P0 FIX: Normalize sub_problem_results from dicts back to SubProblemResult objects
    # After checkpoint restoration, these may be dicts instead of Pydantic models
    sub_problem_results: list[SubProblemResult] = []
    for result in sub_problem_results_raw:
        if isinstance(result, dict):
            sub_problem_results.append(SubProblemResult.model_validate(result))
            logger.debug(
                f"meta_synthesize_node: Normalized dict result for {result.get('sub_problem_id', 'unknown')}"
            )
        else:
            sub_problem_results.append(result)

    # P0 DEBUG: Log synthesis lengths to diagnose 14-token issue
    for i, result in enumerate(sub_problem_results):
        synthesis_len = len(result.synthesis) if result.synthesis else 0
        logger.info(
            f"meta_synthesize_node: Sub-problem {i} ({result.sub_problem_id}) synthesis length: {synthesis_len} chars, "
            f"votes: {len(result.votes)}, contributions: {result.contribution_count}"
        )
        if synthesis_len == 0:
            logger.warning(
                f"meta_synthesize_node: EMPTY SYNTHESIS for sub-problem {result.sub_problem_id}!"
            )

    # Get sub_problems list (handles both dict and object)
    meta_sub_problems = _get_problem_attr(problem, "sub_problems", [])

    # Format all sub-problem syntheses
    formatted_results = []
    total_cost = 0.0
    total_duration = 0.0

    for i, result in enumerate(sub_problem_results, 1):
        # Find the sub-problem by ID (handle both dict and object sub-problems)
        sp = None
        for sub_p in meta_sub_problems:
            sp_id = sub_p.get("id") if isinstance(sub_p, dict) else sub_p.id
            if sp_id == result.sub_problem_id:
                sp = sub_p
                break
        sp_goal = (
            (sp.get("goal") if isinstance(sp, dict) else sp.goal) if sp else result.sub_problem_goal
        )

        # Format votes
        votes_summary = []
        for vote in result.votes:
            votes_summary.append(
                f"- {vote.get('persona_name', 'Unknown')}: {vote.get('recommendation', 'N/A')} "
                f"(confidence: {vote.get('confidence', 0.0):.2f})"
            )

        formatted_results.append(
            f"""## Sub-Problem {i} ({result.sub_problem_id}): {sp_goal}

**Synthesis:**
{result.synthesis}

**Expert Recommendations:**
{chr(10).join(votes_summary) if votes_summary else "No votes recorded"}

**Deliberation Metrics:**
- Contributions: {result.contribution_count}
- Cost: ${result.cost:.4f}
- Experts: {", ".join(result.expert_panel)}
"""
        )
        total_cost += result.cost
        total_duration += result.duration_seconds

    # Create meta-synthesis prompt (structured JSON)
    meta_prompt = META_SYNTHESIS_ACTION_PLAN_PROMPT.format(
        original_problem=_get_problem_attr(problem, "description", ""),
        problem_context=_get_problem_attr(problem, "context") or "No additional context provided",
        sub_problem_count=len(sub_problem_results),
        all_sub_problem_syntheses="\n\n---\n\n".join(formatted_results),
    )

    # Create broker and request
    broker = PromptBroker()

    # Centralized model selection (respects experiment overrides and TASK_MODEL_DEFAULTS)
    meta_synthesis_model = get_model_for_role("meta_synthesis")
    log_with_session(
        logger,
        logging.INFO,
        session_id,
        f"meta_synthesize_node: Using model={meta_synthesis_model}",
    )

    request = PromptRequest(
        system=meta_prompt,
        user_message="Generate the JSON action plan now:",
        prefill="{",  # Force pure JSON output (no markdown, no XML wrapper)
        model=meta_synthesis_model,
        temperature=0.7,
        max_tokens=4000,
        phase="meta_synthesis",
        agent_type="meta_synthesizer",
        cache_system=True,  # Enable prompt caching (system prompt = static meta-synthesis template)
    )

    # Call LLM
    response = await broker.call(request)

    # TOKEN BUDGET WARNING: Check if output tokens approach/exceed budget
    if response.token_usage:
        output_tokens = response.token_usage.output_tokens
        warning_threshold = int(META_SYNTHESIS_MAX_TOKENS * SYNTHESIS_TOKEN_WARNING_THRESHOLD)
        if output_tokens >= warning_threshold:
            log_with_session(
                logger,
                logging.WARNING,
                session_id,
                f"[TOKEN_BUDGET] Meta-synthesis output tokens ({output_tokens}) "
                f">= {int(SYNTHESIS_TOKEN_WARNING_THRESHOLD * 100)}% of budget ({META_SYNTHESIS_MAX_TOKENS}). "
                f"Sub-problems: {len(sub_problem_results)}",
            )

    # Prepend prefill to get complete JSON (including opening brace)
    json_content = "{" + response.content

    # Parse and validate JSON
    try:
        action_plan = json.loads(json_content)
        logger.info("meta_synthesize_node: Successfully parsed JSON action plan")
    except json.JSONDecodeError as e:
        logger.warning(f"meta_synthesize_node: Failed to parse JSON, using fallback: {e}")
        # Fallback to plain text if JSON parsing fails
        action_plan = None
        json_content = response.content

    # Store both JSON and formatted output
    if action_plan:
        # Create readable markdown from JSON for backwards compatibility
        meta_synthesis = f"""# Action Plan

{action_plan.get("synthesis_summary", "")}

## Recommended Actions

"""
        for i, action in enumerate(action_plan.get("recommended_actions", []), 1):
            meta_synthesis += f"""### {i}. {action.get("action", "N/A")} [{action.get("priority", "medium").upper()}]

**Timeline:** {action.get("timeline", "TBD")}

**Rationale:** {action.get("rationale", "N/A")}

**Success Metrics:**
{chr(10).join(f"- {m}" for m in action.get("success_metrics", []))}

**Risks:**
{chr(10).join(f"- {r}" for r in action.get("risks", []))}

---

"""
    else:
        # Fallback to plain content
        meta_synthesis = json_content

    # Add deliberation summary footer
    footer = f"""

---

## Deliberation Summary

- **Original problem**: {_get_problem_attr(problem, "description", "")}
- **Sub-problems deliberated**: {len(sub_problem_results)}
- **Total contributions**: {sum(r.contribution_count for r in sub_problem_results)}
- **Total cost**: ${total_cost:.4f}
- **Meta-synthesis cost**: ${response.cost_total:.4f}
- **Grand total cost**: ${total_cost + response.cost_total:.4f}

Warning: This content is AI-generated for learning and knowledge purposes only, not professional advisory.
Always verify recommendations using licensed legal/financial professionals for your location.
"""

    # Store JSON in synthesis field for frontend parsing
    if action_plan:
        # Frontend will parse this JSON
        meta_synthesis_final = json_content + footer
    else:
        meta_synthesis_final = meta_synthesis + footer

    # Track cost in metrics
    metrics = ensure_metrics(state)
    track_phase_cost(metrics, "meta_synthesis", response)

    logger.info(
        f"meta_synthesize_node: Complete - meta-synthesis generated "
        f"(cost: ${response.cost_total:.4f}, total: ${metrics.total_cost:.4f})"
    )

    # Return state updates
    emit_node_duration("meta_synthesize_node", (time.perf_counter() - _start_time) * 1000)
    return {
        "synthesis": meta_synthesis_final,
        "phase": DeliberationPhase.COMPLETE,
        "metrics": metrics,
        "current_node": "meta_synthesis",
    }
