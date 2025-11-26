"""LangGraph node implementations for deliberation.

This module contains node functions that wrap existing v1 agents
and integrate them into the LangGraph execution model.
"""

import json
import logging
from dataclasses import asdict
from typing import Any, Literal

from bo1.agents.decomposer import DecomposerAgent
from bo1.agents.facilitator import FacilitatorAgent, FacilitatorDecision
from bo1.agents.selector import PersonaSelectorAgent
from bo1.graph.state import (
    DeliberationGraphState,
    graph_state_to_deliberation_state,
)
from bo1.graph.utils import (
    ensure_metrics,
    track_accumulated_cost,
    track_aggregated_cost,
    track_phase_cost,
)
from bo1.models.problem import SubProblem
from bo1.models.state import DeliberationPhase
from bo1.orchestration.deliberation import DeliberationEngine
from bo1.state.postgres_manager import load_user_context
from bo1.utils.json_parsing import extract_json_with_fallback

logger = logging.getLogger(__name__)


async def decompose_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Decompose problem into sub-problems using DecomposerAgent.

    This node wraps the existing DecomposerAgent and updates the graph state
    with the decomposition results.

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates
    """
    logger.info("decompose_node: Starting problem decomposition")

    # Create decomposer agent
    decomposer = DecomposerAgent()

    # Get problem from state
    problem = state["problem"]

    # Call decomposer
    response = await decomposer.decompose_problem(
        problem_description=problem.description,
        context=problem.context,
        constraints=[],  # TODO: Add constraints from problem model
    )

    # Parse decomposition using utility function
    def create_fallback() -> dict[str, Any]:
        return {
            "analysis": "JSON parsing failed",
            "is_atomic": True,
            "sub_problems": [
                {
                    "id": "sp_001",
                    "goal": problem.description,
                    "context": problem.context,
                    "complexity_score": 5,
                    "dependencies": [],
                }
            ],
        }

    decomposition = extract_json_with_fallback(
        content=response.content,
        fallback_factory=create_fallback,
        logger=logger,
    )

    # Convert sub-problem dicts to SubProblem models
    sub_problems = [
        SubProblem(
            id=sp["id"],
            goal=sp["goal"],
            context=sp.get("context", ""),
            complexity_score=sp["complexity_score"],
            dependencies=sp.get("dependencies", []),
        )
        for sp in decomposition.get("sub_problems", [])
    ]

    # Update problem with sub-problems
    problem.sub_problems = sub_problems

    # Track cost in metrics
    metrics = ensure_metrics(state)
    track_phase_cost(metrics, "problem_decomposition", response)

    logger.info(
        f"decompose_node: Complete - {len(sub_problems)} sub-problems "
        f"(cost: ${response.cost_total:.4f})"
    )

    # Return state updates
    return {
        "problem": problem,
        "current_sub_problem": sub_problems[0] if sub_problems else None,
        "phase": DeliberationPhase.DECOMPOSITION,
        "metrics": metrics,
        "current_node": "decompose",
    }


async def select_personas_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Select expert personas for deliberation using PersonaSelectorAgent.

    This node wraps the existing PersonaSelectorAgent and updates the graph state
    with the selected personas.

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates
    """
    logger.info("select_personas_node: Starting persona selection")

    # Create selector agent
    selector = PersonaSelectorAgent()

    # Get current sub-problem
    current_sp = state["current_sub_problem"]
    if not current_sp:
        raise ValueError("No current sub-problem in state")

    # Call selector
    response = await selector.recommend_personas(
        sub_problem=current_sp,
        problem_context=state["problem"].context,
    )

    # Parse recommendations
    recommendations = json.loads(response.content)
    # Extract persona codes from recommended_personas list
    recommended_personas = recommendations.get("recommended_personas", [])
    persona_codes = [p["code"] for p in recommended_personas]

    logger.info(f"Persona codes: {persona_codes}")

    # Load persona profiles
    from bo1.data import get_persona_by_code
    from bo1.models.persona import PersonaProfile

    personas = []
    for code in persona_codes:
        persona_dict = get_persona_by_code(code)
        if persona_dict:
            # Convert dict to PersonaProfile using Pydantic
            persona = PersonaProfile.model_validate(persona_dict)
            personas.append(persona)
        else:
            logger.warning(f"Persona '{code}' not found, skipping")

    # Track cost in metrics
    metrics = ensure_metrics(state)
    track_phase_cost(metrics, "persona_selection", response)

    logger.info(
        f"select_personas_node: Complete - {len(personas)} personas selected "
        f"(cost: ${response.cost_total:.4f})"
    )

    # Return state updates
    # Include recommendations for display (with rationale for each persona)
    return {
        "personas": personas,
        "persona_recommendations": recommended_personas,  # Save for display
        "phase": DeliberationPhase.SELECTION,
        "metrics": metrics,
        "current_node": "select_personas",
        "sub_problem_index": state.get("sub_problem_index", 0),  # Preserve sub_problem_index
    }


async def initial_round_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Run initial round with parallel persona contributions.

    This node wraps the DeliberationEngine.run_initial_round() method
    and updates the graph state with the contributions.

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates
    """
    logger.info("initial_round_node: Starting initial round")

    # Convert graph state to v1 DeliberationState for engine
    v1_state = graph_state_to_deliberation_state(state)

    # Create deliberation engine
    engine = DeliberationEngine(state=v1_state)

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
    return {
        "contributions": contributions,
        "phase": DeliberationPhase.DISCUSSION,
        "round_number": 1,
        "metrics": metrics,
        "current_node": "initial_round",
        "personas": state.get("personas", []),  # Include for event publishing
        "sub_problem_index": state.get("sub_problem_index", 0),  # Preserve sub_problem_index
    }


async def facilitator_decide_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Make facilitator decision on next action (continue/vote/moderator).

    This node wraps the FacilitatorAgent.decide_next_action() method
    and updates the graph state with the facilitator's decision.

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates
    """
    logger.info("facilitator_decide_node: Making facilitator decision")

    # Convert graph state to v1 DeliberationState for facilitator
    v1_state = graph_state_to_deliberation_state(state)

    # Create facilitator agent
    facilitator = FacilitatorAgent()

    # Get current round number and max rounds
    round_number = state.get("round_number", 1)
    max_rounds = state.get("max_rounds", 6)

    # Call facilitator to decide next action
    decision, llm_response = await facilitator.decide_next_action(
        state=v1_state,
        round_number=round_number,
        max_rounds=max_rounds,
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
                            f"Query: '{research_query[:50]}...' ≈ '{completed.get('query', '')[:50]}...'"
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
    logger.info(
        f"facilitator_decide_node: Complete - action={decision.action}, "
        f"next_speaker={decision.next_speaker if decision.action == 'continue' else 'N/A'}, "
        f"sub_problem_index={sub_problem_index} {cost_msg}"
    )

    # Return state updates with facilitator decision
    # Include round_number so it's available for display
    # Convert dataclass to dict for serializability
    return {
        "facilitator_decision": asdict(decision),
        "round_number": round_number,  # Pass through current round for display
        "phase": DeliberationPhase.DISCUSSION,
        "metrics": metrics,
        "current_node": "facilitator_decide",
        "sub_problem_index": sub_problem_index,  # CRITICAL: Always preserve sub_problem_index (Issue #3 fix)
    }


async def persona_contribute_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Single persona contributes in a multi-round deliberation.

    This node is called when the facilitator decides to continue the deliberation
    with a specific persona speaking. It:
    1. Extracts the speaker from the facilitator decision
    2. Gets the persona profile
    3. Calls the persona to contribute
    4. Adds the contribution to state
    5. Increments round number
    6. Tracks cost

    Args:
        state: Current graph state (must have facilitator_decision)

    Returns:
        Dictionary with state updates (new contribution, incremented round)
    """
    from bo1.models.state import ContributionType
    from bo1.orchestration.deliberation import DeliberationEngine

    logger.info("persona_contribute_node: Processing persona contribution")

    # Get facilitator decision (must exist)
    decision = state.get("facilitator_decision")
    if not decision:
        raise ValueError("persona_contribute_node called without facilitator_decision in state")

    # Extract speaker from decision (correct field name is 'next_speaker')
    speaker_code = decision.get("next_speaker")
    if not speaker_code:
        raise ValueError("Facilitator decision missing next_speaker for 'continue' action")

    logger.info(f"persona_contribute_node: Speaker={speaker_code}")

    # Get persona profile
    personas = state.get("personas", [])
    persona = next((p for p in personas if p.code == speaker_code), None)
    if not persona:
        raise ValueError(f"Persona {speaker_code} not found in selected personas")

    # Get problem and contribution context
    problem = state.get("problem")
    contributions = list(state.get("contributions", []))
    round_number = state.get("round_number", 1)

    # Build participant list
    participant_list = ", ".join([p.name for p in personas])

    # Check if expert has memory from previous sub-problems
    expert_memory: str | None = None
    sub_problem_results = state.get("sub_problem_results", [])

    if sub_problem_results:
        # Collect memory from all previous sub-problems where this expert contributed
        memory_parts = []
        for result in sub_problem_results:
            if speaker_code in result.expert_summaries:
                prev_summary = result.expert_summaries[speaker_code]
                prev_goal = result.sub_problem_goal
                memory_parts.append(f"Sub-problem: {prev_goal}\nYour position: {prev_summary}")

        if memory_parts:
            expert_memory = "\n\n".join(memory_parts)
            logger.info(
                f"{persona.display_name} has memory from {len(memory_parts)} previous sub-problem(s)"
            )

    # Create deliberation engine (constructor takes state argument)
    v1_state = graph_state_to_deliberation_state(state)
    engine = DeliberationEngine(state=v1_state)

    # Call persona with correct signature (including expert_memory)
    contribution_msg, llm_response = await engine._call_persona_async(
        persona_profile=persona,
        problem_statement=problem.description if problem else "",
        problem_context=problem.context if problem else "",
        participant_list=participant_list,
        round_number=round_number,
        contribution_type=ContributionType.RESPONSE,
        previous_contributions=contributions,
        expert_memory=expert_memory,
    )

    # Track cost in metrics
    metrics = ensure_metrics(state)
    phase_key = f"round_{round_number}_deliberation"
    track_accumulated_cost(metrics, phase_key, llm_response)

    # NEW: Drift detection
    from bo1.graph.quality_metrics import detect_contribution_drift

    contribution_text = contribution_msg.content
    problem_statement = problem.description if problem else ""

    if detect_contribution_drift(contribution_text, problem_statement):
        # Increment drift counter
        if not hasattr(metrics, "drift_events"):
            metrics.drift_events = 0
        metrics.drift_events += 1
        logger.warning(f"Drift detected in contribution from {speaker_code}")

    # Add new contribution to state
    contributions.append(contribution_msg)

    # Increment round number for next round
    next_round = round_number + 1

    # Trigger summarization for completed round
    round_summaries = list(state.get("round_summaries", []))

    if round_number > 0:  # Don't summarize round 0
        # Get all contributions from the just-completed round
        round_contributions = [
            {"persona": c.persona_name, "content": c.content}
            for c in contributions
            if c.round_number == round_number
        ]

        if round_contributions:  # Only summarize if there were contributions
            from bo1.agents.summarizer import SummarizerAgent

            summarizer = SummarizerAgent()
            # Reuse problem from earlier in the function
            summary_problem_stmt = problem.description if problem else None

            try:
                summary_response = await summarizer.summarize_round(
                    round_number=round_number,
                    contributions=round_contributions,
                    problem_statement=summary_problem_stmt,
                )

                round_summaries.append(summary_response.content)
                track_accumulated_cost(metrics, "summarization", summary_response)

                logger.info(
                    f"Round {round_number} summarized: {summary_response.token_usage.output_tokens} tokens"
                )
            except Exception as e:
                logger.warning(f"Failed to summarize round {round_number}: {e}")
                # Add minimal fallback summary to preserve hierarchical mode
                expert_names = ", ".join([c.get("persona", "Unknown") for c in round_contributions])
                fallback_summary = (
                    f"Round {round_number}: {len(round_contributions)} contributions from {expert_names}. "
                    f"(Detailed summary unavailable)"
                )
                round_summaries.append(fallback_summary)
                logger.info(f"Added fallback summary for round {round_number}")

    logger.info(
        f"persona_contribute_node: Complete - {speaker_code} contributed "
        f"(round {round_number} → {next_round}, cost: ${llm_response.cost_total:.4f})"
    )

    # Return state updates
    return {
        "contributions": contributions,
        "round_number": next_round,
        "round_summaries": round_summaries,
        "metrics": metrics,
        "current_node": "persona_contribute",
        "sub_problem_index": state.get("sub_problem_index", 0),  # Preserve sub_problem_index
    }


async def moderator_intervene_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Moderator intervenes to redirect conversation.

    This node is called when the facilitator detects the conversation has
    drifted off-topic or needs moderation. It:
    1. Calls the ModeratorAgent to intervene
    2. Adds the intervention as a contribution
    3. Tracks cost
    4. Returns updated state

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates (intervention contribution added)
    """
    from bo1.agents.moderator import ModeratorAgent
    from bo1.models.contribution import ContributionMessage, ContributionType

    logger.info("moderator_intervene_node: Moderator intervening")

    # Create moderator agent
    moderator = ModeratorAgent()

    # Get facilitator decision for intervention type
    decision = state.get("facilitator_decision")

    # Extract moderator type with proper type handling
    from typing import Literal

    moderator_type_value = decision.get("moderator_type") if decision else None
    if moderator_type_value and isinstance(moderator_type_value, str):
        # Validate it's one of the allowed types
        if moderator_type_value in ("contrarian", "skeptic", "optimist"):
            moderator_type: Literal["contrarian", "skeptic", "optimist"] = moderator_type_value
        else:
            moderator_type = "contrarian"
    else:
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
        else "conversation drift detected"
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

    logger.info(
        f"moderator_intervene_node: Complete - {moderator_type} intervention "
        f"(cost: ${llm_response.cost_total:.4f})"
    )

    # Return state updates
    return {
        "contributions": contributions,
        "metrics": metrics,
        "current_node": "moderator_intervene",
        "sub_problem_index": state.get("sub_problem_index", 0),  # Preserve sub_problem_index
    }


async def research_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Execute external research requested by facilitator.

    Flow:
    1. Extract research query from facilitator decision
    2. Check semantic cache (PostgreSQL + Voyage embeddings)
    3. If cache miss: Brave Search (default) or Tavily (premium) + summarization
    4. Add research to deliberation context
    5. Continue to next round with enriched context

    Research Strategy:
    - Default: Brave Search + Haiku (~$0.025/query) for facts/statistics
    - Premium: Tavily ($0.001/query) for competitor/market/regulatory analysis

    Args:
        state: Current graph state

    Returns:
        State updates with research results
    """
    from bo1.agents.researcher import ResearcherAgent

    # Extract research query from facilitator decision
    facilitator_decision = state.get("facilitator_decision")

    if not facilitator_decision:
        logger.warning(
            "[RESEARCH] No facilitator decision found - marking as completed to prevent loop"
        )
        # Even without a decision, mark a placeholder to prevent re-triggering
        from bo1.llm.embeddings import generate_embedding

        # Use recent contributions to create a generic query marker
        recent_contributions = state.get("contributions", [])[-3:]
        fallback_query = "Research pattern detected but no specific query provided"
        if recent_contributions:
            # Use last contribution content as query marker
            fallback_query = f"Research needed based on: {recent_contributions[-1].content[:100]}"

        # Generate embedding for this fallback
        try:
            fallback_embedding = generate_embedding(fallback_query, input_type="query")
        except Exception as e:
            logger.warning(f"Failed to generate embedding for fallback query: {e}")
            fallback_embedding = []

        # Mark as completed to prevent infinite loop
        completed_queries_obj = state.get("completed_research_queries", [])
        completed_queries = (
            list(completed_queries_obj) if isinstance(completed_queries_obj, list) else []
        )
        completed_queries.append(
            {
                "query": fallback_query,
                "embedding": fallback_embedding,
            }
        )

        return {
            "completed_research_queries": completed_queries,
            "facilitator_decision": None,
            "current_node": "research",
        }

    decision_reasoning = facilitator_decision.get("reasoning", "")

    if not decision_reasoning:
        logger.warning("[RESEARCH] Facilitator decision has no reasoning - using fallback")
        decision_reasoning = "General research requested"

    # Use the facilitator's reasoning as the research query
    research_query = f"Research needed: {decision_reasoning[:200]}"

    logger.info(f"[RESEARCH] Query extracted: {research_query[:80]}...")

    # Determine research depth based on keywords in reasoning
    deep_keywords = ["competitor", "market", "landscape", "regulation", "policy", "analysis"]
    research_depth: Literal["basic", "deep"] = (
        "deep"
        if any(keyword in decision_reasoning.lower() for keyword in deep_keywords)
        else "basic"
    )

    logger.info(f"[RESEARCH] Depth: {research_depth}")

    # P1-RESEARCH-2: Early cache check for cross-session deduplication
    # Check if similar research exists in cache before calling ResearcherAgent
    from bo1.llm.embeddings import generate_embedding
    from bo1.state.postgres_manager import find_similar_research

    try:
        query_embedding = generate_embedding(research_query, input_type="query")
        cached_results = find_similar_research(
            question_embedding=query_embedding,
            similarity_threshold=0.85,  # Same threshold as in-session dedup
            limit=1,
        )
        if cached_results:
            logger.info(
                f"[RESEARCH] Found similar cached research (similarity={cached_results[0].get('similarity', 0):.3f}). "
                f"ResearcherAgent will use this cached result."
            )
    except Exception as e:
        logger.debug(f"[RESEARCH] Cache pre-check failed (non-critical): {e}")

    # Perform research (uses cache if available)
    researcher = ResearcherAgent()
    results = await researcher.research_questions(
        questions=[
            {
                "question": research_query,
                "priority": "CRITICAL",  # Facilitator-requested = always critical
            }
        ],
        category="general",
        research_depth=research_depth,
    )

    if not results:
        logger.warning("[RESEARCH] No results returned")
        return {"current_node": "research"}

    result = results[0]

    # Add to state context
    research_results_obj = state.get("research_results", [])
    # Ensure it's a list before appending
    if isinstance(research_results_obj, list):
        research_results = research_results_obj
    else:
        research_results = []

    research_results.append(
        {
            "query": research_query,
            "summary": result["summary"],
            "sources": result.get("sources", []),
            "cached": result.get("cached", False),
            "cost": result.get("cost", 0.0),
            "round": state.get("round_number", 0),
            "depth": research_depth,
        }
    )

    logger.info(
        f"[RESEARCH] Complete - Cached: {result.get('cached', False)}, "
        f"Depth: {research_depth}, Cost: ${result.get('cost', 0):.4f}"
    )

    # Mark this research query as completed to prevent infinite loops
    # Store query with embedding for semantic similarity matching
    from bo1.llm.embeddings import generate_embedding

    completed_queries_obj = state.get("completed_research_queries", [])
    completed_queries = (
        list(completed_queries_obj) if isinstance(completed_queries_obj, list) else []
    )

    # Generate embedding for this query (or extract from facilitator decision if available)
    try:
        query_embedding = generate_embedding(research_query, input_type="query")
    except Exception as e:
        logger.warning(f"Failed to generate embedding for research query: {e}")
        query_embedding = []  # Empty embedding for fallback

    # Check if this exact query already exists (avoid duplicates)
    query_exists = any(q.get("query") == research_query for q in completed_queries)

    if not query_exists:
        completed_queries.append(
            {
                "query": research_query,
                "embedding": query_embedding,
            }
        )
        logger.debug(f"Marked research query as completed: '{research_query[:50]}...'")

    return {
        "research_results": research_results,
        "completed_research_queries": completed_queries,  # Track completed research
        "facilitator_decision": None,  # Clear previous decision to prevent loops
        "current_node": "research",
        "sub_problem_index": state.get("sub_problem_index", 0),
    }


async def vote_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Collect recommendations from all personas.

    This node wraps the collect_recommendations() function from voting.py
    and updates the graph state with the collected recommendations.

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates (recommendations, metrics)
    """
    from bo1.llm.broker import PromptBroker
    from bo1.orchestration.voting import collect_recommendations

    logger.info("vote_node: Starting recommendation collection phase")

    # Convert graph state to v1 DeliberationState
    v1_state = graph_state_to_deliberation_state(state)

    # Create broker for LLM calls
    broker = PromptBroker()

    # Collect recommendations from all personas
    recommendations, llm_responses = await collect_recommendations(state=v1_state, broker=broker)

    # Track cost in metrics
    metrics = ensure_metrics(state)
    track_aggregated_cost(metrics, "voting", llm_responses)

    rec_cost = sum(r.cost_total for r in llm_responses)

    logger.info(
        f"vote_node: Complete - {len(recommendations)} recommendations collected (cost: ${rec_cost:.4f})"
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
    return {
        "votes": recommendations_dicts,
        "recommendations": recommendations_dicts,
        "phase": DeliberationPhase.VOTING,
        "metrics": metrics,
        "current_node": "vote",
        "sub_problem_index": state.get("sub_problem_index", 0),  # Preserve sub_problem_index
    }


async def synthesize_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Synthesize final recommendation from deliberation.

    This node creates a comprehensive synthesis report using the
    SYNTHESIS_PROMPT_TEMPLATE and updates the graph state.

    Args:
        state: Current graph state (must have votes and contributions)

    Returns:
        Dictionary with state updates (synthesis report, phase=COMPLETE)
    """
    from bo1.llm.broker import PromptBroker, PromptRequest
    from bo1.prompts.reusable_prompts import SYNTHESIS_PROMPT_TEMPLATE

    logger.info("synthesize_node: Starting synthesis")

    # Get problem and contributions
    problem = state.get("problem")
    contributions = state.get("contributions", [])
    votes = state.get("votes", [])

    if not problem:
        raise ValueError("synthesize_node called without problem in state")

    # Format all contributions and votes for synthesis
    all_contributions_and_votes = []

    # Add discussion history
    all_contributions_and_votes.append("=== DISCUSSION ===\n")
    for contrib in contributions:
        all_contributions_and_votes.append(
            f"Round {contrib.round_number} - {contrib.persona_name}:\n{contrib.content}\n"
        )

    # Add votes
    all_contributions_and_votes.append("\n=== RECOMMENDATIONS ===\n")
    for vote in votes:
        all_contributions_and_votes.append(
            f"{vote['persona_name']}: {vote['recommendation']} "
            f"(confidence: {vote['confidence']:.2f})\n"
            f"Reasoning: {vote['reasoning']}\n"
        )
        if vote.get("conditions"):
            all_contributions_and_votes.append(f"Conditions: {', '.join(vote['conditions'])}\n")
        all_contributions_and_votes.append("\n")

    full_context = "".join(all_contributions_and_votes)

    # Compose synthesis prompt
    synthesis_prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
        problem_statement=problem.description,
        all_contributions_and_votes=full_context,
    )

    # Create broker and request
    broker = PromptBroker()
    request = PromptRequest(
        system=synthesis_prompt,
        user_message="Generate the synthesis report now.",
        prefill="<thinking>",
        model="sonnet",  # Use Sonnet for high-quality synthesis
        temperature=0.7,
        max_tokens=3000,
        phase="synthesis",
        agent_type="synthesizer",
    )

    # Call LLM
    response = await broker.call(request)

    # Prepend prefill for complete content
    synthesis_report = "<thinking>" + response.content

    # Add AI-generated content disclaimer
    disclaimer = (
        "\n\n---\n\n"
        "⚠️ This content is AI-generated for learning and knowledge purposes only, "
        "not professional advisory.\n\n"
        "Always verify recommendations using licensed legal/financial professionals "
        "for your location."
    )
    synthesis_report_with_disclaimer = synthesis_report + disclaimer

    # Track cost in metrics
    metrics = ensure_metrics(state)
    track_phase_cost(metrics, "synthesis", response)

    logger.info(
        f"synthesize_node: Complete - synthesis generated (cost: ${response.cost_total:.4f})"
    )

    # Return state updates
    return {
        "synthesis": synthesis_report_with_disclaimer,
        "phase": DeliberationPhase.SYNTHESIS,  # Don't set COMPLETE yet - may have more sub-problems
        "metrics": metrics,
        "current_node": "synthesize",
        "sub_problem_index": state.get("sub_problem_index", 0),  # Preserve sub_problem_index
    }


async def next_subproblem_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Move to next sub-problem after synthesis.

    This node:
    1. Saves the current sub-problem result (synthesis, votes, costs)
    2. Generates per-expert summaries for memory
    3. Increments sub_problem_index
    4. If more sub-problems: resets deliberation state and sets next sub-problem
    5. If all complete: triggers meta-synthesis by setting current_sub_problem=None

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates
    """
    from bo1.agents.summarizer import SummarizerAgent
    from bo1.models.state import SubProblemResult

    # Extract current sub-problem data
    current_sp = state.get("current_sub_problem")
    problem = state.get("problem")
    contributions = state.get("contributions", [])
    votes = state.get("votes", [])
    personas = state.get("personas", [])
    synthesis = state.get("synthesis", "")
    metrics = state.get("metrics")
    sub_problem_index = state.get("sub_problem_index", 0)

    # Enhanced logging for sub-problem progression (Bug #3 fix)
    total_sub_problems = len(problem.sub_problems) if problem else 0
    logger.info(
        f"next_subproblem_node: Saving result for sub-problem {sub_problem_index + 1}/{total_sub_problems}: "
        f"{current_sp.goal if current_sp else 'unknown'}"
    )

    if not current_sp:
        raise ValueError("next_subproblem_node called without current_sub_problem")

    if not problem:
        raise ValueError("next_subproblem_node called without problem")

    # Calculate cost for this sub-problem (all phase costs accumulated)
    # For simplicity, use total_cost - sum of previous sub-problem costs
    total_cost_so_far = metrics.total_cost if metrics else 0.0
    previous_results = state.get("sub_problem_results", [])
    previous_cost = sum(r.cost for r in previous_results)
    sub_problem_cost = total_cost_so_far - previous_cost

    # Track duration (placeholder - could enhance with actual timing)
    duration_seconds = 0.0

    # Generate per-expert summaries for memory (if there are contributions)
    expert_summaries: dict[str, str] = {}

    if contributions:
        summarizer = SummarizerAgent()

        for persona in personas:
            # Get contributions from this expert
            expert_contributions = [c for c in contributions if c.persona_code == persona.code]

            if expert_contributions:
                try:
                    # Convert contributions to dict format for summarizer
                    contribution_dicts = [
                        {"persona": c.persona_name, "content": c.content}
                        for c in expert_contributions
                    ]

                    # Summarize expert's contributions
                    response = await summarizer.summarize_round(
                        round_number=state.get("round_number", 1),
                        contributions=contribution_dicts,
                        problem_statement=current_sp.goal,
                        target_tokens=75,  # Concise summary for memory
                    )

                    expert_summaries[persona.code] = response.content

                    # Track cost
                    if metrics:
                        phase_costs = metrics.phase_costs
                        phase_costs["expert_memory"] = (
                            phase_costs.get("expert_memory", 0.0) + response.cost_total
                        )

                    logger.info(
                        f"Generated memory summary for {persona.display_name}: "
                        f"{response.token_usage.output_tokens} tokens, ${response.cost_total:.6f}"
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to generate summary for {persona.display_name}: {e}. "
                        f"Expert will not have memory for next sub-problem."
                    )

    # Create SubProblemResult
    result = SubProblemResult(
        sub_problem_id=current_sp.id,
        sub_problem_goal=current_sp.goal,
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

    # Increment index
    next_index = sub_problem_index + 1

    # Check if more sub-problems
    if next_index < len(problem.sub_problems):
        next_sp = problem.sub_problems[next_index]

        logger.info(
            f"Moving to sub-problem {next_index + 1}/{len(problem.sub_problems)}: {next_sp.goal}"
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
        # All complete → meta-synthesis
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
    from bo1.prompts.reusable_prompts import META_SYNTHESIS_ACTION_PLAN_PROMPT

    logger.info("meta_synthesize_node: Starting meta-synthesis (structured JSON)")

    # Get problem and sub-problem results
    problem = state.get("problem")
    sub_problem_results = state.get("sub_problem_results", [])

    if not problem:
        raise ValueError("meta_synthesize_node called without problem")

    if not sub_problem_results:
        raise ValueError("meta_synthesize_node called without sub_problem_results")

    # Format all sub-problem syntheses
    formatted_results = []
    total_cost = 0.0
    total_duration = 0.0

    for i, result in enumerate(sub_problem_results, 1):
        # Find the sub-problem by ID
        sp = next((sp for sp in problem.sub_problems if sp.id == result.sub_problem_id), None)
        sp_goal = sp.goal if sp else result.sub_problem_goal

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
        original_problem=problem.description,
        problem_context=problem.context or "No additional context provided",
        sub_problem_count=len(sub_problem_results),
        all_sub_problem_syntheses="\n\n---\n\n".join(formatted_results),
    )

    # Create broker and request
    broker = PromptBroker()
    request = PromptRequest(
        system=meta_prompt,
        user_message="Generate the JSON action plan now (pure JSON, no markdown):",
        prefill="<action_plan>\n{",  # Force JSON output with proper XML wrapping
        model="sonnet",  # Use Sonnet for high-quality meta-synthesis
        temperature=0.7,
        max_tokens=4000,
        phase="meta_synthesis",
        agent_type="meta_synthesizer",
    )

    # Call LLM
    response = await broker.call(request)

    # Prepend prefill to get complete JSON (including opening brace)
    json_content = "{" + response.content

    # Parse and validate JSON
    try:
        import json

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

- **Original problem**: {problem.description}
- **Sub-problems deliberated**: {len(sub_problem_results)}
- **Total contributions**: {sum(r.contribution_count for r in sub_problem_results)}
- **Total cost**: ${total_cost:.4f}
- **Meta-synthesis cost**: ${response.cost_total:.4f}
- **Grand total cost**: ${total_cost + response.cost_total:.4f}

⚠️ This content is AI-generated for learning and knowledge purposes only, not professional advisory.
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
    return {
        "synthesis": meta_synthesis_final,
        "phase": DeliberationPhase.COMPLETE,
        "metrics": metrics,
        "current_node": "meta_synthesis",
    }


async def context_collection_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Collect business context and information gaps before deliberation.

    This node:
    1. Loads saved business context (if user_id exists)
    2. Injects context into problem.context dictionary
    3. Tracks cost in metrics.phase_costs["context_collection"] (data loading = $0)

    Note: Full context collection (prompts, information gaps, research) will be
    implemented in future iterations. Currently just loads saved context.

    Args:
        state: Current graph state (must have problem)

    Returns:
        Dictionary with state updates (problem with enriched context)
    """
    logger.info("context_collection_node: Starting context collection")

    problem = state.get("problem")
    if not problem:
        raise ValueError("context_collection_node called without problem")

    # Get user_id from state (optional)
    user_id = state.get("user_id")

    # Initialize metrics
    metrics = ensure_metrics(state)

    # Step 1: Load saved business context
    business_context = None
    if user_id:
        logger.info(f"Loading saved business context for user_id: {user_id}")
        try:
            saved_context = load_user_context(user_id)
            if saved_context:
                logger.info("Found saved business context")
                business_context = saved_context

                # Inject business context into problem.context (append to string)
                # Format business context as a readable addition
                context_lines = [
                    "\n\n## Business Context",
                ]
                if saved_context.get("business_model"):
                    context_lines.append(f"- Business Model: {saved_context['business_model']}")
                if saved_context.get("target_market"):
                    context_lines.append(f"- Target Market: {saved_context['target_market']}")
                if saved_context.get("revenue"):
                    context_lines.append(f"- Revenue: {saved_context['revenue']}")
                if saved_context.get("customers"):
                    context_lines.append(f"- Customers: {saved_context['customers']}")
                if saved_context.get("growth_rate"):
                    context_lines.append(f"- Growth Rate: {saved_context['growth_rate']}")

                # Append to existing context
                problem.context = problem.context + "\n".join(context_lines)
                logger.info("Injected business context into problem.context")
        except Exception as e:
            logger.warning(f"Failed to load business context: {e}")

    # Track cost in metrics (data loading = $0, no LLM calls)
    track_phase_cost(metrics, "context_collection", None)

    logger.info("context_collection_node: Complete")

    return {
        "problem": problem,
        "business_context": business_context,
        "metrics": metrics,
        "current_node": "context_collection",
    }


async def clarification_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Handle clarification questions from facilitator during deliberation.

    This node:
    1. Displays clarification question from facilitator
    2. Provides options: Answer now / Pause session / Skip
    3. If answer: Injects into context, continues
    4. If pause: Sets should_stop=True, saves pending_clarification
    5. If skip: Logs skip, continues with warning

    Args:
        state: Current graph state (must have pending_clarification)

    Returns:
        Dictionary with state updates (context with answer, or paused state)
    """
    logger.info("clarification_node: Handling clarification request")

    pending_clarification = state.get("pending_clarification")

    if not pending_clarification:
        logger.warning("clarification_node called without pending_clarification")
        return {
            "current_node": "clarification",
        }

    # For now, we'll implement a simple console-based clarification prompt
    # Full implementation will include web API support for async clarification

    from bo1.ui.console import Console

    console = Console()

    question = pending_clarification.get("question", "Unknown question")
    reason = pending_clarification.get("reason", "")

    console.print("\n[bold yellow]Clarification Needed[/bold yellow]")
    console.print(f"Question: {question}")
    if reason:
        console.print(f"Reason: {reason}")

    console.print("\nOptions:")
    console.print("1. Answer now")
    console.print("2. Pause session (resume later)")
    console.print("3. Skip question")

    choice = console.input("\nYour choice (1-3): ").strip()

    if choice == "1":
        # Collect answer
        answer = console.input("\nYour answer: ").strip()

        # Store answer in pending_clarification for later injection
        answered_clarification = pending_clarification.copy()
        answered_clarification["answer"] = answer
        answered_clarification["answered"] = True

        logger.info(f"Clarification answered: {question[:50]}...")

        # Update business_context with clarification
        business_context = state.get("business_context") or {}
        if not isinstance(business_context, dict):
            business_context = {}
        clarifications = business_context.get("clarifications", {})
        clarifications[question] = answer
        business_context["clarifications"] = clarifications

        return {
            "business_context": business_context,
            "pending_clarification": None,
            "current_node": "clarification",
        }

    elif choice == "2":
        # Pause session
        logger.info("User requested session pause for clarification")

        return {
            "should_stop": True,
            "pending_clarification": pending_clarification,
            "current_node": "clarification",
        }

    else:
        # Skip question
        logger.info(f"User skipped clarification: {question[:50]}...")

        return {
            "pending_clarification": None,
            "current_node": "clarification",
        }


# ============================================================================
# NEW PARALLEL ARCHITECTURE - Multi-Expert Round Node (Day 38)
# ============================================================================


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

    logger.info(
        f"parallel_round_node: Complete - Round {round_number} → {next_round}, "
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
        "sub_problem_index": state.get("sub_problem_index", 0),
    }


def _determine_phase(round_number: int, max_rounds: int) -> str:
    """Determine deliberation phase based on round number.

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
    # Calculate phase boundaries (thirds)
    exploration_end = max(2, max_rounds // 3)
    challenge_end = max(4, 2 * max_rounds // 3)

    if round_number <= exploration_end:
        return "exploration"
    elif round_number <= challenge_end:
        return "challenge"
    else:
        return "convergence"


async def _select_experts_for_round(
    state: DeliberationGraphState,
    phase: str,
    round_number: int,
) -> list[Any]:  # Returns list[PersonaProfile]
    """Select 2-5 experts for this round based on phase and balance.

    Selection Strategy:
    - Exploration: 3-5 experts (broad exploration, prioritize unheard voices)
    - Challenge: 2-3 experts (focused debate, avoid recent speakers)
    - Convergence: 2-3 experts (synthesis, balanced representation)

    Balancing Rules:
    - No expert in >50% of recent 4 rounds
    - Each expert 15-25% of total contributions (balanced)

    Args:
        state: Current deliberation state
        phase: "exploration", "challenge", or "convergence"
        round_number: Current round number

    Returns:
        List of selected PersonaProfile objects
    """
    personas = state.get("personas", [])
    contributions = state.get("contributions", [])
    experts_per_round = state.get("experts_per_round", [])

    if not personas:
        logger.warning("No personas available for selection")
        return []

    # Count contributions per expert
    contribution_counts: dict[str, int] = {}
    for contrib in contributions:
        contribution_counts[contrib.persona_code] = (
            contribution_counts.get(contrib.persona_code, 0) + 1
        )

    # Get recent speakers (last 4 rounds)
    recent_speakers: list[str] = []
    if experts_per_round:
        for round_experts in experts_per_round[-4:]:
            recent_speakers.extend(round_experts)

    # Phase-specific selection
    if phase == "exploration":
        # Select 3-4 experts, prioritize those who haven't spoken much
        target_count = min(4, len(personas))

        # Sort by contribution count (fewest first)
        candidates = sorted(
            personas,
            key=lambda p: (
                contribution_counts.get(p.code, 0),  # Fewest contributions first
                p.code,  # Stable sort by code
            ),
        )

        selected = candidates[:target_count]

    elif phase == "challenge":
        # Select 2-3 experts who haven't spoken recently
        target_count = min(3, len(personas))

        # Filter out recent speakers
        candidates = [
            p
            for p in personas
            if recent_speakers.count(p.code) < 2  # Not in last 2 rounds
        ]

        if not candidates:
            # All experts spoke recently, just use all
            candidates = list(personas)

        # Sort by contribution count (fewest first)
        candidates = sorted(candidates, key=lambda p: contribution_counts.get(p.code, 0))

        selected = candidates[:target_count]

    elif phase == "convergence":
        # Select 2-3 experts representing different viewpoints
        target_count = min(3, len(personas))

        # Select balanced set (least-contributing experts to ensure all voices heard)
        selected = sorted(personas, key=lambda p: contribution_counts.get(p.code, 0))[:target_count]

    else:
        # Default: select first 3
        selected = personas[: min(3, len(personas))]

    logger.info(
        f"Expert selection ({phase}): {[p.code for p in selected]} "
        f"(target: {target_count if 'target_count' in locals() else 'N/A'})"
    )

    return selected


async def _generate_parallel_contributions(
    experts: list[Any],  # list[PersonaProfile]
    state: DeliberationGraphState,
    phase: str,
    round_number: int,
) -> list[Any]:  # Returns list[ContributionMessage]
    """Generate contributions from multiple experts in parallel.

    Uses asyncio.gather to call all experts concurrently, reducing
    total round time from serial (n × LLM_latency) to parallel (1 × LLM_latency).

    Args:
        experts: List of PersonaProfile objects
        state: Current deliberation state
        phase: "exploration", "challenge", or "convergence"
        round_number: Current round number

    Returns:
        List of ContributionMessage objects
    """
    import asyncio

    from bo1.models.state import ContributionType
    from bo1.orchestration.deliberation import DeliberationEngine

    # Convert graph state to v1 for engine
    v1_state = graph_state_to_deliberation_state(state)
    engine = DeliberationEngine(state=v1_state)

    # Get problem context
    problem = state.get("problem")
    contributions = state.get("contributions", [])
    personas = state.get("personas", [])

    participant_list = ", ".join([p.name for p in personas])

    # Get phase-specific speaker prompt
    speaker_prompt = _get_phase_prompt(phase, round_number)

    # Create tasks for all experts
    # NOTE: speaker_prompt is stored in expert_memory for now (until _call_persona_async is updated)
    tasks = []
    for expert in experts:
        # Use expert_memory to pass phase-specific guidance
        phase_guidance = f"Phase Guidance: {speaker_prompt}"

        task = engine._call_persona_async(
            persona_profile=expert,
            problem_statement=problem.description if problem else "",
            problem_context=problem.context if problem else "",
            participant_list=participant_list,
            round_number=round_number,
            contribution_type=ContributionType.RESPONSE,
            previous_contributions=contributions,
            expert_memory=phase_guidance,  # Pass phase prompt via memory field
        )
        tasks.append(task)

    # Run all in parallel
    results = await asyncio.gather(*tasks)

    # Extract contributions and track costs
    contribution_msgs = []
    metrics = ensure_metrics(state)

    for contribution_msg, llm_response in results:
        contribution_msgs.append(contribution_msg)

        # Track cost
        phase_key = f"round_{round_number}_parallel_deliberation"
        track_accumulated_cost(metrics, phase_key, llm_response)

    total_cost = sum(r[1].cost_total for r in results)
    logger.info(
        f"Parallel contributions: {len(contribution_msgs)} experts, cost: ${total_cost:.4f}"
    )

    return contribution_msgs


def _get_phase_prompt(phase: str, round_number: int) -> str:
    """Get phase-specific speaker prompts.

    From MEETING_SYSTEM_ANALYSIS.md, these prompts enforce:
    - 80-token max (prevents rambling)
    - Explicit phase objectives
    - No generic agreement without new information

    Args:
        phase: "exploration", "challenge", or "convergence"
        round_number: Current round number

    Returns:
        Speaker prompt string
    """
    if phase == "exploration":
        return (
            "EXPLORATION PHASE: Surface new perspectives, risks, and opportunities. "
            "Challenge assumptions. Identify gaps in analysis. "
            "Max 80 tokens. No agreement statements without new information."
        )

    elif phase == "challenge":
        return (
            "CHALLENGE PHASE: Directly challenge a previous point OR provide new evidence. "
            "Must either disagree with a specific claim or add novel data. "
            "Max 80 tokens. No summaries or meta-commentary."
        )

    elif phase == "convergence":
        return (
            "CONVERGENCE PHASE: Provide your strongest recommendation, key risk, and "
            "reason it outweighs alternatives. Be specific. "
            "Max 80 tokens. No further debate."
        )

    else:
        return "Provide your contribution based on your expertise."
