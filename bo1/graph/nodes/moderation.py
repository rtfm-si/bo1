"""Moderator intervention node.

This module contains the moderator_intervene_node that handles moderator interventions
during deliberation. ONLY triggers for premature unanimous agreement (before round 3).
"""

import logging
from typing import Any, Literal

from bo1.graph.state import DeliberationGraphState

logger = logging.getLogger(__name__)


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
    from bo1.models.contribution import ContributionMessage, ContributionType

    logger.info("moderator_intervene_node: Moderator intervening for premature consensus")

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
    from bo1.graph.utils import ensure_metrics, track_accumulated_cost

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
