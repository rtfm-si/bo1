"""Persona selection node.

This module contains the select_personas_node function that selects
appropriate expert personas for deliberation.
"""

import json
import logging
from typing import Any

from bo1.agents.selector import PersonaSelectorAgent
from bo1.config import get_settings
from bo1.graph.state import DeliberationGraphState
from bo1.graph.utils import (
    calculate_problem_complexity,
    calculate_target_expert_count,
    ensure_metrics,
    track_phase_cost,
)
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
    from bo1.models.problem import SubProblem

    logger.info("select_personas_node: Starting persona selection")

    # Calculate problem complexity and target expert count
    settings = get_settings()
    complexity_score = calculate_problem_complexity(state)
    target_count = calculate_target_expert_count(
        complexity_score,
        min_experts=settings.min_experts,
        max_experts=settings.max_experts,
        threshold_simple=settings.complexity_threshold_simple,
    )

    logger.info(
        f"select_personas_node: Complexity={complexity_score:.2f}, target_experts={target_count}"
    )

    # Create selector agent with target count
    selector = PersonaSelectorAgent()

    # Get current sub-problem - with defensive fallback for resume edge cases
    current_sp = state.get("current_sub_problem")
    sub_problem_index = state.get("sub_problem_index", 0)

    if not current_sp:
        # BUG FIX (P0): Defensive fallback when current_sub_problem is not set
        # This can happen when resuming from checkpoint after clarification
        # if the routing skips analyze_dependencies_node
        problem = state.get("problem")
        if problem:
            # Handle both dict (from checkpoint) and Problem object
            if isinstance(problem, dict):
                sub_problems = problem.get("sub_problems", [])
            else:
                sub_problems = problem.sub_problems or []

            if sub_problems and sub_problem_index < len(sub_problems):
                sp = sub_problems[sub_problem_index]
                # Convert to SubProblem if it's a dict
                if isinstance(sp, dict):
                    current_sp = SubProblem.model_validate(sp)
                else:
                    current_sp = sp
                logger.warning(
                    f"select_personas_node: current_sub_problem was None, "
                    f"using sub_problems[{sub_problem_index}] (id={current_sp.id}) as fallback"
                )

    if not current_sp:
        raise ValueError(
            f"No current sub-problem in state and could not determine from sub_problems "
            f"(sub_problem_index={sub_problem_index})"
        )

    # Handle both dict (from checkpoint) and Problem object
    problem = state["problem"]
    problem_context = problem.get("context", "") if isinstance(problem, dict) else problem.context

    # Call selector with target count for adaptive expert selection
    response = await selector.recommend_personas(
        sub_problem=current_sp,
        problem_context=problem_context,
        target_count=target_count,
    )

    # Parse recommendations
    recommendations = json.loads(response.content)
    # Extract persona codes from recommended_personas list
    recommended_personas = recommendations.get("recommended_personas", [])
    persona_codes = [p["code"] for p in recommended_personas]

    logger.info(f"Persona codes: {persona_codes}")

    # Load persona profiles (uses cached PersonaProfile instances)
    from bo1.data import get_persona_profile_by_code

    personas = []
    for code in persona_codes:
        persona = get_persona_profile_by_code(code)
        if persona:
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
    # BUG FIX (P0): Include current_sub_problem in return to ensure it's persisted
    # for downstream nodes (important when recovered via fallback)
    return {
        "personas": personas,
        "persona_recommendations": recommended_personas,  # Save for display
        "phase": DeliberationPhase.SELECTION,
        "metrics": metrics,
        "current_node": "select_personas",
        "current_sub_problem": current_sp,  # BUG FIX: Persist for downstream nodes
        "sub_problem_index": state.get("sub_problem_index", 0),  # Preserve sub_problem_index
        "problem_complexity": complexity_score,  # Observability: track complexity score
        "target_expert_count": target_count,  # Observability: track target count
    }
