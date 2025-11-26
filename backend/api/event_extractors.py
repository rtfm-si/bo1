"""Generic event data extraction framework.

This module provides a declarative framework for extracting event data from
LangGraph node outputs. It eliminates duplication across event extractors by
providing reusable transformation functions and a configuration-driven approach.

Benefits:
- Single source of truth for extraction patterns
- Easier to test extraction logic in isolation
- Consistent error handling across all extractors
- Simple to add new event types (just add config)
"""

from collections.abc import Callable
from typing import Any, TypedDict

from bo1.utils.singleton import singleton


class FieldExtractor(TypedDict, total=False):
    """Configuration for extracting a field from event output.

    Attributes:
        source_field: Key in output dict to extract from
        target_field: Key in result dict to store value
        transform: Optional function to transform extracted value
        default: Default value if source field missing
        required: Whether field is required (raises error if missing)
    """

    source_field: str
    target_field: str
    transform: Callable[[Any], Any]
    default: Any
    required: bool


def extract_event_data(
    output: dict[str, Any],
    extractors: list[FieldExtractor],
) -> dict[str, Any]:
    """Extract event data using field extractor configurations.

    Args:
        output: Raw node output dictionary
        extractors: List of field extraction configs

    Returns:
        Extracted event data dictionary

    Raises:
        KeyError: If required field is missing

    Example:
        extractors = [
            {
                "source_field": "problem",
                "target_field": "sub_problems",
                "transform": extract_sub_problems,
            },
        ]
        data = extract_event_data(output, extractors)
    """
    result = {}

    for extractor in extractors:
        source = extractor["source_field"]
        target = extractor["target_field"]
        required = extractor.get("required", False)
        default = extractor.get("default")

        # Extract value
        value = output.get(source, default)

        # Check required
        if required and value is None:
            raise KeyError(f"Required field '{source}' not found in output")

        # Apply transformation if provided
        if transform := extractor.get("transform"):
            value = transform(value)

        result[target] = value

    return result


# ==============================================================================
# Transformation Functions - Common patterns for data extraction
# ==============================================================================


def to_dict_list(items: list[Any]) -> list[dict[str, Any]]:
    """Convert list of Pydantic models to list of dicts.

    Handles both Pydantic models (.model_dump()) and plain dicts.
    """
    return [item.model_dump() if hasattr(item, "model_dump") else item for item in items]


def get_field_safe(obj: Any, field: str, default: Any = None) -> Any:
    """Safely get field from object or dict.

    Works with both Pydantic models (via getattr) and dicts (via .get()).
    """
    if hasattr(obj, field):
        return getattr(obj, field)
    if isinstance(obj, dict):
        return obj.get(field, default)
    return default


def extract_sub_problems(problem: Any) -> list[dict[str, Any]]:
    """Extract sub-problems from Problem object.

    Converts SubProblem objects to dicts with essential fields.
    """
    from bo1.models.problem import SubProblem

    if not problem:
        return []

    sub_problems = get_field_safe(problem, "sub_problems", [])
    result = []

    for sp in sub_problems:
        if isinstance(sp, dict):
            # Already a dict, pass through
            result.append(sp)
        elif isinstance(sp, SubProblem):
            # Pydantic model, extract fields
            result.append(
                {
                    "id": sp.id,
                    "goal": sp.goal,
                    "rationale": getattr(sp, "rationale", ""),
                    "complexity_score": sp.complexity_score,
                    "dependencies": sp.dependencies,
                }
            )
        elif hasattr(sp, "id") and hasattr(sp, "goal"):
            # Duck typing - any object with required attributes
            result.append(
                {
                    "id": getattr(sp, "id", ""),
                    "goal": getattr(sp, "goal", ""),
                    "rationale": getattr(sp, "rationale", ""),
                    "complexity_score": getattr(sp, "complexity_score", 0),
                    "dependencies": getattr(sp, "dependencies", []),
                }
            )

    return result


def extract_persona_codes(personas: list[Any]) -> list[str]:
    """Extract persona codes from persona objects.

    Works with both PersonaProfile objects and dicts.
    """
    return [get_field_safe(p, "code", "unknown") for p in personas]


def extract_metrics_field(metrics: Any, field: str, default: Any = 0.0) -> Any:
    """Extract specific field from metrics object or dict.

    Handles both Pydantic MetricsSnapshot objects and plain dicts.
    """
    if not metrics:
        return default

    if hasattr(metrics, field):
        value = getattr(metrics, field)
        return value if value is not None else default

    if isinstance(metrics, dict):
        return metrics.get(field, default)

    return default


def extract_facilitator_decision(decision: dict[str, Any]) -> dict[str, Any]:
    """Extract facilitator decision data with optional fields."""
    if not decision:
        return {}

    data = {
        "action": decision.get("action", ""),
        "reasoning": decision.get("reasoning", ""),
    }

    # Add optional fields if present
    if next_speaker := decision.get("next_speaker"):
        data["next_speaker"] = next_speaker
    if moderator_type := decision.get("moderator_type"):
        data["moderator_type"] = moderator_type
    if research_query := decision.get("research_query"):
        data["research_query"] = research_query

    return data


def extract_formatted_votes(votes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format votes for compact display."""
    return [
        {
            "persona_code": vote.get("persona_code", ""),
            "persona_name": vote.get("persona_name", ""),
            "recommendation": vote.get("recommendation", ""),
            "confidence": vote.get("confidence", 0.0),
            "reasoning": vote.get("reasoning", ""),
            "conditions": vote.get("conditions", []),
        }
        for vote in votes
    ]


def calculate_consensus_level(votes: list[dict[str, Any]]) -> tuple[str, float]:
    """Calculate consensus level and average confidence from votes."""
    if not votes:
        return ("unknown", 0.0)

    avg_confidence = sum(v.get("confidence", 0.0) for v in votes) / len(votes)

    if avg_confidence >= 0.8:
        consensus_level = "strong"
    elif avg_confidence >= 0.6:
        consensus_level = "moderate"
    else:
        consensus_level = "weak"

    return (consensus_level, avg_confidence)


def extract_subproblem_info(output: dict[str, Any]) -> dict[str, Any]:
    """Extract sub-problem started event data.

    Returns empty dict if not a multi-sub-problem scenario.
    """
    sub_problem_index = output.get("sub_problem_index", 0)
    current_sub_problem = output.get("current_sub_problem")
    problem = output.get("problem")

    # Only return data if this is a multi-sub-problem scenario
    if not (problem and hasattr(problem, "sub_problems") and len(problem.sub_problems) > 1):
        return {}

    if not current_sub_problem:
        return {}

    return {
        "sub_problem_index": sub_problem_index,
        "sub_problem_id": get_field_safe(current_sub_problem, "id", ""),
        "goal": get_field_safe(current_sub_problem, "goal", ""),
        "total_sub_problems": len(problem.sub_problems),
    }


def extract_subproblem_result(result: Any) -> dict[str, Any]:
    """Extract single sub-problem result data."""
    return {
        "sub_problem_id": get_field_safe(result, "sub_problem_id", ""),
        "sub_problem_goal": get_field_safe(result, "sub_problem_goal", ""),
        "cost": get_field_safe(result, "cost", 0.0),
        "duration_seconds": get_field_safe(result, "duration_seconds", 0.0),
        "expert_panel": get_field_safe(result, "expert_panel", []),
        "contribution_count": get_field_safe(result, "contribution_count", 0),
    }


# ==============================================================================
# Extractor Configurations - Declarative definitions for each event type
# ==============================================================================

# Note: These configurations define how to extract data for each event type.
# Each configuration is a list of FieldExtractor dicts that specify:
# - source_field: Where to get the data from output dict
# - target_field: Where to store it in the result dict
# - transform: Optional function to transform the value
# - default: Optional default value if source_field is missing


DECOMPOSITION_EXTRACTORS: list[FieldExtractor] = [
    {
        "source_field": "problem",
        "target_field": "sub_problems",
        "transform": extract_sub_problems,
        "default": [],
    },
    {
        "source_field": "problem",
        "target_field": "count",
        "transform": lambda p: len(get_field_safe(p, "sub_problems", [])),
        "default": 0,
    },
]


PERSONA_SELECTION_EXTRACTORS: list[FieldExtractor] = [
    {
        "source_field": "personas",
        "target_field": "personas",
        "transform": extract_persona_codes,
        "default": [],
    },
    {
        "source_field": "personas",
        "target_field": "count",
        "transform": lambda p: len(p) if p else 0,
        "default": 0,
    },
    {
        "source_field": "sub_problem_index",
        "target_field": "sub_problem_index",
        "default": 0,
    },
]


def _create_facilitator_decision_extractors() -> list[FieldExtractor]:
    """Create facilitator decision extractors with complex logic."""

    def extract_full_decision(output: dict[str, Any]) -> dict[str, Any]:
        """Extract full facilitator decision with all fields."""
        decision = output.get("facilitator_decision")
        round_number = output.get("round_number", 1)
        sub_problem_index = output.get("sub_problem_index", 0)

        if not decision:
            return {}

        result = extract_facilitator_decision(decision)
        result["round"] = round_number
        result["sub_problem_index"] = sub_problem_index
        return result

    # Return a single extractor that handles all fields
    return [
        {
            "source_field": "__root__",
            "target_field": "__root__",
            "transform": extract_full_decision,
        }
    ]


# Special case: facilitator decision needs access to full output
FACILITATOR_DECISION_EXTRACTORS = _create_facilitator_decision_extractors()


def _create_moderator_intervention_extractors() -> list[FieldExtractor]:
    """Create moderator intervention extractors."""

    def extract_moderator_data(output: dict[str, Any]) -> dict[str, Any]:
        """Extract moderator intervention data from contributions."""
        contributions = output.get("contributions", [])
        round_number = output.get("round_number", 1)
        sub_problem_index = output.get("sub_problem_index", 0)

        if not contributions:
            return {}

        contrib = contributions[-1]
        return {
            "moderator_type": contrib.get("persona_code", "moderator"),
            "content": contrib.get("content", ""),
            "trigger_reason": "Facilitator requested intervention",
            "round": round_number,
            "sub_problem_index": sub_problem_index,
        }

    return [
        {
            "source_field": "__root__",
            "target_field": "__root__",
            "transform": extract_moderator_data,
        }
    ]


MODERATOR_INTERVENTION_EXTRACTORS = _create_moderator_intervention_extractors()


CONVERGENCE_EXTRACTORS: list[FieldExtractor] = [
    {
        "source_field": "should_stop",
        "target_field": "converged",
        "default": False,
    },
    {
        "source_field": "should_stop",
        "target_field": "should_stop",
        "default": False,
    },
    {
        "source_field": "stop_reason",
        "target_field": "stop_reason",
        "default": None,
    },
    {
        "source_field": "metrics",
        "target_field": "score",
        "transform": lambda m: extract_metrics_field(m, "convergence_score", 0.0),
        "default": 0.0,
    },
    # Quality metrics (Meeting Quality Enhancement)
    {
        "source_field": "metrics",
        "target_field": "exploration_score",
        "transform": lambda m: extract_metrics_field(m, "exploration_score", None),
        "default": None,
    },
    {
        "source_field": "metrics",
        "target_field": "focus_score",
        "transform": lambda m: extract_metrics_field(m, "focus_score", None),
        "default": None,
    },
    {
        "source_field": "metrics",
        "target_field": "novelty_score",
        "transform": lambda m: extract_metrics_field(m, "novelty_score", None),
        "default": None,
    },
    {
        "source_field": "metrics",
        "target_field": "meeting_completeness_index",
        "transform": lambda m: extract_metrics_field(m, "meeting_completeness_index", None),
        "default": None,
    },
    {
        "source_field": "metrics",
        "target_field": "aspect_coverage",
        "transform": lambda m: (
            [a.model_dump() if hasattr(a, "model_dump") else a for a in m.aspect_coverage]
            if m and hasattr(m, "aspect_coverage") and m.aspect_coverage
            else []
        ),
        "default": [],
    },
    {
        "source_field": "facilitator_guidance",
        "target_field": "facilitator_guidance",
        "default": None,
    },
    {
        "source_field": "round_number",
        "target_field": "round",
        "default": 1,
    },
    {
        "source_field": "max_rounds",
        "target_field": "max_rounds",
        "default": 10,
    },
    {
        "source_field": "sub_problem_index",
        "target_field": "sub_problem_index",
        "default": 0,
    },
    {
        "source_field": "__constant__",
        "target_field": "threshold",
        "transform": lambda _: 0.85,
        "default": 0.85,
    },
    # Phase field (exploration/challenge/convergence)
    {
        "source_field": "current_phase",
        "target_field": "phase",
        "default": None,
    },
    # Additional quality metrics (conflict_score already handled above via novelty_score duplication)
    {
        "source_field": "metrics",
        "target_field": "conflict_score",
        "transform": lambda m: extract_metrics_field(m, "conflict_score", None),
        "default": None,
    },
    {
        "source_field": "metrics",
        "target_field": "drift_events",
        "transform": lambda m: extract_metrics_field(m, "drift_events", 0),
        "default": 0,
    },
]


def _create_voting_extractors() -> list[FieldExtractor]:
    """Create voting extractors with consensus calculation."""

    def extract_voting_data(output: dict[str, Any]) -> dict[str, Any]:
        """Extract voting data with consensus metrics."""
        votes = output.get("votes", [])
        sub_problem_index = output.get("sub_problem_index", 0)

        formatted_votes = extract_formatted_votes(votes)
        consensus_level, avg_confidence = calculate_consensus_level(votes)

        return {
            "votes": formatted_votes,
            "votes_count": len(votes),
            "consensus_level": consensus_level,
            "avg_confidence": avg_confidence,
            "sub_problem_index": sub_problem_index,
        }

    return [
        {
            "source_field": "__root__",
            "target_field": "__root__",
            "transform": extract_voting_data,
        }
    ]


VOTING_EXTRACTORS = _create_voting_extractors()


SYNTHESIS_EXTRACTORS: list[FieldExtractor] = [
    {
        "source_field": "synthesis",
        "target_field": "synthesis",
        "default": "",
    },
    {
        "source_field": "synthesis",
        "target_field": "word_count",
        "transform": lambda s: len(s.split()) if s else 0,
        "default": 0,
    },
    {
        "source_field": "sub_problem_index",
        "target_field": "sub_problem_index",
        "default": 0,
    },
]


META_SYNTHESIS_EXTRACTORS: list[FieldExtractor] = [
    {
        "source_field": "synthesis",
        "target_field": "synthesis",
        "default": "",
    },
    {
        "source_field": "synthesis",
        "target_field": "word_count",
        "transform": lambda s: len(s.split()) if s else 0,
        "default": 0,
    },
]


SUBPROBLEM_STARTED_EXTRACTORS: list[FieldExtractor] = [
    {
        "source_field": "__root__",
        "target_field": "__root__",
        "transform": extract_subproblem_info,
    }
]


def _create_subproblem_complete_extractors() -> list[FieldExtractor]:
    """Create sub-problem complete extractors."""

    def extract_completion_data(output: dict[str, Any]) -> dict[str, Any]:
        """Extract most recent sub-problem completion."""
        sub_problem_results = output.get("sub_problem_results", [])

        if not sub_problem_results:
            return {}

        # Get the most recently completed sub-problem result
        result = sub_problem_results[-1]
        result_data = extract_subproblem_result(result)
        completed_index = len(sub_problem_results) - 1
        result_data["sub_problem_index"] = completed_index

        return result_data

    return [
        {
            "source_field": "__root__",
            "target_field": "__root__",
            "transform": extract_completion_data,
        }
    ]


SUBPROBLEM_COMPLETE_EXTRACTORS = _create_subproblem_complete_extractors()


def _create_completion_extractors() -> list[FieldExtractor]:
    """Create final completion extractors."""

    def extract_final_data(output: dict[str, Any]) -> dict[str, Any]:
        """Extract final deliberation completion data."""
        metrics = output.get("metrics", {})
        total_cost = extract_metrics_field(metrics, "total_cost", 0.0)
        total_tokens = extract_metrics_field(metrics, "total_tokens", 0)

        round_number = output.get("round_number", 0)
        stop_reason = output.get("stop_reason", "completed")
        contributions = output.get("contributions", [])
        synthesis = output.get("synthesis", "")
        session_id = output.get("session_id", "")

        return {
            "session_id": session_id,
            "final_output": synthesis or "Deliberation complete",
            "total_cost": total_cost,
            "total_rounds": round_number,
            "total_contributions": len(contributions),
            "total_tokens": total_tokens,
            "duration_seconds": 0.0,  # TODO: Track duration
            "stop_reason": stop_reason,
        }

    return [
        {
            "source_field": "__root__",
            "target_field": "__root__",
            "transform": extract_final_data,
        }
    ]


COMPLETION_EXTRACTORS = _create_completion_extractors()


# ==============================================================================
# Special Extractor - handles output that spans entire dict
# ==============================================================================


def extract_with_root_transform(
    output: dict[str, Any],
    extractors: list[FieldExtractor],
) -> dict[str, Any]:
    """Special extractor for configurations that use __root__ transforms.

    These extractors need access to the full output dict, not individual fields.
    """
    if len(extractors) == 1 and extractors[0]["source_field"] == "__root__":
        transform = extractors[0].get("transform")
        if transform:
            return transform(output)

    # Fallback to regular extraction
    return extract_event_data(output, extractors)


# ==============================================================================
# Event Extractor Registry - Centralized registry for all event extractors
# ==============================================================================


class EventExtractorRegistry:
    """Central registry for event data extractors.

    Provides a single source of truth for all event type -> extractor mappings,
    eliminating the need for scattered import statements and manual function
    definitions in event_collector.py.

    Benefits:
    - Single registration point for all extractors
    - Automatic extractor function generation
    - Easy to add new event types (just call register())
    - Type-safe extractor lookup
    - Centralized documentation

    Examples:
        >>> registry = get_event_registry()
        >>> data = registry.extract("decomposition", output)
        >>> print(registry.get_event_types())
        ['decomposition', 'persona_selection', ...]
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._extractors: dict[str, list[FieldExtractor]] = {}

    def register(
        self,
        event_type: str,
        extractors: list[FieldExtractor] | Callable[[], list[FieldExtractor]],
    ) -> None:
        """Register extractors for an event type.

        Args:
            event_type: Event type name (e.g., 'decomposition', 'persona_selection')
            extractors: List of FieldExtractor configs, or factory function that returns them

        Examples:
            >>> registry = EventExtractorRegistry()
            >>> registry.register("decomposition", DECOMPOSITION_EXTRACTORS)
            >>> registry.register("facilitator_decision", _create_facilitator_decision_extractors)
        """
        if callable(extractors):
            # Factory function - call it to get extractors
            extractors = extractors()
        self._extractors[event_type] = extractors

    def get(self, event_type: str) -> list[FieldExtractor] | None:
        """Get extractors for event type.

        Args:
            event_type: Event type name

        Returns:
            List of FieldExtractor configs, or None if not registered
        """
        return self._extractors.get(event_type)

    def extract(self, event_type: str, output: dict[str, Any]) -> dict[str, Any]:
        """Extract data for event type.

        Args:
            event_type: Event type name
            output: Raw node output dictionary

        Returns:
            Extracted event data dictionary

        Raises:
            ValueError: If event type not registered

        Examples:
            >>> registry = get_event_registry()
            >>> data = registry.extract("decomposition", {"problem": {...}})
            >>> print(data["sub_problems"])
        """
        extractors = self.get(event_type)
        if extractors is None:
            raise ValueError(
                f"Unknown event type: {event_type}. "
                f"Registered types: {list(self._extractors.keys())}"
            )

        # Handle special __root__ extractors
        if extractors and extractors[0].get("source_field") == "__root__":
            return extract_with_root_transform(output, extractors)

        return extract_event_data(output, extractors)

    def get_event_types(self) -> list[str]:
        """Get list of all registered event types.

        Returns:
            List of event type names

        Examples:
            >>> registry = get_event_registry()
            >>> print(registry.get_event_types())
            ['decomposition', 'persona_selection', 'facilitator_decision', ...]
        """
        return list(self._extractors.keys())

    def is_registered(self, event_type: str) -> bool:
        """Check if event type is registered.

        Args:
            event_type: Event type name

        Returns:
            True if registered, False otherwise
        """
        return event_type in self._extractors


@singleton
def get_event_registry() -> EventExtractorRegistry:
    """Get or create global event extractor registry.

    This function uses the @singleton decorator to lazily initialize the registry
    on first call and register all standard event extractors.

    Returns:
        Singleton EventExtractorRegistry instance

    Examples:
        >>> registry = get_event_registry()
        >>> data = registry.extract("decomposition", output)

        >>> # For testing: reset singleton
        >>> get_event_registry.reset()  # type: ignore
        >>> new_registry = get_event_registry()
    """
    registry = EventExtractorRegistry()

    # Register all standard extractors
    registry.register("decomposition", DECOMPOSITION_EXTRACTORS)
    registry.register("persona_selection", PERSONA_SELECTION_EXTRACTORS)
    registry.register("facilitator_decision", _create_facilitator_decision_extractors)
    registry.register("moderator_intervention", _create_moderator_intervention_extractors)
    registry.register("convergence", CONVERGENCE_EXTRACTORS)
    registry.register("voting", _create_voting_extractors)
    registry.register("synthesis", SYNTHESIS_EXTRACTORS)
    registry.register("meta_synthesis", META_SYNTHESIS_EXTRACTORS)
    registry.register("subproblem_started", SUBPROBLEM_STARTED_EXTRACTORS)
    registry.register("subproblem_complete", _create_subproblem_complete_extractors)
    registry.register("completion", _create_completion_extractors)

    # Parallel architecture events (Day 38+)
    registry.register(
        "parallel_round_start",
        [
            {"source_field": "round", "target_field": "round_number"},
            {"source_field": "phase", "target_field": "phase"},
            {"source_field": "experts_selected", "target_field": "experts"},
            {"source_field": "expert_count", "target_field": "count"},
        ],
    )

    return registry
