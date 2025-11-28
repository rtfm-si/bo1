"""LangGraph node implementations for deliberation.

This module contains node functions that wrap existing v1 agents
and integrate them into the LangGraph execution model.
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict
from typing import Any, Literal

from anthropic import APIConnectionError, APITimeoutError

from bo1.agents.decomposer import DecomposerAgent
from bo1.agents.facilitator import FacilitatorAgent, FacilitatorDecision
from bo1.agents.selector import PersonaSelectorAgent
from bo1.graph.state import DeliberationGraphState
from bo1.graph.utils import (
    ensure_metrics,
    track_accumulated_cost,
    track_aggregated_cost,
    track_phase_cost,
)
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import DeliberationPhase, SubProblemResult
from bo1.orchestration.deliberation import DeliberationEngine
from bo1.state.postgres_manager import load_user_context
from bo1.utils.json_parsing import extract_json_with_fallback

logger = logging.getLogger(__name__)


async def retry_with_backoff(
    func: Any,
    *args: Any,
    max_retries: int = 3,
    initial_delay: float = 2.0,
    backoff_factor: float = 2.0,
    **kwargs: Any,
) -> Any:
    """Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Positional arguments to pass to func
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds before first retry (default: 2.0)
        backoff_factor: Multiplier for delay on each retry (default: 2.0)
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result from successful function call

    Raises:
        The last exception if all retries fail

    Example:
        >>> result = await retry_with_backoff(_deliberate_subproblem, sub_problem, problem, ...)
        # Tries up to 3 times with delays: 2s, 4s, 8s
    """
    last_exception = None
    delay = initial_delay

    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            return await func(*args, **kwargs)
        except (TimeoutError, APITimeoutError, APIConnectionError) as e:
            last_exception = e

            if attempt < max_retries:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed with {type(e).__name__}: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(
                    f"All {max_retries + 1} attempts failed for {func.__name__}. Last error: {e}"
                )
                raise
        except Exception as e:
            # Don't retry on non-timeout errors (e.g., validation errors, logic errors)
            logger.error(f"Non-retryable error in {func.__name__}: {type(e).__name__}: {e}")
            raise

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception


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

    # Assess complexity to determine adaptive parameters
    from bo1.agents.complexity_assessor import ComplexityAssessor, validate_complexity_assessment

    assessor = ComplexityAssessor()
    complexity_response = await assessor.assess_complexity(
        problem_description=problem.description,
        context=problem.context,
        sub_problems=[
            {"id": sp.id, "goal": sp.goal, "complexity_score": sp.complexity_score}
            for sp in sub_problems
        ],
    )

    # Parse complexity assessment
    def create_complexity_fallback() -> dict[str, Any]:
        # Default to moderate complexity if assessment fails
        return {
            "scope_breadth": 0.4,
            "dependencies": 0.4,
            "ambiguity": 0.4,
            "stakeholders": 0.3,
            "novelty": 0.3,
            "overall_complexity": 0.38,
            "recommended_rounds": 4,
            "recommended_experts": 4,
            "reasoning": "Complexity assessment failed, using moderate defaults",
        }

    complexity_assessment = extract_json_with_fallback(
        content=complexity_response.content,
        fallback_factory=create_complexity_fallback,
        logger=logger,
    )

    # Validate and sanitize complexity scores
    complexity_assessment = validate_complexity_assessment(complexity_assessment)

    # Update metrics with complexity scores
    metrics.complexity_score = complexity_assessment.get("overall_complexity", 0.4)
    metrics.scope_breadth = complexity_assessment.get("scope_breadth", 0.4)
    metrics.dependencies = complexity_assessment.get("dependencies", 0.4)
    metrics.ambiguity = complexity_assessment.get("ambiguity", 0.4)
    metrics.stakeholders_complexity = complexity_assessment.get("stakeholders", 0.3)
    metrics.novelty = complexity_assessment.get("novelty", 0.3)
    metrics.recommended_rounds = complexity_assessment.get("recommended_rounds", 4)
    metrics.recommended_experts = complexity_assessment.get("recommended_experts", 4)
    metrics.complexity_reasoning = complexity_assessment.get(
        "reasoning", "Complexity assessment completed"
    )

    # Track complexity assessment cost
    track_phase_cost(metrics, "complexity_assessment", complexity_response)

    logger.info(
        f"decompose_node: Complete - {len(sub_problems)} sub-problems, "
        f"complexity={metrics.complexity_score:.2f}, "
        f"recommended_rounds={metrics.recommended_rounds}, "
        f"recommended_experts={metrics.recommended_experts} "
        f"(cost: ${response.cost_total + complexity_response.cost_total:.4f})"
    )

    # Return state updates with adaptive max_rounds
    return {
        "problem": problem,
        "current_sub_problem": sub_problems[0] if sub_problems else None,
        "phase": DeliberationPhase.DECOMPOSITION,
        "metrics": metrics,
        "max_rounds": metrics.recommended_rounds,  # Adaptive based on complexity
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
    logger.info("facilitator_decide_node: Making facilitator decision")

    # PROACTIVE RESEARCH EXECUTION: Check for pending research queries from previous round
    # If queries exist, automatically trigger research node without facilitator decision
    pending_queries = state.get("pending_research_queries", [])
    if pending_queries:
        logger.info(
            f"facilitator_decide_node: {len(pending_queries)} pending research queries detected. "
            f"Triggering proactive research."
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
    """Execute external research requested by facilitator or triggered proactively.

    Flow:
    1. Check for pending_research_queries from proactive detection
    2. If none, extract research query from facilitator decision
    3. Check semantic cache (PostgreSQL + Voyage embeddings)
    4. If cache miss: Brave Search (default) or Tavily (premium) + summarization
    5. Add research to deliberation context
    6. Continue to next round with enriched context

    Research Strategy:
    - Default: Brave Search + Haiku (~$0.025/query) for facts/statistics
    - Premium: Tavily ($0.001/query) for competitor/market/regulatory analysis

    Args:
        state: Current graph state

    Returns:
        State updates with research results
    """
    from bo1.agents.researcher import ResearcherAgent

    # PROACTIVE RESEARCH: Check for pending queries first
    pending_queries = state.get("pending_research_queries", [])

    if pending_queries:
        logger.info(f"[RESEARCH] Processing {len(pending_queries)} proactive research queries")

        # Execute all pending queries
        researcher = ResearcherAgent()

        # Convert pending queries to research format
        research_questions = []
        for query_data in pending_queries:
            research_questions.append(
                {
                    "question": query_data.get("question", ""),
                    "priority": query_data.get("priority", "MEDIUM"),
                    "reason": query_data.get("reason", ""),
                }
            )

        # Determine research depth based on query priorities
        has_high_priority = any(q.get("priority") == "HIGH" for q in pending_queries)
        research_depth: Literal["basic", "deep"] = "deep" if has_high_priority else "basic"

        # Perform research (uses cache if available)
        results = await researcher.research_questions(
            questions=research_questions,
            category="general",
            research_depth=research_depth,
        )

        # Add to state context
        research_results_obj = state.get("research_results", [])
        research_results = (
            list(research_results_obj) if isinstance(research_results_obj, list) else []
        )

        for result in results:
            research_results.append(
                {
                    "query": result["question"],
                    "summary": result["summary"],
                    "sources": result.get("sources", []),
                    "cached": result.get("cached", False),
                    "cost": result.get("cost", 0.0),
                    "round": state.get("round_number", 0),
                    "depth": research_depth,
                    "proactive": True,  # Mark as proactively triggered
                }
            )

        total_cost = sum(r.get("cost", 0.0) for r in results)
        logger.info(
            f"[RESEARCH] Proactive research complete - {len(results)} queries, "
            f"Total cost: ${total_cost:.4f}"
        )

        # Clear pending queries
        return {
            "research_results": research_results,
            "pending_research_queries": [],  # Clear after processing
            "facilitator_decision": None,  # Clear decision to prevent loops
            "current_node": "research",
            "sub_problem_index": state.get("sub_problem_index", 0),
        }

    # FALLBACK: Extract research query from facilitator decision
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
    facilitator_research_depth: Literal["basic", "deep"] = (
        "deep"
        if any(keyword in decision_reasoning.lower() for keyword in deep_keywords)
        else "basic"
    )

    logger.info(f"[RESEARCH] Depth: {facilitator_research_depth}")

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
        research_depth=facilitator_research_depth,
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
            "depth": facilitator_research_depth,
        }
    )

    logger.info(
        f"[RESEARCH] Complete - Cached: {result.get('cached', False)}, "
        f"Depth: {facilitator_research_depth}, Cost: ${result.get('cost', 0):.4f}"
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

    logger.info("vote_node: Starting recommendation collection phase")

    # Create broker for LLM calls
    broker = PromptBroker()

    # Collect recommendations from all personas with v2 state
    recommendations, llm_responses = await collect_recommendations(state=state, broker=broker)

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
        conditions = vote.get("conditions")
        if conditions and isinstance(conditions, list):
            all_contributions_and_votes.append(
                f"Conditions: {', '.join(str(c) for c in conditions)}\n"
            )
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
        max_tokens=1500,  # Reduced from 3000 to force conciseness
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
        user_message="Generate the JSON action plan now:",
        prefill="{",  # Force pure JSON output (no markdown, no XML wrapper)
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
# PARALLEL SUB-PROBLEMS - Dependency Analysis (Phase 1-2)
# ============================================================================


def topological_batch_sort(sub_problems: list[SubProblem]) -> list[list[int]]:
    """Sort sub-problems into execution batches respecting dependencies.

    Returns list of batches, where each batch contains indices of
    sub-problems that can run in parallel.

    Args:
        sub_problems: List of SubProblem objects with dependencies

    Returns:
        List of batches, where each batch is a list of sub-problem indices
        that can be executed in parallel

    Raises:
        ValueError: If circular dependency detected

    Examples:
        >>> sp1 = SubProblem(id="sp_001", goal="A", context="", complexity_score=5, dependencies=[])
        >>> sp2 = SubProblem(id="sp_002", goal="B", context="", complexity_score=5, dependencies=["sp_001"])
        >>> sp3 = SubProblem(id="sp_003", goal="C", context="", complexity_score=5, dependencies=[])
        >>> batches = topological_batch_sort([sp1, sp2, sp3])
        >>> batches
        [[0, 2], [1]]  # sp_001 and sp_003 can run in parallel, then sp_002
    """
    # Build ID to index mapping (kept for potential future use in validation)
    _id_to_idx = {sp.id: i for i, sp in enumerate(sub_problems)}  # noqa: F841
    in_degree = [len(sp.dependencies) for sp in sub_problems]
    batches = []
    remaining = set(range(len(sub_problems)))

    while remaining:
        # Find all sub-problems with no remaining dependencies
        batch = [i for i in remaining if in_degree[i] == 0]

        if not batch:
            # No sub-problems ready -> circular dependency
            raise ValueError("Circular dependency detected in sub-problems")

        batches.append(batch)

        # Remove batch from remaining
        for idx in batch:
            remaining.remove(idx)
            sp_id = sub_problems[idx].id

            # Decrement in-degree for sub-problems that depend on this one
            for other_idx in remaining:
                if sp_id in sub_problems[other_idx].dependencies:
                    in_degree[other_idx] -= 1

    return batches


async def analyze_dependencies_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Analyze sub-problem dependencies and create execution batches.

    This node runs after decomposition to determine which sub-problems
    can be executed in parallel vs sequentially.

    Args:
        state: Current graph state (must have problem with sub_problems)

    Returns:
        Dictionary with state updates:
        - execution_batches: List of batches (each batch = list of sub-problem indices)
        - parallel_mode: Boolean indicating if any batches have >1 sub-problem

    Examples:
        If sub-problems are: [A (no deps), B (depends on A), C (no deps)]
        Then execution_batches = [[0, 2], [1]]  # A and C parallel, then B
        And parallel_mode = True (batch 0 has 2 sub-problems)
    """
    from bo1.feature_flags.features import ENABLE_PARALLEL_SUBPROBLEMS

    logger.info("analyze_dependencies_node: Starting dependency analysis")

    problem = state.get("problem")
    if not problem:
        raise ValueError("analyze_dependencies_node called without problem")

    sub_problems = problem.sub_problems

    # Check if parallel sub-problems feature is enabled
    if not ENABLE_PARALLEL_SUBPROBLEMS or len(sub_problems) <= 1:
        # Sequential mode or single sub-problem
        logger.info(
            f"analyze_dependencies_node: Sequential mode "
            f"(feature_flag={ENABLE_PARALLEL_SUBPROBLEMS}, sub_problems={len(sub_problems)})"
        )
        return {
            "execution_batches": [[i] for i in range(len(sub_problems))],
            "parallel_mode": False,
            "current_node": "analyze_dependencies",
        }

    # Perform topological sort to find execution batches
    try:
        batches = topological_batch_sort(sub_problems)

        # Check if any batch has more than 1 sub-problem (actual parallelism)
        has_parallelism = any(len(batch) > 1 for batch in batches)

        logger.info(
            f"analyze_dependencies_node: Complete - {len(batches)} batches, "
            f"parallel={has_parallelism}, batches={batches}"
        )

        return {
            "execution_batches": batches,
            "parallel_mode": has_parallelism,
            "current_node": "analyze_dependencies",
        }

    except ValueError as e:
        # Circular dependency detected
        logger.error(f"analyze_dependencies_node: {e}. Falling back to sequential execution.")

        # Fallback: execute all sub-problems sequentially
        return {
            "execution_batches": [[i] for i in range(len(sub_problems))],
            "parallel_mode": False,
            "dependency_error": str(e),
            "current_node": "analyze_dependencies",
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

    # Lightweight quality check after semantic deduplication
    quality_results: list[Any] = []
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
                facilitator_guidance = state.get("facilitator_guidance") or {}
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

                # Store updated guidance in state (will be returned at end)
                # Note: We'll include this in the return dict below

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
            f"parallel_round_node: Complete - Round {round_number} → {next_round}, "
            f"{len(filtered_contributions)} contributions added "
            f"(quality: {avg_quality:.2f}, {shallow_count} shallow)"
        )
    else:
        logger.info(
            f"parallel_round_node: Complete - Round {round_number} → {next_round}, "
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
    }

    # Include facilitator_guidance if it was updated with quality issues
    if "facilitator_guidance" in locals():
        return_dict["facilitator_guidance"] = facilitator_guidance

    return return_dict


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

    Selection Strategy (Adaptive based on complexity):
    - Uses metrics.recommended_experts as baseline (3-5 based on complexity)
    - Exploration: recommended_experts (broad exploration, prioritize unheard voices)
    - Challenge: max(2, recommended_experts - 1) (focused debate, avoid recent speakers)
    - Convergence: max(2, recommended_experts - 1) (synthesis, balanced representation)

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

    # Get adaptive expert count from complexity assessment
    metrics = state.get("metrics")
    recommended_experts = 4  # Default fallback
    if metrics and hasattr(metrics, "recommended_experts") and metrics.recommended_experts:
        recommended_experts = metrics.recommended_experts
    logger.info(f"Using recommended_experts={recommended_experts} from complexity assessment")

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

    # Phase-specific selection (adaptive based on complexity)
    if phase == "exploration":
        # Select recommended_experts, prioritize those who haven't spoken much
        target_count = min(recommended_experts, len(personas))

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
        # Select fewer experts for focused debate (recommended - 1, minimum 2)
        target_count = min(max(2, recommended_experts - 1), len(personas))

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
        # Select fewer experts for synthesis (recommended - 1, minimum 2)
        target_count = min(max(2, recommended_experts - 1), len(personas))

        # Select balanced set (least-contributing experts to ensure all voices heard)
        selected = sorted(personas, key=lambda p: contribution_counts.get(p.code, 0))[:target_count]

    else:
        # Default: use recommended_experts
        target_count = min(recommended_experts, len(personas))
        selected = personas[:target_count]

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
    import asyncio

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
    speaker_prompt = _get_phase_prompt(phase, round_number)

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
        research_results = state.get("research_results", [])
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


def phase_prompt_short(phase: str) -> str:
    """Get simplified phase prompt for retry attempts."""
    if phase == "exploration":
        return "Share your key insights and concerns."
    elif phase == "challenge":
        return "Challenge an assumption or add new evidence."
    elif phase == "convergence":
        return "Provide your recommendation and main reason."
    else:
        return "Provide your expert analysis."


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


# ============================================================================
# CONTEXT PASSING HELPERS (Phase 1.5 - Issue #22)
# ============================================================================


def extract_recommendation_from_synthesis(synthesis: str) -> str:
    """Extract key recommendation from synthesis XML.

    Parses synthesis content to extract the core recommendation for context passing.
    Tries multiple XML tags in order of preference:
    1. <recommendation> tag (most specific)
    2. <executive_summary> tag (fallback)
    3. First 500 characters (last resort)

    Args:
        synthesis: Full synthesis text (may contain XML tags)

    Returns:
        Extracted recommendation text (truncated to 500 chars max)

    Example:
        >>> synthesis = "<recommendation>Invest in SEO...</recommendation>"
        >>> extract_recommendation_from_synthesis(synthesis)
        'Invest in SEO...'
    """
    import re

    # Try to extract <recommendation> tag content
    match = re.search(r"<recommendation[^>]*>(.*?)</recommendation>", synthesis, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try executive_summary as fallback
    match = re.search(r"<executive_summary[^>]*>(.*?)</executive_summary>", synthesis, re.DOTALL)
    if match:
        content = match.group(1).strip()
        return content[:500] + "..." if len(content) > 500 else content

    # Last resort: first 500 chars
    return synthesis[:500] + "..." if len(synthesis) > 500 else synthesis


def build_dependency_context(
    current_sp: SubProblem, sub_problem_results: list[SubProblemResult], problem: Problem
) -> str | None:
    """Build context from dependent sub-problems.

    When a sub-problem has dependencies (earlier sub-problems that must complete first),
    this function extracts their conclusions and formats them for expert context.

    This fixes Issue #22A: Full synthesis not passed to dependent sub-problems.

    Args:
        current_sp: The current sub-problem being deliberated
        sub_problem_results: Results from completed sub-problems
        problem: The parent problem (contains all sub-problem metadata)

    Returns:
        Formatted dependency context string, or None if no dependencies

    Example:
        >>> # Sub-problem 2 depends on sub-problem 1
        >>> context = build_dependency_context(sp2, [result1], problem)
        >>> print(context)
        <dependent_conclusions>
        This sub-problem depends on conclusions from earlier sub-problems:

        **Determine pricing tier structure** (Resolved)
        Key Conclusion: Use 3-tier model with $49, $99, $199 pricing...
        </dependent_conclusions>
    """
    if not current_sp.dependencies:
        return None

    context_parts = []
    context_parts.append("<dependent_conclusions>")
    context_parts.append("This sub-problem depends on conclusions from earlier sub-problems:\n")

    for dep_id in current_sp.dependencies:
        # Find the dependency sub-problem
        dep_sp = next((sp for sp in problem.sub_problems if sp.id == dep_id), None)
        if not dep_sp:
            logger.warning(f"Dependency {dep_id} not found in problem.sub_problems")
            continue

        # Find the result for this dependency
        dep_result = next((r for r in sub_problem_results if r.sub_problem_id == dep_id), None)
        if not dep_result:
            logger.warning(f"No result found for dependency {dep_id}")
            continue

        # Extract key recommendation from synthesis
        recommendation = extract_recommendation_from_synthesis(dep_result.synthesis)

        context_parts.append(f"""
**{dep_sp.goal}** (Resolved)
Key Conclusion: {recommendation}
""")

    context_parts.append("</dependent_conclusions>")
    return "\n".join(context_parts)


def build_subproblem_context_for_all(sub_problem_results: list[SubProblemResult]) -> str | None:
    """Build context from all completed sub-problems for any expert.

    Provides ALL experts (even new ones) with context about previous sub-problem outcomes.
    This ensures experts who didn't participate in earlier sub-problems still know what
    was decided.

    This fixes Issue #22B: Non-participating experts get no context.

    Args:
        sub_problem_results: Results from all completed sub-problems

    Returns:
        Formatted context string, or None if no results

    Example:
        >>> context = build_subproblem_context_for_all([result1, result2])
        >>> print(context)
        <previous_subproblem_outcomes>

        Sub-problem: Determine pricing tier structure
        Conclusion: Use 3-tier model with $49, $99, $199 pricing...
        Expert Panel: maria, zara, chen

        Sub-problem: Select acquisition channels
        Conclusion: Focus on SEO and content marketing initially...
        Expert Panel: tariq, aria, elena
        </previous_subproblem_outcomes>
    """
    if not sub_problem_results:
        return None

    context_parts = []
    context_parts.append("<previous_subproblem_outcomes>")

    for result in sub_problem_results:
        recommendation = extract_recommendation_from_synthesis(result.synthesis)

        context_parts.append(f"""
Sub-problem: {result.sub_problem_goal}
Conclusion: {recommendation}
Expert Panel: {", ".join(result.expert_panel)}
""")

    context_parts.append("</previous_subproblem_outcomes>")
    return "\n".join(context_parts)


# ============================================================================
# PARALLEL SUB-PROBLEMS - Core Execution (Phases 3-4)
# ============================================================================


async def _deliberate_subproblem(
    sub_problem: SubProblem,
    problem: Problem,
    all_personas: list[PersonaProfile],
    previous_results: list[SubProblemResult],
    sub_problem_index: int,
    user_id: str | None = None,
    event_bridge: Any | None = None,  # EventBridge | None (avoid circular import)
) -> SubProblemResult:
    """Run complete deliberation for a single sub-problem.

    This encapsulates the full deliberation lifecycle:
    - Persona selection for this specific sub-problem
    - Initial round
    - Multi-round deliberation (up to 6 rounds)
    - Convergence checking
    - Voting/recommendations collection
    - Synthesis generation

    This function is designed to be called in parallel for independent sub-problems.

    Args:
        sub_problem: The sub-problem to deliberate
        problem: The parent problem (for context)
        all_personas: Available personas (persona selection will choose subset)
        previous_results: Results from previously completed sub-problems (for expert memory)
        sub_problem_index: Index of this sub-problem (0-based) for event tracking
        user_id: Optional user ID for context persistence
        event_bridge: Optional EventBridge for emitting real-time events during parallel execution

    Returns:
        SubProblemResult with synthesis, votes, costs, and expert summaries

    Example:
        >>> # Parallel execution of independent sub-problems
        >>> tasks = [
        ...     _deliberate_subproblem(sp1, problem, personas, []),
        ...     _deliberate_subproblem(sp2, problem, personas, []),
        ... ]
        >>> results = await asyncio.gather(*tasks)
    """
    from bo1.agents.selector import PersonaSelectorAgent
    from bo1.agents.summarizer import SummarizerAgent
    from bo1.data import get_persona_by_code
    from bo1.llm.broker import PromptBroker, PromptRequest
    from bo1.models.persona import PersonaProfile
    from bo1.orchestration.voting import collect_recommendations
    from bo1.prompts.reusable_prompts import SYNTHESIS_PROMPT_TEMPLATE

    logger.info(
        f"_deliberate_subproblem: Starting deliberation for sub-problem '{sub_problem.id}': {sub_problem.goal[:80]}"
    )

    # Track metrics for this sub-problem
    from bo1.models.state import DeliberationMetrics

    metrics = DeliberationMetrics()
    start_time = time.time()

    # Step 1: Select personas for this sub-problem
    logger.info(f"_deliberate_subproblem: Selecting personas for {sub_problem.id}")
    selector = PersonaSelectorAgent()
    response = await selector.recommend_personas(
        sub_problem=sub_problem,
        problem_context=problem.context,
    )

    # Parse recommendations
    recommendations = json.loads(response.content)
    recommended_personas = recommendations.get("recommended_personas", [])
    persona_codes = [p["code"] for p in recommended_personas]

    # Load persona profiles
    personas = []
    for code in persona_codes:
        persona_dict = get_persona_by_code(code)
        if persona_dict:
            persona = PersonaProfile.model_validate(persona_dict)
            personas.append(persona)

    # Track persona selection cost
    track_phase_cost(metrics, "persona_selection", response)

    # Emit persona selection events (one per persona, matching sequential execution)
    if event_bridge:
        for i, persona in enumerate(personas):
            # Find matching rationale from recommendations
            rationale = ""
            for rec in recommended_personas:
                if rec.get("code") == persona.code:
                    rationale = rec.get("rationale", "")
                    break

            persona_dict = {
                "code": persona.code,
                "name": persona.name,
                "archetype": persona.archetype,
                "display_name": persona.display_name,
                "domain_expertise": persona.domain_expertise,
            }

            event_bridge.emit(
                "persona_selected",
                {
                    "persona": persona_dict,
                    "rationale": rationale,
                    "order": i + 1,
                },
            )

    logger.info(
        f"_deliberate_subproblem: Selected {len(personas)} personas for {sub_problem.id}: {persona_codes}"
    )

    # Step 2: Build expert memory from previous results
    expert_memory: dict[str, str] = {}
    if previous_results:
        # Build memory parts first
        memory_parts: dict[str, list[str]] = {}
        for result in previous_results:
            for expert_code, summary in result.expert_summaries.items():
                if expert_code not in memory_parts:
                    memory_parts[expert_code] = []
                memory_parts[expert_code].append(
                    f"Sub-problem: {result.sub_problem_goal}\nYour position: {summary}"
                )

        # Join memory parts for each expert
        expert_memory = {code: "\n\n".join(parts) for code, parts in memory_parts.items() if parts}

        logger.info(
            f"_deliberate_subproblem: Built expert memory for {len(expert_memory)} experts from {len(previous_results)} previous sub-problems"
        )

    # Step 3: Run deliberation rounds
    from bo1.graph.safety.loop_prevention import get_adaptive_max_rounds

    contributions = []
    round_summaries = []
    # Issue #11: Use adaptive round limits based on sub-problem complexity
    max_rounds = get_adaptive_max_rounds(sub_problem.complexity_score)

    # Create a minimal graph state for deliberation
    # This allows us to reuse existing parallel_round_node logic
    mini_state = DeliberationGraphState(
        session_id=f"subproblem_{sub_problem.id}",
        problem=problem,
        current_sub_problem=sub_problem,
        personas=personas,
        contributions=[],
        round_summaries=[],
        phase=DeliberationPhase.DISCUSSION,
        round_number=1,
        max_rounds=max_rounds,
        metrics=metrics,
        facilitator_decision=None,
        should_stop=False,
        stop_reason=None,
        user_input=None,
        user_id=user_id,
        current_node="parallel_subproblem_deliberation",
        votes=[],
        synthesis=None,
        sub_problem_results=previous_results,
        sub_problem_index=sub_problem_index,
        collect_context=False,
        business_context=None,
        pending_clarification=None,
        phase_costs={},
        current_phase="exploration",
        experts_per_round=[],
        semantic_novelty_scores={},
        exploration_score=0.0,
        focus_score=1.0,
        completed_research_queries=[],
    )

    # Run rounds until convergence or max rounds (parallel multi-expert architecture)
    for round_num in range(1, max_rounds + 1):
        mini_state["round_number"] = round_num

        # Emit round start event
        if event_bridge:
            event_bridge.emit(
                "round_started",
                {
                    "round_number": round_num,
                },
            )

        # Run parallel round
        updates = await parallel_round_node(mini_state)

        # Update mini_state with results
        mini_state["contributions"] = updates["contributions"]
        mini_state["round_number"] = updates["round_number"]
        mini_state["round_summaries"] = updates["round_summaries"]
        mini_state["metrics"] = updates["metrics"]
        mini_state["current_phase"] = updates.get("current_phase", "exploration")
        mini_state["experts_per_round"] = updates.get("experts_per_round", [])

        # Emit individual contribution events (matching sequential execution)
        if event_bridge:
            # Get contributions from this round
            round_contributions = [
                c for c in mini_state["contributions"] if c.round_number == round_num
            ]

            # Emit one event per contribution
            for contrib in round_contributions:
                # Get persona profile for archetype and domain_expertise
                contrib_persona: PersonaProfile | None = None
                for p in personas:
                    if p.code == contrib.persona_code:
                        contrib_persona = p
                        break

                # Note: contribution_summaries are not generated in parallel execution
                # The summary field is optional in frontend TypeScript types
                event_bridge.emit(
                    "contribution",
                    {
                        "persona_code": contrib.persona_code,
                        "persona_name": contrib.persona_name,
                        "archetype": contrib_persona.archetype if contrib_persona else "",
                        "domain_expertise": contrib_persona.domain_expertise
                        if contrib_persona
                        else [],
                        "content": contrib.content,
                        "round": round_num,
                        "contribution_type": "initial" if round_num == 1 else "followup",
                    },
                )

        # Check convergence
        from bo1.graph.safety.loop_prevention import check_convergence_node

        convergence_updates = await check_convergence_node(mini_state)
        mini_state["should_stop"] = convergence_updates.get("should_stop", False)
        mini_state["stop_reason"] = convergence_updates.get("stop_reason")

        if mini_state["should_stop"]:
            logger.info(
                f"_deliberate_subproblem: Convergence reached at round {round_num} for {sub_problem.id}"
            )
            break

    # Extract final contributions and summaries
    contributions = mini_state["contributions"]
    round_summaries = mini_state["round_summaries"]
    metrics = mini_state["metrics"]

    logger.info(
        f"_deliberate_subproblem: Deliberation complete for {sub_problem.id} - {len(contributions)} contributions, {len(round_summaries)} rounds"
    )

    # Step 4: Collect recommendations
    logger.info(f"_deliberate_subproblem: Collecting recommendations for {sub_problem.id}")

    # Emit voting started event
    if event_bridge:
        event_bridge.emit(
            "voting_started",
            {
                "experts": [p.code for p in personas],
                "count": len(personas),
            },
        )

    broker = PromptBroker()
    recommendations, llm_responses = await collect_recommendations(state=mini_state, broker=broker)
    track_aggregated_cost(metrics, "voting", llm_responses)

    # Convert recommendations to dicts
    votes = [
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

    logger.info(
        f"_deliberate_subproblem: Collected {len(votes)} recommendations for {sub_problem.id}"
    )

    # Emit voting complete event
    if event_bridge:
        # Calculate consensus level based on agreement (simple heuristic)
        # Could be improved with actual consensus analysis
        consensus_level = "moderate"
        if len(votes) >= len(personas) * 0.8:
            consensus_level = "strong"
        elif len(votes) < len(personas) * 0.5:
            consensus_level = "weak"

        event_bridge.emit(
            "voting_complete",
            {
                "votes_count": len(votes),
                "consensus_level": consensus_level,
            },
        )

    # Step 5: Generate synthesis
    logger.info(f"_deliberate_subproblem: Generating synthesis for {sub_problem.id}")

    # Emit synthesis started event
    if event_bridge:
        event_bridge.emit("synthesis_started", {})

    # Format contributions and votes
    all_contributions_and_votes = []
    all_contributions_and_votes.append("=== DISCUSSION ===\n")
    for contrib in contributions:
        all_contributions_and_votes.append(
            f"Round {contrib.round_number} - {contrib.persona_name}:\n{contrib.content}\n"
        )

    all_contributions_and_votes.append("\n=== RECOMMENDATIONS ===\n")
    for vote in votes:
        all_contributions_and_votes.append(
            f"{vote['persona_name']}: {vote['recommendation']} "
            f"(confidence: {vote['confidence']:.2f})\n"
            f"Reasoning: {vote['reasoning']}\n"
        )
        conditions = vote.get("conditions")
        if conditions and isinstance(conditions, list):
            all_contributions_and_votes.append(
                f"Conditions: {', '.join(str(c) for c in conditions)}\n"
            )
        all_contributions_and_votes.append("\n")

    full_context = "".join(all_contributions_and_votes)

    synthesis_prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
        problem_statement=sub_problem.goal,
        all_contributions_and_votes=full_context,
    )

    broker = PromptBroker()
    request = PromptRequest(
        system=synthesis_prompt,
        user_message="Generate the synthesis report now.",
        prefill="<thinking>",
        model="sonnet",
        temperature=0.7,
        max_tokens=3000,
        phase="synthesis",
        agent_type="synthesizer",
    )

    response = await broker.call(request)
    synthesis = "<thinking>" + response.content
    track_phase_cost(metrics, "synthesis", response)

    logger.info(
        f"_deliberate_subproblem: Synthesis generated for {sub_problem.id} (cost: ${response.cost_total:.4f})"
    )

    # Emit synthesis complete event
    if event_bridge:
        event_bridge.emit(
            "synthesis_complete",
            {
                "synthesis": synthesis,
                "word_count": len(synthesis.split()),
            },
        )

    # Step 6: Generate expert summaries for memory
    expert_summaries: dict[str, str] = {}
    summarizer = SummarizerAgent()

    for persona in personas:
        expert_contributions = [c for c in contributions if c.persona_code == persona.code]

        if expert_contributions:
            try:
                contribution_dicts = [
                    {"persona": c.persona_name, "content": c.content} for c in expert_contributions
                ]

                summary_response = await summarizer.summarize_round(
                    round_number=mini_state["round_number"],
                    contributions=contribution_dicts,
                    problem_statement=sub_problem.goal,
                    target_tokens=75,
                )

                expert_summaries[persona.code] = summary_response.content
                track_phase_cost(metrics, "expert_memory", summary_response)

            except Exception as e:
                logger.warning(
                    f"Failed to generate summary for {persona.display_name} in {sub_problem.id}: {e}"
                )

    # Calculate duration
    duration_seconds = time.time() - start_time

    # Create result
    result = SubProblemResult(
        sub_problem_id=sub_problem.id,
        sub_problem_goal=sub_problem.goal,
        synthesis=synthesis,
        votes=votes,
        contribution_count=len(contributions),
        cost=metrics.total_cost,
        duration_seconds=duration_seconds,
        expert_panel=[p.code for p in personas],
        expert_summaries=expert_summaries,
    )

    logger.info(
        f"_deliberate_subproblem: Complete for {sub_problem.id} - "
        f"{len(contributions)} contributions, ${metrics.total_cost:.4f}, {duration_seconds:.1f}s"
    )

    return result


async def parallel_subproblems_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Execute independent sub-problems in parallel using asyncio.gather().

    This node implements the core parallel sub-problem execution strategy:
    1. Reads execution_batches from state (computed by analyze_dependencies_node)
    2. For each batch, runs all sub-problems in that batch concurrently
    3. Passes completed results to next batch (for expert memory)
    4. Returns all SubProblemResult objects

    Batching respects dependencies: sub-problems in batch N can depend on
    results from batches 0..N-1, but not on other sub-problems in batch N.

    Args:
        state: Current graph state (must have execution_batches, problem)

    Returns:
        Dictionary with state updates:
        - sub_problem_results: All results from all batches
        - current_sub_problem: None (all complete)
        - phase: SYNTHESIS (ready for meta-synthesis)

    Example:
        Given execution_batches = [[0, 1], [2]]:
        - Batch 0: Deliberate sub-problems 0 and 1 in parallel
        - Batch 1: Deliberate sub-problem 2 (can reference results from 0, 1)
        - Return all 3 results
    """
    import asyncio

    logger.info("parallel_subproblems_node: Starting parallel sub-problem execution")

    problem = state.get("problem")
    if not problem:
        raise ValueError("parallel_subproblems_node called without problem")

    # Get session_id and event publisher for real-time event emission
    session_id = state.get("session_id")
    if not session_id:
        logger.warning(
            "No session_id in state - events will not be emitted during parallel execution"
        )
        event_publisher = None
    else:
        # Import here to avoid circular imports
        from backend.api.dependencies import get_event_publisher

        event_publisher = get_event_publisher()

    execution_batches = state.get("execution_batches", [])
    if not execution_batches:
        logger.warning("No execution_batches in state, creating sequential batches")
        execution_batches = [[i] for i in range(len(problem.sub_problems))]

    sub_problems = problem.sub_problems
    user_id = state.get("user_id")

    # Get all available personas for selection
    from bo1.data import get_active_personas

    all_personas_dicts = get_active_personas()
    all_personas = [PersonaProfile.model_validate(p) for p in all_personas_dicts]

    # Track all results across batches
    all_results: list[SubProblemResult] = []
    total_batches = len(execution_batches)

    logger.info(
        f"parallel_subproblems_node: Executing {total_batches} batches for {len(sub_problems)} sub-problems"
    )

    # Execute batches sequentially, sub-problems within batch in parallel
    for batch_idx, batch in enumerate(execution_batches):
        logger.info(
            f"parallel_subproblems_node: Starting batch {batch_idx + 1}/{total_batches} with {len(batch)} sub-problems: {batch}"
        )

        # Create tasks for all sub-problems in this batch
        batch_tasks = []
        for sp_index in batch:
            if sp_index >= len(sub_problems):
                logger.error(
                    f"Invalid sub-problem index {sp_index} in batch {batch_idx} (only {len(sub_problems)} sub-problems)"
                )
                continue

            sub_problem = sub_problems[sp_index]

            # Create EventBridge for this sub-problem (if event_publisher available)
            event_bridge = None
            if event_publisher and session_id:
                from backend.api.event_bridge import EventBridge

                event_bridge = EventBridge(session_id, event_publisher)
                event_bridge.set_sub_problem_index(sp_index)

            # Create deliberation task with retry wrapper
            # Retries up to 3 times with exponential backoff (2s, 4s, 8s)
            task = retry_with_backoff(
                _deliberate_subproblem,
                sub_problem=sub_problem,
                problem=problem,
                all_personas=all_personas,
                previous_results=all_results,  # Results from previous batches
                sub_problem_index=sp_index,
                user_id=user_id,
                event_bridge=event_bridge,  # Pass EventBridge for real-time events
                max_retries=3,
                initial_delay=2.0,
                backoff_factor=2.0,
            )
            batch_tasks.append((sp_index, task))

        # Execute batch in parallel
        logger.info(f"parallel_subproblems_node: Executing {len(batch_tasks)} tasks in parallel")
        batch_results_raw = await asyncio.gather(
            *[t[1] for t in batch_tasks], return_exceptions=True
        )

        # Pair results with indices, failing if any sub-problem failed
        batch_results: list[tuple[int, SubProblemResult]] = []
        failed_subproblems: list[tuple[int, str, Exception]] = []

        for i, result in enumerate(batch_results_raw):
            sp_index = batch_tasks[i][0]
            if isinstance(result, Exception):
                sub_problem_goal = sub_problems[sp_index].goal
                logger.error(
                    f"parallel_subproblems_node: CRITICAL - Sub-problem {sp_index} "
                    f"('{sub_problem_goal}') failed after all retries: {result}",
                    exc_info=result,
                )
                failed_subproblems.append((sp_index, sub_problem_goal, result))
            else:
                # Type assertion: result is SubProblemResult when not an Exception
                assert isinstance(result, SubProblemResult)
                batch_results.append((sp_index, result))

        # If any sub-problem failed, fail the entire deliberation with clear error
        if failed_subproblems:
            failed_list = "\n".join(
                f"  - Sub-problem {idx}: '{goal}' - {type(err).__name__}: {err}"
                for idx, goal, err in failed_subproblems
            )
            error_msg = (
                f"Deliberation failed: {len(failed_subproblems)} critical sub-problem(s) "
                f"could not be completed after multiple retries.\n{failed_list}\n\n"
                f"This means the final decision will be incomplete. "
                f"Please try again or contact support if the issue persists."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Add to all_results in the correct order
        for _sp_index, result in sorted(batch_results, key=lambda x: x[0]):
            # Type assertion: result should be SubProblemResult (exceptions filtered above)
            assert isinstance(result, SubProblemResult)
            all_results.append(result)

        # Emit subproblem_complete events for each completed sub-problem in this batch
        # This ensures frontend receives the same events for parallel as sequential execution
        if event_publisher and session_id:
            for sp_index, result in batch_results:
                event_publisher.publish_event(
                    session_id,
                    "subproblem_complete",
                    {
                        "sub_problem_index": sp_index,
                        "goal": result.sub_problem_goal,
                        "synthesis": result.synthesis,
                        "recommendations_count": len(result.votes)
                        if hasattr(result, "votes")
                        else 0,
                        "expert_panel": result.expert_panel,
                        "contribution_count": result.contribution_count,
                        "cost": result.cost,
                        "duration_seconds": result.duration_seconds,
                    },
                )
                logger.info(
                    f"parallel_subproblems_node: Emitted subproblem_complete for sub-problem {sp_index}"
                )

        logger.info(
            f"parallel_subproblems_node: Batch {batch_idx + 1}/{total_batches} complete - "
            f"{len(batch_results)} sub-problems deliberated"
        )

    # Calculate total metrics
    total_cost = sum(r.cost for r in all_results)
    total_contributions = sum(r.contribution_count for r in all_results)
    total_duration = sum(r.duration_seconds for r in all_results)

    logger.info(
        f"parallel_subproblems_node: Complete - {len(all_results)} sub-problems deliberated, "
        f"{total_contributions} total contributions, ${total_cost:.4f}, {total_duration:.1f}s"
    )

    # Update metrics in state
    metrics = ensure_metrics(state)
    # Add costs from all sub-problems (they tracked their own costs)
    for result in all_results:
        metrics.total_cost += result.cost

    return {
        "sub_problem_results": all_results,
        "current_sub_problem": None,  # All complete
        "phase": DeliberationPhase.SYNTHESIS,  # Ready for meta-synthesis
        "metrics": metrics,
        "current_node": "parallel_subproblems",
    }
