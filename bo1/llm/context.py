"""Thread-local context for cost attribution.

This module provides context variables that propagate session information
through async call stacks without modifying function signatures.
"""

import contextvars
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

# Context variable for session info (default=None to avoid mutable default)
_cost_context: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "cost_context", default=None
)


def _get_context_dict() -> dict[str, Any]:
    """Get the context dict, initializing if needed."""
    ctx = _cost_context.get()
    if ctx is None:
        ctx = {}
        _cost_context.set(ctx)
    return ctx


@dataclass
class CostContext:
    """Context for cost attribution."""

    session_id: str | None = None
    user_id: str | None = None
    node_name: str | None = None
    phase: str | None = None
    round_number: int | None = None
    sub_problem_index: int | None = None
    persona_name: str | None = None


def set_cost_context(**kwargs: Any) -> None:
    """Set cost context values."""
    current = _get_context_dict()
    _cost_context.set({**current, **kwargs})


def get_cost_context() -> dict[str, Any]:
    """Get current cost context."""
    return _get_context_dict().copy()


def clear_cost_context() -> None:
    """Clear all cost context."""
    _cost_context.set({})


@contextmanager
def cost_context_scope(**kwargs: Any) -> Generator[None, None, None]:
    """Context manager to set cost context for a scope.

    Usage:
        with cost_context_scope(session_id="123", node_name="parallel_round"):
            # All API calls in this scope inherit the context
            await some_llm_call()
    """
    old = _get_context_dict()
    _cost_context.set({**old, **kwargs})
    try:
        yield
    finally:
        _cost_context.set(old)
