"""Utility functions for graph node operations.

This module consolidates common patterns used across graph nodes to reduce
code duplication and improve maintainability.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bo1.graph.state import DeliberationGraphState
    from bo1.llm.response import LLMResponse
    from bo1.models.state import DeliberationMetrics


def ensure_metrics(state: "DeliberationGraphState") -> "DeliberationMetrics":
    """Get or create metrics from state.

    This helper eliminates the repeated pattern of checking if metrics
    exists in state and creating a new DeliberationMetrics object if not.

    Handles checkpoint deserialization where metrics may be a dict.

    Args:
        state: Current graph state

    Returns:
        DeliberationMetrics object (existing or newly created)

    Example:
        >>> metrics = ensure_metrics(state)
        >>> metrics.total_cost += 0.05
    """
    from bo1.models.state import DeliberationMetrics

    metrics = state.get("metrics")
    if metrics is None:
        metrics = DeliberationMetrics()
    elif isinstance(metrics, dict):
        # Handle checkpoint deserialization - reconstruct from dict
        metrics = DeliberationMetrics(
            total_cost=metrics.get("total_cost", 0.0),
            total_tokens=metrics.get("total_tokens", 0),
            phase_costs=metrics.get("phase_costs", {}),
            start_time=metrics.get("start_time"),
            end_time=metrics.get("end_time"),
        )
    return metrics


def track_phase_cost(
    metrics: "DeliberationMetrics",
    phase_name: str,
    response: "LLMResponse | None",
) -> None:
    """Track cost for a single LLM response (replaces existing phase cost).

    Use this when a phase has a single LLM call (e.g., decomposition, selection).
    This REPLACES any existing cost for the phase.

    Args:
        metrics: DeliberationMetrics object to update
        phase_name: Name of the phase (e.g., "problem_decomposition")
        response: LLMResponse containing cost information (or None for $0 cost)

    Example:
        >>> metrics = ensure_metrics(state)
        >>> track_phase_cost(metrics, "problem_decomposition", response)
        >>> # For phases with no LLM calls
        >>> track_phase_cost(metrics, "context_collection", None)
    """
    if response is None:
        # No LLM call = $0 cost
        metrics.phase_costs[phase_name] = 0.0
    else:
        metrics.phase_costs[phase_name] = response.cost_total
        metrics.total_cost += response.cost_total
        metrics.total_tokens += response.total_tokens


def track_accumulated_cost(
    metrics: "DeliberationMetrics",
    phase_name: str,
    response: "LLMResponse",
) -> None:
    """Track cost that accumulates across multiple calls to same phase.

    Use this when a phase may have multiple sequential LLM calls (e.g.,
    facilitator_decision called multiple times). This ADDS to existing cost.

    Args:
        metrics: DeliberationMetrics object to update
        phase_name: Name of the phase (e.g., "facilitator_decision")
        response: LLMResponse containing cost information

    Example:
        >>> metrics = ensure_metrics(state)
        >>> # First call
        >>> track_accumulated_cost(metrics, "facilitator_decision", response1)
        >>> # Second call - adds to existing
        >>> track_accumulated_cost(metrics, "facilitator_decision", response2)
    """
    current = metrics.phase_costs.get(phase_name, 0.0)
    metrics.phase_costs[phase_name] = current + response.cost_total
    metrics.total_cost += response.cost_total
    metrics.total_tokens += response.total_tokens


def track_aggregated_cost(
    metrics: "DeliberationMetrics",
    phase_name: str,
    responses: list["LLMResponse"],
) -> None:
    """Track cost from multiple parallel LLM responses.

    Use this when a phase has multiple parallel LLM calls (e.g., initial round
    where all personas contribute simultaneously). This aggregates all costs
    and REPLACES the phase cost.

    Args:
        metrics: DeliberationMetrics object to update
        phase_name: Name of the phase (e.g., "initial_round")
        responses: List of LLMResponse objects from parallel calls

    Example:
        >>> metrics = ensure_metrics(state)
        >>> responses = [response1, response2, response3]
        >>> track_aggregated_cost(metrics, "initial_round", responses)
    """
    total_cost = sum(r.cost_total for r in responses)
    total_tokens = sum(r.total_tokens for r in responses)
    metrics.phase_costs[phase_name] = total_cost
    metrics.total_cost += total_cost
    metrics.total_tokens += total_tokens


def calculate_problem_complexity(state: "DeliberationGraphState") -> float:
    """Calculate overall problem complexity score (0-1) from state.

    Factors:
    - Number of sub-problems (1=simple, 3+=complex)
    - Average sub-problem complexity scores (1-10)
    - Dependency depth (batch count from execution_batches)

    Args:
        state: Current graph state with problem/sub-problems

    Returns:
        Complexity score between 0.0 (simple) and 1.0 (very complex)

    Example:
        >>> complexity = calculate_problem_complexity(state)
        >>> target_experts = calculate_target_expert_count(complexity)
    """
    problem = state.get("problem")
    if not problem:
        return 0.5  # Default middle complexity

    # Handle both dict (from checkpoint) and Problem object
    if isinstance(problem, dict):
        sub_problems = problem.get("sub_problems", [])
    else:
        sub_problems = problem.sub_problems or []

    if not sub_problems:
        return 0.3  # Single implicit problem = low complexity

    # Factor 1: Number of sub-problems (normalized: 1->0.2, 5->1.0)
    num_sub_problems = len(sub_problems)
    num_factor = min((num_sub_problems - 1) / 4, 1.0) * 0.4  # 0-0.4 range

    # Factor 2: Average complexity score (normalized: 1-10 -> 0-1)
    complexity_scores = []
    for sp in sub_problems:
        if isinstance(sp, dict):
            score = sp.get("complexity_score", 5)
        else:
            score = getattr(sp, "complexity_score", 5)
        complexity_scores.append(score)

    avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 5
    complexity_factor = (avg_complexity - 1) / 9 * 0.4  # 0-0.4 range

    # Factor 3: Dependency depth (from execution_batches if available)
    execution_batches = state.get("execution_batches", [])
    num_batches = len(execution_batches) if execution_batches else 1
    batch_factor = min((num_batches - 1) / 3, 1.0) * 0.2  # 0-0.2 range

    # Combine factors (weights sum to 1.0)
    total_complexity = num_factor + complexity_factor + batch_factor

    return min(max(total_complexity, 0.0), 1.0)  # Clamp to 0-1


def calculate_target_expert_count(
    complexity_score: float,
    min_experts: int = 3,
    max_experts: int = 5,
    threshold_simple: float = 0.4,
) -> int:
    """Calculate target number of experts based on problem complexity.

    Args:
        complexity_score: Problem complexity (0-1)
        min_experts: Minimum experts for simple problems (default: 3)
        max_experts: Maximum experts for complex problems (default: 5)
        threshold_simple: Complexity threshold for using min_experts (default: 0.4)

    Returns:
        Target expert count (integer between min_experts and max_experts)

    Example:
        >>> calculate_target_expert_count(0.3)  # Simple
        3
        >>> calculate_target_expert_count(0.7)  # Complex
        4
        >>> calculate_target_expert_count(0.9)  # Very complex
        5
    """
    if complexity_score < threshold_simple:
        return min_experts

    # Linear interpolation from min to max based on complexity
    # For complexity 0.4 -> min, complexity 1.0 -> max
    range_start = threshold_simple
    range_end = 1.0
    position = (complexity_score - range_start) / (range_end - range_start)

    expert_count = min_experts + position * (max_experts - min_experts)
    return int(round(expert_count))
