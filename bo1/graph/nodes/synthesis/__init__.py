"""Synthesis and voting nodes.

This package contains nodes for the final stages of deliberation:
- vote_node: Collects recommendations from all personas
- synthesize_node: Creates synthesis from deliberation
- next_subproblem_node: Handles transition between sub-problems
- meta_synthesize_node: Creates cross-sub-problem meta-synthesis
"""

from bo1.graph.nodes.synthesis.meta import meta_synthesize_node
from bo1.graph.nodes.synthesis.subproblem_transition import next_subproblem_node
from bo1.graph.nodes.synthesis.synthesize import synthesize_node
from bo1.graph.nodes.synthesis.vote import vote_node
from bo1.utils.deliberation_logger import get_deliberation_logger

__all__ = [
    "get_deliberation_logger",
    "meta_synthesize_node",
    "next_subproblem_node",
    "synthesize_node",
    "vote_node",
]
