"""Deliberation domain logic for Board of One.

This module contains the core business logic for sub-problem deliberation,
extracted from nodes.py for better testability and maintainability.

Usage:
    from bo1.graph.deliberation import (
        PhaseManager,
        topological_batch_sort,
        build_dependency_context,
        build_subproblem_context_for_all,
        extract_recommendation_from_synthesis,
        select_experts_for_round,
        deliberate_subproblem,
    )

Module Structure:
- phases.py: Phase management (exploration, challenge, convergence)
- batch_sort.py: Dependency-aware batch sorting for parallel execution
- context.py: Context building between sub-problems
- experts.py: Expert selection for deliberation rounds
- engine.py: Single sub-problem deliberation orchestration
"""

from bo1.graph.deliberation.batch_sort import topological_batch_sort
from bo1.graph.deliberation.context import (
    build_dependency_context,
    build_subproblem_context_for_all,
    extract_recommendation_from_synthesis,
)
from bo1.graph.deliberation.engine import deliberate_subproblem
from bo1.graph.deliberation.experts import select_experts_for_round
from bo1.graph.deliberation.phases import DeliberationPhase, PhaseManager

__all__ = [
    # Phase management
    "PhaseManager",
    "DeliberationPhase",
    # Batch sorting
    "topological_batch_sort",
    # Context building
    "build_dependency_context",
    "build_subproblem_context_for_all",
    "extract_recommendation_from_synthesis",
    # Expert selection
    "select_experts_for_round",
    # Deliberation engine
    "deliberate_subproblem",
]
