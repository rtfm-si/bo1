"""Data analysis node.

This module contains the data_analysis_node function that executes
dataset analysis requested by the facilitator.
"""

import logging
from typing import Any

from bo1.graph.nodes.utils import log_with_session
from bo1.graph.state import (
    DeliberationGraphState,
    get_core_state,
    get_data_state,
    get_phase_state,
    get_problem_state,
)

logger = logging.getLogger(__name__)


async def data_analysis_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Execute dataset analysis requested by facilitator.

    Flow:
    1. Extract dataset_id and analysis_questions from facilitator decision
    2. Verify dataset is in attached_datasets
    3. Call DataAnalysisAgent.analyze_dataset()
    4. Add results to data_analysis_results state field
    5. Clear facilitator_decision to prevent loops

    Args:
        state: Current graph state

    Returns:
        State updates with analysis results
    """
    from bo1.agents.data_analyst import DataAnalysisAgent, DataAnalysisError

    # Use nested state accessors for grouped field access
    core_state = get_core_state(state)
    data_state = get_data_state(state)
    problem_state = get_problem_state(state)
    phase_state = get_phase_state(state)

    session_id = core_state.get("session_id")
    request_id = core_state.get("request_id")
    facilitator_decision = state.get("facilitator_decision")  # ephemeral - direct access

    if not facilitator_decision:
        log_with_session(
            logger,
            logging.WARNING,
            session_id,
            "[DATA_ANALYSIS] No facilitator decision found - skipping analysis",
            request_id=request_id,
        )
        return {
            "facilitator_decision": None,
            "current_node": "data_analysis",
        }

    # Extract analysis parameters
    dataset_id = facilitator_decision.get("dataset_id")
    analysis_questions = facilitator_decision.get("analysis_questions", [])

    if not dataset_id:
        logger.warning("[DATA_ANALYSIS] No dataset_id in facilitator decision")
        return {
            "facilitator_decision": None,
            "current_node": "data_analysis",
        }

    if not analysis_questions:
        # Generate default analysis question from reasoning
        reasoning = facilitator_decision.get("reasoning", "")
        analysis_questions = [f"Analyze data relevant to: {reasoning[:200]}"]
        logger.info(
            f"[DATA_ANALYSIS] No explicit questions, using reasoning: {analysis_questions[0][:50]}..."
        )

    # Verify dataset is attached to session
    attached_datasets = data_state.get("attached_datasets", [])
    if dataset_id not in attached_datasets:
        logger.warning(
            f"[DATA_ANALYSIS] Dataset {dataset_id} not in attached_datasets: {attached_datasets}"
        )
        return {
            "facilitator_decision": None,
            "current_node": "data_analysis",
            "data_analysis_results": data_state.get("data_analysis_results", [])
            + [
                {
                    "dataset_id": dataset_id,
                    "error": "Dataset not attached to session",
                    "questions": analysis_questions,
                    "results": [],
                    "round": phase_state.get("round_number", 0),
                }
            ],
        }

    logger.info(
        f"[DATA_ANALYSIS] Analyzing dataset {dataset_id} with {len(analysis_questions)} questions"
    )

    # Get user_id and auth context
    user_id = core_state.get("user_id") or ""

    # Initialize agent and perform analysis
    agent = DataAnalysisAgent()

    try:
        results = await agent.analyze_dataset(
            dataset_id=dataset_id,
            questions=analysis_questions,
            user_id=user_id,
            auth_token=None,  # Internal calls don't need auth token
        )
    except DataAnalysisError as e:
        sp_idx = problem_state.get("sub_problem_index")
        round_num = phase_state.get("round_number")
        log_with_session(
            logger,
            logging.ERROR,
            session_id,
            f"[DATA_ANALYSIS] Analysis failed: {e}",
            request_id=request_id,
            sub_problem_index=sp_idx if isinstance(sp_idx, int) else None,
            round_number=round_num if isinstance(round_num, int) else None,
        )
        results = [
            {
                "question": q,
                "error": str(e),
                "query_result": None,
                "chart_result": None,
                "cost": 0.0,
            }
            for q in analysis_questions
        ]

    # Calculate total cost
    total_cost = sum(r.get("cost", 0.0) for r in results)

    # Add to state
    data_analysis_results_obj = data_state.get("data_analysis_results", [])
    data_analysis_results = (
        list(data_analysis_results_obj) if isinstance(data_analysis_results_obj, list) else []
    )

    data_analysis_results.append(
        {
            "dataset_id": dataset_id,
            "questions": analysis_questions,
            "results": results,
            "cost": total_cost,
            "round": phase_state.get("round_number", 0),
        }
    )

    logger.info(f"[DATA_ANALYSIS] Complete - {len(results)} results, cost: ${total_cost:.4f}")

    return {
        "data_analysis_results": data_analysis_results,
        "facilitator_decision": None,  # Clear to prevent loops
        "current_node": "data_analysis",
        "sub_problem_index": problem_state.get("sub_problem_index", 0),
    }
