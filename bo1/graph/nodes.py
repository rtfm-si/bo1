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
