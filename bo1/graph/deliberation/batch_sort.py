"""Dependency-aware batch sorting for parallel sub-problem execution.

Uses topological sorting to group independent sub-problems into batches
that can be executed in parallel.

This module is extracted from nodes.py for better testability.
"""

import logging

from bo1.models.problem import SubProblem

logger = logging.getLogger(__name__)


def topological_batch_sort(sub_problems: list[SubProblem]) -> list[list[int]]:
    """Sort sub-problems into execution batches respecting dependencies.

    Returns list of batches, where each batch contains indices of
    sub-problems that can run in parallel.

    Uses Kahn's algorithm variant that groups nodes at the same level
    (with all dependencies satisfied) into parallel batches.

    Args:
        sub_problems: List of SubProblem objects with dependencies

    Returns:
        List of batches, where each batch is a list of sub-problem indices
        that can be executed in parallel

    Raises:
        ValueError: If circular dependency detected

    Examples:
        >>> from bo1.models.problem import SubProblem
        >>> sp1 = SubProblem(id="sp_001", goal="A", context="", complexity_score=5, dependencies=[])
        >>> sp2 = SubProblem(id="sp_002", goal="B", context="", complexity_score=5, dependencies=["sp_001"])
        >>> sp3 = SubProblem(id="sp_003", goal="C", context="", complexity_score=5, dependencies=[])
        >>> batches = topological_batch_sort([sp1, sp2, sp3])
        >>> batches
        [[0, 2], [1]]  # sp_001 and sp_003 can run in parallel, then sp_002
    """
    if not sub_problems:
        return []

    # Build ID to index mapping (for future validation use)
    _id_to_idx = {sp.id: i for i, sp in enumerate(sub_problems)}  # noqa: F841
    in_degree = [len(sp.dependencies) for sp in sub_problems]
    batches: list[list[int]] = []
    remaining = set(range(len(sub_problems)))

    while remaining:
        # Find all sub-problems with no remaining dependencies
        batch = [i for i in remaining if in_degree[i] == 0]

        if not batch:
            # No sub-problems ready -> circular dependency
            raise ValueError("Circular dependency detected in sub-problems")

        batches.append(batch)

        # Remove batch from remaining
        for idx in batch:
            remaining.remove(idx)
            sp_id = sub_problems[idx].id

            # Decrement in-degree for sub-problems that depend on this one
            for other_idx in remaining:
                if sp_id in sub_problems[other_idx].dependencies:
                    in_degree[other_idx] -= 1

    logger.info(f"Sub-problem batches: {batches} (parallel execution groups)")
    return batches
