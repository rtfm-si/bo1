"""Subgraph module for sub-problem deliberation.

This module provides a LangGraph subgraph for deliberating individual sub-problems
with real-time event streaming via get_stream_writer().

Key components:
- SubProblemGraphState: State type for subgraph execution
- create_subproblem_graph(): Factory for compiled subgraph
- State transformation helpers for parent/subgraph data flow
"""

from bo1.graph.deliberation.subgraph.config import create_subproblem_graph, get_subproblem_graph
from bo1.graph.deliberation.subgraph.state import (
    SubProblemGraphState,
    build_expert_memory,
    create_subproblem_initial_state,
    result_from_subgraph_state,
)

__all__ = [
    "SubProblemGraphState",
    "build_expert_memory",
    "create_subproblem_graph",
    "get_subproblem_graph",
    "create_subproblem_initial_state",
    "result_from_subgraph_state",
]
