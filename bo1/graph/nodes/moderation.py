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
from bo1.graph.nodes.utils import emit_node_duration, log_with_session
from bo1.graph.state import DeliberationGraphState
from bo1.graph.utils import ensure_metrics, track_accumulated_cost
from bo1.models.state import DeliberationPhase
from bo1.prompts.moderator import (
    FACILITATOR_MAX_TOKENS,
    FACILITATOR_TOKEN_WARNING_THRESHOLD,
)

logger = logging.getLogger(__name__)


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
    session_id = state.get("session_id")
    log_with_session(
        logger, logging.INFO, session_id, "facilitator_decide_node: Making facilitator decision"
    )

    # PROACTIVE RESEARCH EXECUTION: Check for pending research queries from previous round
    # If queries exist, automatically trigger research node without facilitator decision
    pending_queries = state.get("pending_research_queries", [])
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
            "round_number": state.get("round_number", 1),
            "phase": DeliberationPhase.DISCUSSION,
            "current_node": "facilitator_decide",
            "sub_problem_index": state.get("sub_problem_index", 0),
            # Note: pending_research_queries will be consumed by research_node
        }

    # Create facilitator agent
    facilitator = FacilitatorAgent()

    # Get current round number and max rounds
    round_number = state.get("round_number", 1)
    max_rounds = state.get("max_rounds", 6)

    # Call facilitator to decide next action with v2 state
    decision, llm_response = await facilitator.decide_next_action(
        state=state,
        round_number=round_number,
        max_rounds=max_rounds,
    )

    # TOKEN BUDGET WARNING: Check if output tokens approach/exceed budget
    if llm_response and llm_response.token_usage:
        output_tokens = llm_response.token_usage.output_tokens
        warning_threshold = int(FACILITATOR_MAX_TOKENS * FACILITATOR_TOKEN_WARNING_THRESHOLD)
        if output_tokens >= warning_threshold:
            log_with_session(
                logger,
                logging.WARNING,
                session_id,
                f"[TOKEN_BUDGET] Facilitator output tokens ({output_tokens}) "
                f">= {int(FACILITATOR_TOKEN_WARNING_THRESHOLD * 100)}% of budget ({FACILITATOR_MAX_TOKENS}). "
                f"Action: {decision.action}, Round: {round_number}/{max_rounds}",
            )

    # VALIDATION: Ensure decision is complete and valid (Issue #3 fix)
    # This prevents silent failures when facilitator returns invalid decisions
    personas = state.get("personas", [])
    persona_codes = [p.code for p in personas]

    if decision.action == "continue":
        # Validate next_speaker exists in personas
        if not decision.next_speaker:
            logger.error(
                "facilitator_decide_node: 'continue' action without next_speaker! "
                "Falling back to first available persona."
            )
            # Fallback: select first persona
            decision.next_speaker = persona_codes[0] if persona_codes else "unknown"
            decision.reasoning = f"ERROR RECOVERY: Selected {decision.next_speaker} due to missing next_speaker in facilitator decision"

        elif decision.next_speaker not in persona_codes:
            logger.error(
                f"facilitator_decide_node: Invalid next_speaker '{decision.next_speaker}' "
                f"not in selected personas: {persona_codes}. Falling back to first available persona."
            )
            # Fallback: select first persona
            decision.next_speaker = persona_codes[0] if persona_codes else "unknown"
            decision.reasoning = f"ERROR RECOVERY: Selected {decision.next_speaker} because original speaker was invalid"

    elif decision.action == "moderator":
        # Validate moderator_type exists
        if not decision.moderator_type:
            logger.error(
                "facilitator_decide_node: 'moderator' action without moderator_type! "
                "Defaulting to contrarian moderator."
            )
            # Fallback: default to contrarian
            decision.moderator_type = "contrarian"
            decision.reasoning = "ERROR RECOVERY: Using contrarian moderator due to missing type"

    elif decision.action == "research":
        # Validate research_query exists
        if not decision.research_query and not decision.reasoning:
            logger.error(
                "facilitator_decide_node: 'research' action without research_query or reasoning! "
                "Overriding to 'continue' to prevent failure."
            )
            # Fallback: skip research, continue with discussion
            decision.action = "continue"
            decision.next_speaker = persona_codes[0] if persona_codes else "unknown"
            decision.reasoning = (
                "ERROR RECOVERY: Skipping research due to missing query, continuing discussion"
            )

    # SAFETY CHECK: Prevent premature voting (Bug #3 fix)
    # Override facilitator if trying to vote before minimum rounds
    # NOTE: Research action is now fully implemented and no longer overridden
    # NEW PARALLEL ARCHITECTURE: Reduced from 3 to 2 (with 3-5 experts per round, 2 rounds = 6-10 contributions)
    min_rounds_before_voting = 2
    if decision.action == "vote" and round_number < min_rounds_before_voting:
        logger.warning(
            f"Facilitator attempted to vote at round {round_number} (min: {min_rounds_before_voting}). "
            f"Overriding to 'continue' for deeper exploration."
        )
        override_reason = f"Overridden: Minimum {min_rounds_before_voting} rounds required before voting. Need deeper exploration."

        # Override decision to continue
        # Select a persona who hasn't spoken much
        personas = state.get("personas", [])
        contributions = state.get("contributions", [])

        # Count contributions per persona
        contribution_counts: dict[str, int] = {}
        for contrib in contributions:
            persona_code = contrib.persona_code
            contribution_counts[persona_code] = contribution_counts.get(persona_code, 0) + 1

        # Find persona with fewest contributions
        min_contributions = min(contribution_counts.values()) if contribution_counts else 0
        candidates = [
            p.code for p in personas if contribution_counts.get(p.code, 0) == min_contributions
        ]

        next_speaker = candidates[0] if candidates else personas[0].code if personas else "unknown"

        # Override decision
        decision = FacilitatorDecision(
            action="continue",
            reasoning=override_reason,
            next_speaker=next_speaker,
            speaker_prompt="Build on the discussion so far and add depth to the analysis.",
        )

    # SAFETY CHECK: Prevent infinite research loops (Bug fix)
    # Check if facilitator is requesting research that's already been completed
    if decision.action == "research":
        completed_queries = state.get("completed_research_queries", [])

        # Extract research query from facilitator reasoning
        research_query = decision.reasoning[:200] if decision.reasoning else ""

        # Check semantic similarity to completed queries
        is_duplicate = False
        if completed_queries and research_query:
            from bo1.llm.embeddings import cosine_similarity, generate_embedding

            try:
                query_embedding = generate_embedding(research_query, input_type="query")

                for completed in completed_queries:
                    completed_embedding = completed.get("embedding")
                    if not completed_embedding:
                        continue

                    similarity = cosine_similarity(query_embedding, completed_embedding)

                    # High similarity threshold (0.85) = very similar query
                    # Lowered from 0.90 to catch more similar queries (P1-RESEARCH-1)
                    if similarity > 0.85:
                        is_duplicate = True
                        logger.warning(
                            f"Research deduplication: Query too similar to completed research "
                            f"(similarity={similarity:.3f}). Overriding to 'continue'. "
                            f"Query: '{research_query[:50]}...' ~ '{completed.get('query', '')[:50]}...'"
                        )
                        break

            except Exception as e:
                logger.warning(
                    f"Research deduplication check failed: {e}. Allowing research to proceed."
                )

        # Override to 'continue' if duplicate research detected
        if is_duplicate:
            # Select next speaker (same logic as premature voting override)
            personas = state.get("personas", [])
            contributions = state.get("contributions", [])

            research_contrib_counts: dict[str, int] = {}
            for contrib in contributions:
                persona_code = contrib.persona_code
                research_contrib_counts[persona_code] = (
                    research_contrib_counts.get(persona_code, 0) + 1
                )

            min_contributions_research = (
                min(research_contrib_counts.values()) if research_contrib_counts else 0
            )
            candidates_research = [
                p.code
                for p in personas
                if research_contrib_counts.get(p.code, 0) == min_contributions_research
            ]

            next_speaker = (
                candidates_research[0]
                if candidates_research
                else personas[0].code
                if personas
                else "unknown"
            )

            decision = FacilitatorDecision(
                action="continue",
                reasoning="Research already completed for this topic. Continuing deliberation with fresh perspectives.",
                next_speaker=next_speaker,
                speaker_prompt="Build on the research findings and add your unique perspective to the analysis.",
            )

    # Track cost in metrics (if LLM was called)
    metrics = ensure_metrics(state)

    if llm_response:
        track_accumulated_cost(metrics, "facilitator_decision", llm_response)
        cost_msg = f"(cost: ${llm_response.cost_total:.4f})"
    else:
        cost_msg = "(no LLM call)"

    # Enhanced logging with sub_problem_index for debugging (Issue #3 fix)
    sub_problem_index = state.get("sub_problem_index", 0)
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
    session_id = state.get("session_id")
    log_with_session(
        logger,
        logging.INFO,
        session_id,
        "moderator_intervene_node: Moderator intervening for premature consensus",
    )

    # Create moderator agent
    moderator = ModeratorAgent()

    # Get facilitator decision for intervention type
    decision = state.get("facilitator_decision")

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

    # Get problem and contributions
    problem = state.get("problem")
    contributions = list(state.get("contributions", []))

    # Build discussion excerpt from recent contributions (last 3)
    recent_contributions = contributions[-3:] if len(contributions) >= 3 else contributions
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
        round_number=state.get("round_number", 1),
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
        "sub_problem_index": state.get("sub_problem_index", 0),  # Preserve sub_problem_index
    }
