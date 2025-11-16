"""Cost analytics and reporting for deliberation sessions.

This module provides functions to analyze and export cost breakdowns
by phase, enabling visibility into where deliberation costs are incurred.
"""

import csv
import json
import logging
from pathlib import Path
from typing import Any

from bo1.graph.state import DeliberationGraphState

logger = logging.getLogger(__name__)


def get_phase_costs(state: DeliberationGraphState) -> dict[str, float]:
    """Extract phase costs from deliberation state.

    Args:
        state: Current deliberation graph state

    Returns:
        Dictionary mapping phase names to costs (USD)

    Example:
        >>> costs = get_phase_costs(state)
        >>> print(costs["problem_decomposition"])
        0.0012
    """
    metrics = state.get("metrics")
    if metrics is None:
        return {}

    # Handle both DeliberationMetrics object and dict
    if hasattr(metrics, "phase_costs"):
        return dict(metrics.phase_costs)
    elif isinstance(metrics, dict):
        return dict(metrics.get("phase_costs", {}))
    else:
        return {}


def calculate_cost_breakdown(
    state: DeliberationGraphState,
) -> list[dict[str, Any]]:
    """Calculate cost breakdown with percentages and metadata.

    Args:
        state: Current deliberation graph state

    Returns:
        List of phase cost records with:
        - phase: Phase name
        - cost: Cost in USD
        - percentage: Percentage of total cost
        - tokens: Token count (if available)

    Example:
        >>> breakdown = calculate_cost_breakdown(state)
        >>> for item in breakdown:
        ...     print(f"{item['phase']}: ${item['cost']:.4f} ({item['percentage']:.1f}%)")
    """
    metrics = state.get("metrics")
    if metrics is None:
        return []

    # Handle both DeliberationMetrics object and dict
    if hasattr(metrics, "phase_costs"):
        phase_costs = dict(metrics.phase_costs)
        total_cost = metrics.total_cost
    elif isinstance(metrics, dict):
        phase_costs = dict(metrics.get("phase_costs", {}))
        total_cost = metrics.get("total_cost", 0.0)
    else:
        return []

    if total_cost == 0:
        return []

    # Build breakdown records
    breakdown = []
    for phase, cost in phase_costs.items():
        percentage = (cost / total_cost * 100) if total_cost > 0 else 0.0
        breakdown.append(
            {
                "phase": phase,
                "cost": cost,
                "percentage": percentage,
                "tokens": None,  # TODO: Track per-phase tokens
            }
        )

    # Sort by cost descending - cast to float for sorting
    breakdown.sort(
        key=lambda x: float(x["cost"]) if x.get("cost") is not None else 0.0,  # type: ignore[arg-type]
        reverse=True,
    )

    return breakdown


def export_phase_metrics_csv(state: DeliberationGraphState, output_path: str | Path) -> None:
    """Export phase metrics to CSV file.

    Args:
        state: Current deliberation graph state
        output_path: Path to output CSV file

    Example:
        >>> export_phase_metrics_csv(state, "exports/session_123_costs.csv")
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    breakdown = calculate_cost_breakdown(state)

    with output_path.open("w", newline="") as csvfile:
        fieldnames = ["phase", "cost", "percentage", "tokens"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for record in breakdown:
            writer.writerow(record)

    logger.info(f"Phase metrics exported to CSV: {output_path}")


def export_phase_metrics_json(state: DeliberationGraphState, output_path: str | Path) -> None:
    """Export phase metrics to JSON file for archival.

    Includes full session metadata in addition to phase costs.

    Args:
        state: Current deliberation graph state
        output_path: Path to output JSON file

    Example:
        >>> export_phase_metrics_json(state, "exports/session_123_costs.json")
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metrics = state.get("metrics")
    if metrics is None:
        metrics_dict = {}
    elif hasattr(metrics, "model_dump"):
        metrics_dict = metrics.model_dump()
    elif isinstance(metrics, dict):
        metrics_dict = dict(metrics)
    else:
        metrics_dict = {}

    # Build export data
    export_data = {
        "session_id": state.get("session_id", "unknown"),
        "total_cost": metrics_dict.get("total_cost", 0.0),
        "total_tokens": metrics_dict.get("total_tokens", 0),
        "round_number": state.get("round_number", 0),
        "max_rounds": state.get("max_rounds", 0),
        "phase_costs": dict(metrics_dict.get("phase_costs", {})),
        "breakdown": calculate_cost_breakdown(state),
    }

    with output_path.open("w") as jsonfile:
        json.dump(export_data, jsonfile, indent=2)

    logger.info(f"Phase metrics exported to JSON: {output_path}")


def get_most_expensive_phases(
    state: DeliberationGraphState, top_n: int = 3
) -> list[tuple[str, float]]:
    """Get the N most expensive phases.

    Args:
        state: Current deliberation graph state
        top_n: Number of top phases to return

    Returns:
        List of (phase_name, cost) tuples, sorted by cost descending

    Example:
        >>> top_phases = get_most_expensive_phases(state, top_n=3)
        >>> for phase, cost in top_phases:
        ...     print(f"{phase}: ${cost:.4f}")
    """
    breakdown = calculate_cost_breakdown(state)
    return [(item["phase"], item["cost"]) for item in breakdown[:top_n]]


def get_total_deliberation_cost(state: DeliberationGraphState) -> float:
    """Get total deliberation cost from state.

    Args:
        state: Current deliberation graph state

    Returns:
        Total cost in USD

    Example:
        >>> cost = get_total_deliberation_cost(state)
        >>> print(f"Total: ${cost:.4f}")
    """
    metrics = state.get("metrics")
    if metrics is None:
        return 0.0

    # Handle both DeliberationMetrics object and dict
    if hasattr(metrics, "total_cost"):
        return metrics.total_cost
    elif isinstance(metrics, dict):
        return metrics.get("total_cost", 0.0)
    else:
        return 0.0
