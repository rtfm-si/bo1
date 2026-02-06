"""Vote node: Collects recommendations from all personas."""

import logging
import time
from typing import Any

from bo1.graph.nodes.utils import emit_node_duration
from bo1.graph.state import (
    DeliberationGraphState,
    get_core_state,
    get_problem_state,
)
from bo1.graph.utils import ensure_metrics, track_aggregated_cost
from bo1.models.state import DeliberationPhase
from bo1.utils.deliberation_logger import get_deliberation_logger

logger = logging.getLogger(__name__)


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

    _start_time = time.perf_counter()

    # Use nested state accessors for grouped field access
    core_state = get_core_state(state)
    problem_state = get_problem_state(state)

    session_id = core_state.get("session_id")
    user_id = core_state.get("user_id")
    dlog = get_deliberation_logger(session_id, user_id, "vote_node")
    dlog.info("Starting recommendation collection phase")

    # Create broker for LLM calls
    broker = PromptBroker()

    # Collect recommendations from all personas with v2 state
    recommendations, llm_responses = await collect_recommendations(state=state, broker=broker)

    # Track cost in metrics
    metrics = ensure_metrics(state)
    track_aggregated_cost(metrics, "voting", llm_responses)

    rec_cost = sum(r.cost_total for r in llm_responses)

    dlog.info(
        "Recommendations collected",
        recommendations=len(recommendations),
        cost=f"${rec_cost:.4f}",
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
    emit_node_duration("vote_node", (time.perf_counter() - _start_time) * 1000)
    return {
        "votes": recommendations_dicts,
        "recommendations": recommendations_dicts,
        "phase": DeliberationPhase.VOTING,
        "metrics": metrics,
        "current_node": "vote",
        "sub_problem_index": problem_state.get(
            "sub_problem_index", 0
        ),  # Preserve sub_problem_index
    }
