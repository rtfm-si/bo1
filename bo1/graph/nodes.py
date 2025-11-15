"""LangGraph node implementations for deliberation.

This module contains node functions that wrap existing v1 agents
and integrate them into the LangGraph execution model.
"""

import json
import logging
from typing import Any

from bo1.agents.decomposer import DecomposerAgent
from bo1.agents.facilitator import FacilitatorAgent
from bo1.agents.selector import PersonaSelectorAgent
from bo1.graph.state import (
    DeliberationGraphState,
    graph_state_to_deliberation_state,
)
from bo1.models.problem import SubProblem
from bo1.models.state import DeliberationPhase
from bo1.orchestration.deliberation import DeliberationEngine

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

    # Parse decomposition
    decomposition = json.loads(response.content)

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
    metrics = state.get("metrics")
    if metrics is None:
        from bo1.models.state import DeliberationMetrics

        metrics = DeliberationMetrics()

    metrics.phase_costs["problem_decomposition"] = response.cost_total
    metrics.total_cost += response.cost_total

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
    metrics = state.get("metrics")
    if metrics is None:
        from bo1.models.state import DeliberationMetrics

        metrics = DeliberationMetrics()

    metrics.phase_costs["persona_selection"] = response.cost_total
    metrics.total_cost += response.cost_total

    logger.info(
        f"select_personas_node: Complete - {len(personas)} personas selected "
        f"(cost: ${response.cost_total:.4f})"
    )

    # Return state updates
    return {
        "personas": personas,
        "phase": DeliberationPhase.SELECTION,
        "metrics": metrics,
        "current_node": "select_personas",
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
    metrics = state.get("metrics")
    if metrics is None:
        from bo1.models.state import DeliberationMetrics

        metrics = DeliberationMetrics()

    round_cost = sum(r.cost_total for r in llm_responses)
    metrics.phase_costs["initial_round"] = round_cost
    metrics.total_cost += round_cost

    logger.info(
        f"initial_round_node: Complete - {len(contributions)} contributions "
        f"(cost: ${round_cost:.4f})"
    )

    # Return state updates
    return {
        "contributions": contributions,
        "phase": DeliberationPhase.DISCUSSION,
        "round_number": 1,
        "metrics": metrics,
        "current_node": "initial_round",
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
    max_rounds = state.get("max_rounds", 10)

    # Call facilitator to decide next action
    decision, llm_response = await facilitator.decide_next_action(
        state=v1_state,
        round_number=round_number,
        max_rounds=max_rounds,
    )

    # Track cost in metrics (if LLM was called)
    metrics = state.get("metrics")
    if metrics is None:
        from bo1.models.state import DeliberationMetrics

        metrics = DeliberationMetrics()

    if llm_response:
        metrics.phase_costs["facilitator_decision"] = (
            metrics.phase_costs.get("facilitator_decision", 0.0) + llm_response.cost_total
        )
        metrics.total_cost += llm_response.cost_total
        cost_msg = f"(cost: ${llm_response.cost_total:.4f})"
    else:
        cost_msg = "(no LLM call)"

    logger.info(f"facilitator_decide_node: Complete - action={decision.action} {cost_msg}")

    # Return state updates with facilitator decision
    return {
        "facilitator_decision": decision,
        "phase": DeliberationPhase.DISCUSSION,
        "metrics": metrics,
        "current_node": "facilitator_decide",
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
    speaker_code = decision.next_speaker
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

    # Create deliberation engine (constructor takes state argument)
    v1_state = graph_state_to_deliberation_state(state)
    engine = DeliberationEngine(state=v1_state)

    # Call persona with correct signature
    contribution_msg, llm_response = await engine._call_persona_async(
        persona_profile=persona,
        problem_statement=problem.description if problem else "",
        problem_context=problem.context if problem else "",
        participant_list=participant_list,
        round_number=round_number,
        contribution_type=ContributionType.RESPONSE,
        previous_contributions=contributions,
    )

    # Track cost in metrics
    metrics = state.get("metrics")
    if metrics is None:
        from bo1.models.state import DeliberationMetrics

        metrics = DeliberationMetrics()

    phase_key = f"round_{round_number}_deliberation"
    metrics.phase_costs[phase_key] = (
        metrics.phase_costs.get(phase_key, 0.0) + llm_response.cost_total
    )
    metrics.total_cost += llm_response.cost_total

    # Add new contribution to state
    contributions.append(contribution_msg)

    # Increment round number for next round
    next_round = round_number + 1

    logger.info(
        f"persona_contribute_node: Complete - {speaker_code} contributed "
        f"(round {round_number} → {next_round}, cost: ${llm_response.cost_total:.4f})"
    )

    # Return state updates
    return {
        "contributions": contributions,
        "round_number": next_round,
        "metrics": metrics,
        "current_node": "persona_contribute",
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
    moderator_type = (
        decision.moderator_type if decision and decision.moderator_type else "contrarian"
    )

    # Get problem and contributions
    problem = state.get("problem")
    contributions = list(state.get("contributions", []))

    # Build discussion excerpt from recent contributions (last 3)
    recent_contributions = contributions[-3:] if len(contributions) >= 3 else contributions
    discussion_excerpt = "\n\n".join(
        [f"{c.persona_name}: {c.content}" for c in recent_contributions]
    )

    # Get trigger reason from facilitator decision
    trigger_reason = (
        decision.moderator_focus
        if decision and decision.moderator_focus
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
    intervention_msg = ContributionMessage(
        persona_code="moderator",
        persona_name=f"{moderator_type.capitalize()} Moderator",
        content=intervention_text,
        contribution_type=ContributionType.MODERATOR,
        round_number=state.get("round_number", 1),
    )

    # Track cost in metrics
    metrics = state.get("metrics")
    if metrics is None:
        from bo1.models.state import DeliberationMetrics

        metrics = DeliberationMetrics()

    phase_key = f"moderator_intervention_{moderator_type}"
    metrics.phase_costs[phase_key] = (
        metrics.phase_costs.get(phase_key, 0.0) + llm_response.cost_total
    )
    metrics.total_cost += llm_response.cost_total

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
    }


async def vote_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Collect votes from all personas.

    This node wraps the existing collect_votes() function from voting.py
    and updates the graph state with the collected votes.

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates (votes, metrics)
    """
    from bo1.llm.broker import PromptBroker
    from bo1.orchestration.voting import collect_votes

    logger.info("vote_node: Starting voting phase")

    # Convert graph state to v1 DeliberationState for voting
    v1_state = graph_state_to_deliberation_state(state)

    # Create broker for LLM calls
    broker = PromptBroker()

    # Collect votes from all personas
    votes, llm_responses = await collect_votes(state=v1_state, broker=broker)

    # Track cost in metrics
    metrics = state.get("metrics")
    if metrics is None:
        from bo1.models.state import DeliberationMetrics

        metrics = DeliberationMetrics()

    vote_cost = sum(r.cost_total for r in llm_responses)
    metrics.phase_costs["voting"] = vote_cost
    metrics.total_cost += vote_cost

    logger.info(f"vote_node: Complete - {len(votes)} votes collected (cost: ${vote_cost:.4f})")

    # Convert Vote objects to dicts for state storage
    votes_dicts = [
        {
            "persona_code": v.persona_code,
            "persona_name": v.persona_name,
            "decision": v.decision.value,
            "reasoning": v.reasoning,
            "confidence": v.confidence,
            "conditions": v.conditions,
            "weight": v.weight,
        }
        for v in votes
    ]

    # Return state updates
    return {
        "votes": votes_dicts,
        "phase": DeliberationPhase.VOTING,
        "metrics": metrics,
        "current_node": "vote",
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
    all_contributions_and_votes.append("\n=== VOTES ===\n")
    for vote in votes:
        all_contributions_and_votes.append(
            f"{vote['persona_name']}: {vote['decision']} "
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
    metrics = state.get("metrics")
    if metrics is None:
        from bo1.models.state import DeliberationMetrics

        metrics = DeliberationMetrics()

    metrics.phase_costs["synthesis"] = response.cost_total
    metrics.total_cost += response.cost_total

    logger.info(
        f"synthesize_node: Complete - synthesis generated (cost: ${response.cost_total:.4f})"
    )

    # Return state updates
    return {
        "synthesis": synthesis_report_with_disclaimer,
        "phase": DeliberationPhase.COMPLETE,
        "metrics": metrics,
        "current_node": "synthesize",
    }
