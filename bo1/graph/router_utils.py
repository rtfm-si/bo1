"""Shared router utilities for LangGraph conditional edges.

Provides common helpers and decorators for consistent router behavior.
"""

import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from bo1.logging import ErrorCode, log_error

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def validate_state_field(state: Any, field_name: str, router_name: str) -> Any | None:
    """Validate that a required state field is present.

    Returns the field value if present, None if missing.
    Logs ErrorCode.GRAPH_STATE_ERROR with router context when field is missing.

    Args:
        state: Current graph state
        field_name: Name of the field to validate
        router_name: Name of the calling router (for logging context)

    Returns:
        Field value if present, None if missing
    """
    value = state.get(field_name)
    if not value:
        log_error(
            logger,
            ErrorCode.GRAPH_STATE_ERROR,
            f"{router_name}: No {field_name} in state!",
        )
        return None
    return value


def get_problem_attr(problem: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute from problem (handles both dict and object).

    After checkpoint restoration, Problem objects may be deserialized as dicts.
    This helper handles both cases.
    """
    if problem is None:
        return default
    if isinstance(problem, dict):
        return problem.get(attr, default)
    return getattr(problem, attr, default)


def get_subproblem_attr(sp: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute from sub-problem (handles both dict and object).

    After checkpoint restoration, SubProblem objects may be deserialized as dicts.
    This helper handles both cases.
    """
    if sp is None:
        return default
    if isinstance(sp, dict):
        return sp.get(attr, default)
    return getattr(sp, attr, default)


def log_routing_decision(router_name: str) -> Callable[[F], F]:
    """Decorator for consistent router logging.

    Logs entry with router name and key state values,
    then logs exit with the routing decision.

    Args:
        router_name: Name of the router function (for log context)

    Returns:
        Decorated function with entry/exit logging
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(state: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
            # Extract key state values for entry log
            phase = state.get("phase")
            round_number = state.get("round_number")
            sub_problem_index = state.get("sub_problem_index")
            should_stop = state.get("should_stop")

            # Build context string with available values
            context_parts = []
            if phase is not None:
                context_parts.append(f"phase={phase}")
            if round_number is not None:
                context_parts.append(f"round={round_number}")
            if sub_problem_index is not None:
                context_parts.append(f"sp_idx={sub_problem_index}")
            if should_stop is not None:
                context_parts.append(f"should_stop={should_stop}")

            context_str = ", ".join(context_parts) if context_parts else "no context"

            logger.info(f"{router_name}: Entry ({context_str})")

            # Execute the router
            decision = func(state, *args, **kwargs)

            logger.info(f"{router_name}: Decision -> {decision}")

            return decision

        return wrapper  # type: ignore[return-value]

    return decorator
