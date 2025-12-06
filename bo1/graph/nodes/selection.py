"""Persona selection node.

This module contains the select_personas_node function that selects
appropriate expert personas for deliberation.
"""

import json
import logging
from typing import Any

from bo1.agents.selector import PersonaSelectorAgent
from bo1.graph.state import DeliberationGraphState
from bo1.graph.utils import ensure_metrics, track_phase_cost
from bo1.models.persona import PersonaProfile
from bo1.models.state import DeliberationPhase

logger = logging.getLogger(__name__)


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

    # Handle both dict (from checkpoint) and Problem object
    problem = state["problem"]
    problem_context = problem.get("context", "") if isinstance(problem, dict) else problem.context

    # Call selector
    response = await selector.recommend_personas(
        sub_problem=current_sp,
        problem_context=problem_context,
    )

    # Parse recommendations
    recommendations = json.loads(response.content)
    # Extract persona codes from recommended_personas list
    recommended_personas = recommendations.get("recommended_personas", [])
    persona_codes = [p["code"] for p in recommended_personas]

    logger.info(f"Persona codes: {persona_codes}")

    # Load persona profiles
    from bo1.data import get_persona_by_code

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
