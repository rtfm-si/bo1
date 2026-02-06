"""Moderation and facilitation nodes.

This module contains nodes for moderating and facilitating deliberation:
- facilitator_decide_node: Decides next action (continue/vote/moderator/research)
- moderator_intervene_node: Handles moderator interventions
"""

import logging
import time
from dataclasses import asdict
from typing import Any, Literal

from bo1.agents.facilitator import FacilitatorAgent, FacilitatorDecision
from bo1.config import TokenBudgets
from bo1.constants import ModerationConfig, SimilarityCacheThresholds
from bo1.graph.nodes.utils import emit_node_duration, log_with_session
from bo1.graph.quality.semantic_dedup import check_research_query_novelty
from bo1.graph.state import (
    DeliberationGraphState,
    ResearchState,
    get_core_state,
    get_discussion_state,
    get_participant_state,
    get_phase_state,
    get_problem_state,
    get_research_state,
)
from bo1.graph.utils import ensure_metrics, track_accumulated_cost
from bo1.models.state import DeliberationPhase

logger = logging.getLogger(__name__)


def _select_least_speaking_persona(
    personas: list[Any],
    contributions: list[Any],
) -> str:
    """Select the persona with the fewest contributions.

    Args:
        personas: List of PersonaProfile objects
        contributions: List of ContributionMessage objects

    Returns:
        Persona code of the least-speaking persona
    """
    counts: dict[str, int] = {}
    for c in contributions:
        counts[c.persona_code] = counts.get(c.persona_code, 0) + 1
    min_count = min(counts.values()) if counts else 0
    candidates = [p.code for p in personas if counts.get(p.code, 0) == min_count]
    return candidates[0] if candidates else personas[0].code if personas else "unknown"


def _validate_and_override_decision(
    decision: FacilitatorDecision,
    state: DeliberationGraphState,
    personas: list[Any],
    round_number: int,
    session_id: str | None,
    request_id: str | None,
    research_state: dict[str, Any] | ResearchState,
) -> FacilitatorDecision:
    """Validate facilitator decision and apply safety overrides.

    Handles:
    - Speaker validation (missing/invalid next_speaker)
    - Moderator type fallback
    - Research query validation
    - Premature voting prevention
    - Duplicate research prevention
    """
    persona_codes = [p.code for p in personas]

    # --- Field validation ---
    if decision.action == "continue":
        if not decision.next_speaker:
            log_with_session(
                logger,
                logging.ERROR,
                session_id,
                "facilitator_decide_node: 'continue' without next_speaker! Falling back.",
                request_id=request_id,
            )
            decision.next_speaker = persona_codes[0] if persona_codes else "unknown"
            decision.reasoning = (
                f"ERROR RECOVERY: Selected {decision.next_speaker} due to missing next_speaker"
            )
        elif decision.next_speaker not in persona_codes:
            log_with_session(
                logger,
                logging.ERROR,
                session_id,
                f"facilitator_decide_node: Invalid next_speaker '{decision.next_speaker}' "
                f"not in {persona_codes}. Falling back.",
                request_id=request_id,
            )
            decision.next_speaker = persona_codes[0] if persona_codes else "unknown"
            decision.reasoning = f"ERROR RECOVERY: Selected {decision.next_speaker} because original speaker was invalid"

    elif decision.action == "moderator":
        if not decision.moderator_type:
            log_with_session(
                logger,
                logging.ERROR,
                session_id,
                "facilitator_decide_node: 'moderator' without moderator_type! Defaulting to contrarian.",
                request_id=request_id,
            )
            decision.moderator_type = "contrarian"
            decision.reasoning = "ERROR RECOVERY: Using contrarian moderator due to missing type"

    elif decision.action == "research":
        if not decision.research_query and not decision.reasoning:
            log_with_session(
                logger,
                logging.ERROR,
                session_id,
                "facilitator_decide_node: 'research' without query or reasoning! Overriding to continue.",
                request_id=request_id,
            )
            decision.action = "continue"
            decision.next_speaker = persona_codes[0] if persona_codes else "unknown"
            decision.reasoning = "ERROR RECOVERY: Skipping research due to missing query"

    # --- Premature voting prevention ---
    min_rounds = ModerationConfig.MIN_ROUNDS_BEFORE_VOTING
    if decision.action == "vote" and round_number < min_rounds:
        logger.warning(
            f"Facilitator attempted vote at round {round_number} (min: {min_rounds}). Overriding."
        )
        contributions = get_discussion_state(state).get("contributions", [])
        next_speaker = _select_least_speaking_persona(personas, contributions)
        decision = FacilitatorDecision(
            action="continue",
            reasoning=f"Overridden: Minimum {min_rounds} rounds required before voting.",
            next_speaker=next_speaker,
            speaker_prompt="Build on the discussion so far and add depth to the analysis.",
        )

    # --- Duplicate research prevention ---
    if decision.action == "research":
        completed_queries = research_state.get("completed_research_queries", [])
        research_query = decision.reasoning[:200] if decision.reasoning else ""
        is_duplicate = False
        if completed_queries and research_query:
            is_duplicate, _similarity = check_research_query_novelty(
                research_query,
                completed_queries,
                threshold=SimilarityCacheThresholds.RESEARCH_DEDUP,
            )
        if is_duplicate:
            contributions = get_discussion_state(state).get("contributions", [])
            next_speaker = _select_least_speaking_persona(personas, contributions)
            decision = FacilitatorDecision(
                action="continue",
                reasoning="Research already completed for this topic. Continuing deliberation.",
                next_speaker=next_speaker,
                speaker_prompt="Build on the research findings and add your unique perspective.",
            )

    return decision


async def facilitator_decide_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Make facilitator decision on next action (continue/vote/moderator).

    This node wraps the FacilitatorAgent.decide_next_action() method
    and updates the graph state with the facilitator's decision.

    NEW: Checks for pending_research_queries from proactive detection and
    automatically triggers research before making facilitator decision.

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates
    """
    _start_time = time.perf_counter()

    # Use nested state accessors for grouped field access
    core_state = get_core_state(state)
    phase_state = get_phase_state(state)
    problem_state = get_problem_state(state)
    research_state = get_research_state(state)

    session_id = core_state.get("session_id")
    request_id = core_state.get("request_id")
    log_with_session(
        logger,
        logging.INFO,
        session_id,
        "facilitator_decide_node: Making facilitator decision",
        request_id=request_id,
    )

    # PROACTIVE RESEARCH EXECUTION: Check for pending research queries from previous round
    # If queries exist, automatically trigger research node without facilitator decision
    pending_queries = research_state.get("pending_research_queries", [])
    if pending_queries:
        log_with_session(
            logger,
            logging.INFO,
            session_id,
            f"facilitator_decide_node: {len(pending_queries)} pending research queries detected. "
            f"Triggering proactive research.",
        )

        # Create a facilitator decision to trigger research
        # Use the first query's reason as the decision reasoning
        research_decision = FacilitatorDecision(
            action="research",
            reasoning=f"Proactive research triggered: {pending_queries[0].get('reason', 'Information gap detected')}",
            next_speaker=None,
            speaker_prompt=None,
            research_query="; ".join(
                [q.get("question", "") for q in pending_queries[:3]]
            ),  # Batch up to 3 queries
        )

        # Return decision to route to research node
        # Clear pending queries so they're processed by research_node
        return {
            "facilitator_decision": asdict(research_decision),
            "round_number": phase_state.get("round_number", 1),
            "phase": DeliberationPhase.DISCUSSION,
            "current_node": "facilitator_decide",
            "sub_problem_index": problem_state.get("sub_problem_index", 0),
            # Note: pending_research_queries will be consumed by research_node
        }

    # Create facilitator agent
    facilitator = FacilitatorAgent()

    # Get current round number and max rounds from accessor
    round_number = phase_state.get("round_number", 1)
    max_rounds = phase_state.get("max_rounds", 6)

    # Call facilitator to decide next action with v2 state
    decision, llm_response = await facilitator.decide_next_action(
        state=state,
        round_number=round_number,
        max_rounds=max_rounds,
    )

    # TOKEN BUDGET WARNING: Check if output tokens approach/exceed budget
    if llm_response and llm_response.token_usage:
        output_tokens = llm_response.token_usage.output_tokens
        warning_threshold = int(TokenBudgets.FACILITATOR * 0.9)
        if output_tokens >= warning_threshold:
            log_with_session(
                logger,
                logging.WARNING,
                session_id,
                f"[TOKEN_BUDGET] Facilitator output tokens ({output_tokens}) "
                f">= 90% of budget ({TokenBudgets.FACILITATOR}). "
                f"Action: {decision.action}, Round: {round_number}/{max_rounds}",
            )

    # Validate and apply safety overrides
    participant_state = get_participant_state(state)
    personas = participant_state.get("personas", [])
    decision = _validate_and_override_decision(
        decision,
        state,
        personas,
        round_number,
        session_id,
        request_id,
        research_state,
    )

    # Track cost in metrics (if LLM was called)
    metrics = ensure_metrics(state)

    if llm_response:
        track_accumulated_cost(metrics, "facilitator_decision", llm_response)
        cost_msg = f"(cost: ${llm_response.cost_total:.4f})"
    else:
        cost_msg = "(no LLM call)"

    # Enhanced logging with sub_problem_index for debugging (Issue #3 fix)
    sub_problem_index = problem_state.get("sub_problem_index", 0)
    log_with_session(
        logger,
        logging.INFO,
        session_id,
        f"facilitator_decide_node: Complete - action={decision.action}, "
        f"next_speaker={decision.next_speaker if decision.action == 'continue' else 'N/A'}, "
        f"sub_problem_index={sub_problem_index} {cost_msg}",
    )

    # Build state updates
    state_updates: dict[str, Any] = {
        "facilitator_decision": asdict(decision),
        "round_number": round_number,  # Pass through current round for display
        "phase": DeliberationPhase.DISCUSSION,
        "metrics": metrics,
        "current_node": "facilitator_decide",
        "sub_problem_index": sub_problem_index,  # CRITICAL: Always preserve sub_problem_index (Issue #3 fix)
    }

    # If clarify action, set pending_clarification for clarification_node
    if decision.action == "clarify":
        state_updates["pending_clarification"] = {
            "question": decision.clarification_question or decision.reasoning,
            "reason": decision.clarification_reason or "Facilitator requested clarification",
            "round_number": round_number,
        }
        logger.info(
            f"facilitator_decide_node: Set pending_clarification for question: "
            f"'{(decision.clarification_question or decision.reasoning)[:50]}...'"
        )

    emit_node_duration("facilitator_decide_node", (time.perf_counter() - _start_time) * 1000)
    return state_updates


async def moderator_intervene_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Moderator intervenes to challenge premature consensus.

    TARGETED USE: Only called when facilitator detects unanimous agreement
    before round 3. Prevents groupthink and premature convergence.

    This node:
    1. Calls the ModeratorAgent to intervene (contrarian type)
    2. Adds the intervention as a contribution
    3. Tracks cost
    4. Returns updated state

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates (intervention contribution added)
    """
    from bo1.agents.moderator import ModeratorAgent
    from bo1.models.state import ContributionMessage, ContributionType

    _start_time = time.perf_counter()

    # Use nested state accessors for grouped field access
    core_state = get_core_state(state)
    problem_state = get_problem_state(state)
    discussion_state = get_discussion_state(state)
    phase_state = get_phase_state(state)

    session_id = core_state.get("session_id")
    log_with_session(
        logger,
        logging.INFO,
        session_id,
        "moderator_intervene_node: Moderator intervening for premature consensus",
    )

    # Create moderator agent
    moderator = ModeratorAgent()

    # Get facilitator decision for intervention type
    decision = state.get("facilitator_decision")  # ephemeral - direct access

    # Extract moderator type with proper type handling (default to contrarian for premature consensus)
    moderator_type_value = decision.get("moderator_type") if decision else None
    if moderator_type_value and isinstance(moderator_type_value, str):
        # Validate it's one of the allowed types
        if moderator_type_value in ("contrarian", "skeptic", "optimist"):
            moderator_type: Literal["contrarian", "skeptic", "optimist"] = moderator_type_value
        else:
            moderator_type = "contrarian"
    else:
        # Default to contrarian for challenging premature consensus
        moderator_type = "contrarian"

    # Get problem and contributions from accessors
    problem = problem_state.get("problem")
    contributions = list(discussion_state.get("contributions", []))

    # Build discussion excerpt from recent contributions
    # Uses centralized ModerationConfig.RECENT_CONTRIBUTIONS_WINDOW
    window = ModerationConfig.RECENT_CONTRIBUTIONS_WINDOW
    recent_contributions = (
        contributions[-window:] if len(contributions) >= window else contributions
    )
    discussion_excerpt = "\n\n".join(
        [f"{c.persona_name}: {c.content}" for c in recent_contributions]
    )

    # Get trigger reason from facilitator decision
    moderator_focus = decision.get("moderator_focus") if decision else None
    trigger_reason = (
        moderator_focus
        if moderator_focus and isinstance(moderator_focus, str)
        else "premature unanimous agreement detected"
    )

    # Call moderator with correct signature
    intervention_text, llm_response = await moderator.intervene(
        moderator_type=moderator_type,
        problem_statement=problem.description if problem else "",
        discussion_excerpt=discussion_excerpt,
        trigger_reason=trigger_reason,
    )

    # Create ContributionMessage from moderator intervention
    moderator_name = moderator_type.capitalize() if moderator_type else "Moderator"
    intervention_msg = ContributionMessage(
        persona_code="moderator",
        persona_name=f"{moderator_name} Moderator",
        content=intervention_text,
        contribution_type=ContributionType.MODERATOR,
        round_number=phase_state.get("round_number", 1),
        thinking=None,
        token_count=llm_response.token_usage.output_tokens if llm_response.token_usage else None,
        cost=llm_response.cost if hasattr(llm_response, "cost") else None,
    )

    # Track cost in metrics
    metrics = ensure_metrics(state)
    phase_key = f"moderator_intervention_{moderator_type}"
    track_accumulated_cost(metrics, phase_key, llm_response)

    # Add intervention to contributions
    contributions.append(intervention_msg)

    log_with_session(
        logger,
        logging.INFO,
        session_id,
        f"moderator_intervene_node: Complete - {moderator_type} intervention "
        f"(cost: ${llm_response.cost_total:.4f})",
    )

    # Return state updates
    emit_node_duration("moderator_intervene_node", (time.perf_counter() - _start_time) * 1000)
    return {
        "contributions": contributions,
        "metrics": metrics,
        "current_node": "moderator_intervene",
        "sub_problem_index": problem_state.get(
            "sub_problem_index", 0
        ),  # Preserve sub_problem_index
    }
