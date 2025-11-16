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

    Args:
        state: Current graph state

    Returns:
        DeliberationMetrics object (existing or newly created)

    Example:
        >>> metrics = ensure_metrics(state)
        >>> metrics.total_cost += 0.05
    """
    metrics = state.get("metrics")
    if metrics is None:
        from bo1.models.state import DeliberationMetrics

        metrics = DeliberationMetrics()
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
