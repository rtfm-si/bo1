"""Configuration and factory for sub-problem deliberation subgraph.

This module provides the subgraph construction and a singleton for efficient reuse.
The subgraph is compiled once and reused for all sub-problem executions.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from bo1.graph.deliberation.subgraph.nodes import (
    check_convergence_sp_node,
    parallel_round_sp_node,
    select_personas_sp_node,
    synthesize_sp_node,
    vote_sp_node,
)
from bo1.graph.deliberation.subgraph.routers import (
    route_after_convergence,
    route_after_round,
)
from bo1.graph.deliberation.subgraph.state import SubProblemGraphState

# Module-level singleton for efficient reuse
_SUBPROBLEM_GRAPH: CompiledStateGraph[Any, Any] | None = None


def create_subproblem_graph() -> CompiledStateGraph[Any, Any]:
    """Create compiled subgraph for single sub-problem deliberation.

    This graph is designed to be executed in parallel for independent
    sub-problems, with events streaming via get_stream_writer().

    Graph structure:
        select_personas → parallel_round → check_convergence
                              ↑                   ↓
                              └─── (continue) ←───┘
                                        ↓ (stop)
                                      vote → synthesize → END

    Returns:
        Compiled LangGraph ready for execution as a subgraph

    Note:
        The graph is compiled WITHOUT a checkpointer. The parent graph
        provides checkpointing, and subgraph state is propagated through
        the parent's checkpoint system.
    """
    workflow = StateGraph(SubProblemGraphState)

    # Add nodes
    workflow.add_node("select_personas", select_personas_sp_node)
    workflow.add_node("parallel_round", parallel_round_sp_node)
    workflow.add_node("check_convergence", check_convergence_sp_node)
    workflow.add_node("vote", vote_sp_node)
    workflow.add_node("synthesize", synthesize_sp_node)

    # Linear edges
    workflow.add_edge("select_personas", "parallel_round")
    workflow.add_edge("vote", "synthesize")
    workflow.add_edge("synthesize", END)

    # Conditional edges
    workflow.add_conditional_edges(
        "parallel_round",
        route_after_round,
        {
            "check_convergence": "check_convergence",
            "vote": "vote",
        },
    )

    workflow.add_conditional_edges(
        "check_convergence",
        route_after_convergence,
        {
            "parallel_round": "parallel_round",
            "vote": "vote",
        },
    )

    # Entry point
    workflow.set_entry_point("select_personas")

    # Compile WITHOUT checkpointer (parent provides it)
    return workflow.compile()


def get_subproblem_graph() -> CompiledStateGraph[Any, Any]:
    """Get or create the subproblem graph (singleton).

    This ensures the graph is compiled only once and reused across
    all sub-problem executions, avoiding compilation overhead.

    Returns:
        The compiled subproblem graph
    """
    global _SUBPROBLEM_GRAPH
    if _SUBPROBLEM_GRAPH is None:
        _SUBPROBLEM_GRAPH = create_subproblem_graph()
    return _SUBPROBLEM_GRAPH


def reset_subproblem_graph() -> None:
    """Reset the singleton graph (for testing purposes).

    This forces the next call to get_subproblem_graph() to create
    a new graph instance.
    """
    global _SUBPROBLEM_GRAPH
    _SUBPROBLEM_GRAPH = None
