"""Router registry for LangGraph conditional edges.

This module provides:
- Domain-specific router modules (phase, facilitator, synthesis)
- A registry for dynamic router lookup
- Re-exports for backward compatibility
"""

from collections.abc import Callable
from typing import Any

# Re-export router_utils for backward compatibility
from bo1.graph.router_utils import (
    get_problem_attr,
    get_subproblem_attr,
    log_routing_decision,
    validate_state_field,
)
from bo1.graph.routers.facilitator import (
    route_after_identify_gaps,
    route_clarification,
    route_convergence_check,
    route_facilitator_decision,
)
from bo1.graph.routers.phase import route_phase
from bo1.graph.routers.synthesis import (
    route_after_next_subproblem,
    route_after_synthesis,
    route_on_resume,
    route_subproblem_execution,
)

# Private aliases for backward compatibility
_validate_state_field = validate_state_field
_get_problem_attr = get_problem_attr
_get_subproblem_attr = get_subproblem_attr


# Router registry: name → function mapping
ROUTER_REGISTRY: dict[str, Callable[..., Any]] = {
    # Phase routing
    "route_phase": route_phase,
    # Facilitator routing
    "route_facilitator_decision": route_facilitator_decision,
    "route_convergence_check": route_convergence_check,
    "route_clarification": route_clarification,
    "route_after_identify_gaps": route_after_identify_gaps,
    # Synthesis and sub-problem routing
    "route_after_synthesis": route_after_synthesis,
    "route_after_next_subproblem": route_after_next_subproblem,
    "route_subproblem_execution": route_subproblem_execution,
    "route_on_resume": route_on_resume,
}


def get_router(name: str) -> Callable[..., Any]:
    """Get a router function by name.

    Args:
        name: Router function name (e.g., "route_phase")

    Returns:
        The router function

    Raises:
        KeyError: If router name not found in registry
    """
    if name not in ROUTER_REGISTRY:
        raise KeyError(f"Router '{name}' not found. Available: {list(ROUTER_REGISTRY.keys())}")
    return ROUTER_REGISTRY[name]


def list_routers() -> list[str]:
    """List all available router names.

    Returns:
        Sorted list of router names
    """
    return sorted(ROUTER_REGISTRY.keys())


# Re-export all router functions for backward compatibility
__all__ = [
    # Registry functions
    "ROUTER_REGISTRY",
    "get_router",
    "list_routers",
    # Router utilities (from router_utils)
    "validate_state_field",
    "get_problem_attr",
    "get_subproblem_attr",
    "log_routing_decision",
    # Private aliases for backward compat
    "_validate_state_field",
    "_get_problem_attr",
    "_get_subproblem_attr",
    # Phase routers
    "route_phase",
    # Facilitator routers
    "route_facilitator_decision",
    "route_convergence_check",
    "route_clarification",
    "route_after_identify_gaps",
    # Synthesis routers
    "route_after_synthesis",
    "route_after_next_subproblem",
    "route_subproblem_execution",
    "route_on_resume",
]
