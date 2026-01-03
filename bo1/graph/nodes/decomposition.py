"""Problem decomposition node.

This module contains the decompose_node function that breaks down
complex problems into manageable sub-problems and assesses complexity.
"""

import logging
import time
from typing import Any

from bo1.agents.decomposer import DecomposerAgent
from bo1.graph.nodes.utils import emit_node_duration, log_with_session
from bo1.graph.state import (
    DeliberationGraphState,
    get_core_state,
)
from bo1.graph.utils import ensure_metrics, track_phase_cost
from bo1.models.problem import SubProblem
from bo1.models.state import DeliberationPhase
from bo1.utils.comparison_detector import ComparisonDetector
from bo1.utils.deliberation_logger import get_deliberation_logger
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
    _start_time = time.perf_counter()

    # Use nested state accessors for grouped field access
    core_state = get_core_state(state)

    session_id = core_state.get("session_id")
    user_id = core_state.get("user_id")
    request_id = core_state.get("request_id")
    dlog = get_deliberation_logger(session_id, user_id, "decompose_node")
    dlog.info("Starting problem decomposition")

    log_with_session(
        logger, logging.INFO, session_id, "decompose_node: Starting", request_id=request_id
    )

    # Create decomposer agent
    decomposer = DecomposerAgent()

    # Get problem from state
    problem = state["problem"]

    # PROACTIVE RESEARCH: Detect comparison questions ("X vs Y")
    # If detected, generate research queries that will be executed before deliberation
    comparison_result = ComparisonDetector.detect(
        problem_statement=problem.description,
        context=problem.context,
    )

    pending_research_queries: list[dict[str, str]] = []
    if comparison_result.is_comparison:
        dlog.info(
            "Detected comparison question",
            comparison_type=comparison_result.comparison_type,
            options=str(comparison_result.options),
        )
        pending_research_queries = comparison_result.research_queries
        dlog.info("Generated proactive research queries", queries=len(pending_research_queries))

    # AUDIT FIX (Priority 5, Task 5.2): Determine complexity-based limits BEFORE decomposition
    # This helps the LLM understand expected decomposition count
    # Rough initial complexity estimate based on problem length and keywords
    problem_text = problem.description + " " + (problem.context or "")
    problem_length = len(problem_text.split())

    # Simple heuristic for initial complexity estimate
    if problem_length < 20:
        estimated_complexity = 3  # Simple, likely atomic
    elif problem_length < 50:
        estimated_complexity = 5  # Moderate
    elif problem_length < 100:
        estimated_complexity = 7  # Complex
    else:
        estimated_complexity = 8  # Very complex

    # Strategic decision keywords indicate higher complexity
    strategic_keywords = [
        "pivot",
        "acquisition",
        "expansion",
        "founder",
        "co-founder",
        "series",
        "funding",
    ]
    if any(keyword in problem_text.lower() for keyword in strategic_keywords):
        estimated_complexity = min(9, estimated_complexity + 2)

    log_with_session(
        logger,
        logging.INFO,
        session_id,
        f"decompose_node: Initial complexity estimate = {estimated_complexity} "
        f"(problem length: {problem_length} words)",
    )

    # Call decomposer with complexity hint in constraints
    response = await decomposer.decompose_problem(
        problem_description=problem.description,
        context=problem.context,
        constraints=[
            f"Estimated complexity: {estimated_complexity}/10",
            "Target: Minimize sub-problems (prefer 1-3, avoid 4+)",
        ],
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

    # AUDIT FIX (Priority 5, Task 5.2): Enforce complexity-based limits
    # Truncate if LLM generated too many sub-problems (Quality > Quantity)
    max_subproblems_allowed = 4  # Hard cap based on audit findings (avg was 4.2)

    if len(sub_problems) > max_subproblems_allowed:
        log_with_session(
            logger,
            logging.WARNING,
            session_id,
            f"decompose_node: Truncating {len(sub_problems)} sub-problems to {max_subproblems_allowed} "
            f"(audit finding: too many sub-problems reduces quality)",
        )
        # Keep the most important ones (highest complexity or first N)
        sub_problems = sub_problems[:max_subproblems_allowed]

    log_with_session(
        logger,
        logging.INFO,
        session_id,
        f"decompose_node: Created {len(sub_problems)} sub-problems "
        f"(target: 1-3, max: {max_subproblems_allowed})",
    )

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

    log_with_session(
        logger,
        logging.INFO,
        session_id,
        f"decompose_node: Complete - {len(sub_problems)} sub-problems, "
        f"complexity={metrics.complexity_score:.2f}, "
        f"recommended_rounds={metrics.recommended_rounds}, "
        f"recommended_experts={metrics.recommended_experts} "
        f"(cost: ${response.cost_total + complexity_response.cost_total:.4f})",
    )

    # Return state updates with adaptive max_rounds
    state_updates: dict[str, Any] = {
        "problem": problem,
        "current_sub_problem": sub_problems[0] if sub_problems else None,
        "phase": DeliberationPhase.DECOMPOSITION,
        "metrics": metrics,
        "max_rounds": metrics.recommended_rounds,  # Adaptive based on complexity
        "current_node": "decompose",
    }

    # PROACTIVE RESEARCH: Include pending research queries if comparison detected
    if pending_research_queries:
        state_updates["pending_research_queries"] = pending_research_queries
        state_updates["comparison_detected"] = True
        state_updates["comparison_options"] = comparison_result.options
        state_updates["comparison_type"] = comparison_result.comparison_type
        log_with_session(
            logger,
            logging.INFO,
            session_id,
            f"decompose_node: Added {len(pending_research_queries)} research queries to state "
            f"for comparison: {comparison_result.options}",
        )

    emit_node_duration("decompose_node", (time.perf_counter() - _start_time) * 1000)
    return state_updates
