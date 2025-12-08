"""LangGraph node implementations for deliberation.

This package contains modular node functions for the deliberation graph.
Each module focuses on a specific concern:

- decomposition: Problem decomposition and complexity assessment
- selection: Persona selection for deliberation
- rounds: Initial and parallel deliberation rounds
- moderation: Facilitator decisions and moderator interventions
- research: External research execution
- synthesis: Voting, synthesis, and meta-synthesis
- subproblems: Parallel sub-problem execution
- context: Context collection and clarification
- utils: Shared helper functions

All node functions are re-exported from this module for backward compatibility
with existing imports from `bo1.graph.nodes`.
"""

# Decomposition
# Re-export context building helpers that were in original nodes.py
# These delegate to bo1.graph.deliberation but are exported for convenience
from bo1.graph.deliberation import (
    build_dependency_context,
    build_subproblem_context_for_all,
    extract_recommendation_from_synthesis,
)

# Context
from bo1.graph.nodes.context import (
    clarification_node,
    context_collection_node,
    identify_gaps_node,
)
from bo1.graph.nodes.decomposition import decompose_node

# Moderation (consolidated from archived/moderation.py)
from bo1.graph.nodes.moderation import facilitator_decide_node, moderator_intervene_node

# Research
from bo1.graph.nodes.research import research_node

# Rounds
from bo1.graph.nodes.rounds import (
    _determine_phase,
    _generate_parallel_contributions,
    initial_round_node,
    parallel_round_node,
)

# Selection
from bo1.graph.nodes.selection import select_personas_node

# Subproblems
from bo1.graph.nodes.subproblems import (
    _deliberate_subproblem,
    _parallel_subproblems_subgraph,
    analyze_dependencies_node,
    parallel_subproblems_node,
    topological_batch_sort,
)

# Synthesis
from bo1.graph.nodes.synthesis import (
    meta_synthesize_node,
    next_subproblem_node,
    synthesize_node,
    vote_node,
)

# Utils (re-export for backward compatibility)
from bo1.graph.nodes.utils import (
    get_phase_prompt,
    phase_prompt_short,
    retry_with_backoff,
)

__all__ = [
    # Decomposition
    "decompose_node",
    # Selection
    "select_personas_node",
    # Rounds
    "initial_round_node",
    "parallel_round_node",
    "_determine_phase",
    "_generate_parallel_contributions",
    # Moderation
    "facilitator_decide_node",
    "moderator_intervene_node",
    # Research
    "research_node",
    # Synthesis
    "vote_node",
    "synthesize_node",
    "next_subproblem_node",
    "meta_synthesize_node",
    # Subproblems
    "analyze_dependencies_node",
    "parallel_subproblems_node",
    "topological_batch_sort",
    "_deliberate_subproblem",
    "_parallel_subproblems_subgraph",
    "_parallel_subproblems_legacy",
    # Context
    "context_collection_node",
    "identify_gaps_node",
    "clarification_node",
    # Utils
    "retry_with_backoff",
    "phase_prompt_short",
    "get_phase_prompt",
    # Context building helpers (from deliberation module)
    "extract_recommendation_from_synthesis",
    "build_dependency_context",
    "build_subproblem_context_for_all",
]
