"""Routing functions for sub-problem deliberation subgraph.

These functions determine conditional edges in the subgraph based on state.
"""

from typing import Literal

from bo1.graph.deliberation.subgraph.state import SubProblemGraphState
from bo1.graph.router_utils import log_routing_decision


@log_routing_decision("route_after_round")
def route_after_round(
    state: SubProblemGraphState,
) -> Literal["check_convergence", "vote"]:
    """Route after a parallel round completes.

    If we've reached max rounds, go directly to voting.
    Otherwise, check convergence first.
    """
    round_number = state.get("round_number", 1)
    max_rounds = state.get("max_rounds", 6)

    if round_number > max_rounds:
        return "vote"

    return "check_convergence"


@log_routing_decision("route_after_convergence")
def route_after_convergence(
    state: SubProblemGraphState,
) -> Literal["parallel_round", "vote"]:
    """Route after convergence check.

    If should_stop is True (convergence reached or max rounds), go to voting.
    Otherwise, continue with another round.
    """
    should_stop = state.get("should_stop", False)
    round_number = state.get("round_number", 1)
    max_rounds = state.get("max_rounds", 6)

    if should_stop or round_number > max_rounds:
        return "vote"

    return "parallel_round"
