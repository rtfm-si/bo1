"""Context collection and clarification nodes.

This package contains nodes for collecting and managing context:
- context_collection_node: Collects business context before deliberation
- identify_gaps_node: Identifies critical information gaps after decomposition
- clarification_node: Handles clarification questions during deliberation
"""

from bo1.graph.nodes.context.clarification import clarification_node
from bo1.graph.nodes.context.cognitive import build_cognitive_context_block
from bo1.graph.nodes.context.collection import context_collection_node
from bo1.graph.nodes.context.gaps import identify_gaps_node

__all__ = [
    "build_cognitive_context_block",
    "clarification_node",
    "context_collection_node",
    "identify_gaps_node",
]
