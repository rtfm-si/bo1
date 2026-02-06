"""Synthesize node: Creates synthesis from deliberation."""

import logging
import time
from typing import Any

from bo1.config import TokenBudgets, get_model_for_role
from bo1.graph.nodes.utils import emit_node_duration, log_with_session
from bo1.graph.state import (
    DeliberationGraphState,
    get_context_state,
    get_core_state,
    get_discussion_state,
    get_phase_state,
    get_problem_state,
    prune_contributions_for_phase,
)
from bo1.graph.utils import ensure_metrics, track_phase_cost
from bo1.models.state import DeliberationPhase
from bo1.prompts.synthesis import (
    compose_continuation_prompt,
    detect_overflow,
    strip_continuation_marker,
)
from bo1.utils.checkpoint_helpers import get_problem_attr
from bo1.utils.deliberation_logger import get_deliberation_logger

logger = logging.getLogger(__name__)


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

    # Use nested state accessors for grouped field access
    core_state = get_core_state(state)
    problem_state = get_problem_state(state)
    discussion_state = get_discussion_state(state)
    phase_state = get_phase_state(state)
    context_state = get_context_state(state)

    session_id = core_state.get("session_id")
    user_id = core_state.get("user_id")
    request_id = core_state.get("request_id")
    dlog = get_deliberation_logger(session_id, user_id, "synthesize_node")
    dlog.info("Starting synthesis with hierarchical template")

    log_with_session(
        logger, logging.INFO, session_id, "synthesize_node: Starting", request_id=request_id
    )

    # Prune contributions to reduce token usage (post-convergence)
    # Safe: synthesis uses round_summaries for context, not raw contributions
    pruned_contributions = prune_contributions_for_phase(state)

    # Get problem and contributions
    problem = problem_state.get("problem")
    contributions = pruned_contributions
    votes = discussion_state.get("votes", [])
    round_summaries = discussion_state.get("round_summaries", [])
    current_round = phase_state.get("round_number", 1)

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
    limited_context_mode = context_state.get("limited_context_mode", False)
    prompt_section, output_section = get_limited_context_sections(limited_context_mode)

    if limited_context_mode:
        logger.info("synthesize_node: Limited context mode active - including assumptions section")

    # Compose synthesis prompt using hierarchical template
    synthesis_prompt = SYNTHESIS_HIERARCHICAL_TEMPLATE.format(
        problem_statement=get_problem_attr(problem, "description", ""),
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
        warning_threshold = int(TokenBudgets.SYNTHESIS * 0.9)
        if output_tokens >= warning_threshold:
            log_with_session(
                logger,
                logging.WARNING,
                session_id,
                f"[TOKEN_BUDGET] Synthesis output tokens ({output_tokens}) "
                f">= 90% of budget ({TokenBudgets.SYNTHESIS}). "
                f"Sub-problem: {problem_state.get('sub_problem_index', 0)}",
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
        "sub_problem_index": problem_state.get(
            "sub_problem_index", 0
        ),  # Preserve sub_problem_index
        "contributions": contributions,  # Pruned contributions (reduces Redis payload)
    }
