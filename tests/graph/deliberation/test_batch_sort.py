"""Tests for topological batch sorting."""

import pytest

from bo1.graph.deliberation.batch_sort import topological_batch_sort
from bo1.models.problem import SubProblem


class TestTopologicalBatchSort:
    """Test dependency-aware batch sorting."""

    @pytest.fixture
    def make_subproblem(self):
        """Factory for creating SubProblem instances."""

        def _make(id: str, goal: str, dependencies: list[str] | None = None):
            return SubProblem(
                id=id,
                goal=goal,
                context="Test context",
                complexity_score=5,
                dependencies=dependencies or [],
            )

        return _make

    def test_empty_list(self, make_subproblem):
        """Empty list returns empty batches."""
        batches = topological_batch_sort([])
        assert batches == []

    def test_single_subproblem(self, make_subproblem):
        """Single sub-problem returns single batch."""
        sub_problems = [make_subproblem("sp1", "A")]
        batches = topological_batch_sort(sub_problems)
        assert batches == [[0]]

    def test_independent_subproblems_single_batch(self, make_subproblem):
        """Independent sub-problems go in one batch."""
        sub_problems = [
            make_subproblem("sp1", "A"),
            make_subproblem("sp2", "B"),
            make_subproblem("sp3", "C"),
        ]
        batches = topological_batch_sort(sub_problems)
        assert len(batches) == 1
        assert set(batches[0]) == {0, 1, 2}

    def test_linear_dependencies(self, make_subproblem):
        """Linear chain = sequential batches."""
        sub_problems = [
            make_subproblem("sp1", "A"),
            make_subproblem("sp2", "B", ["sp1"]),
            make_subproblem("sp3", "C", ["sp2"]),
        ]
        batches = topological_batch_sort(sub_problems)
        assert len(batches) == 3
        assert batches == [[0], [1], [2]]

    def test_diamond_dependency(self, make_subproblem):
        """Diamond pattern: A -> B,C -> D."""
        sub_problems = [
            make_subproblem("sp1", "A"),
            make_subproblem("sp2", "B", ["sp1"]),
            make_subproblem("sp3", "C", ["sp1"]),
            make_subproblem("sp4", "D", ["sp2", "sp3"]),
        ]
        batches = topological_batch_sort(sub_problems)
        assert len(batches) == 3
        assert batches[0] == [0]  # sp1
        assert set(batches[1]) == {1, 2}  # sp2, sp3 parallel
        assert batches[2] == [3]  # sp4

    def test_mixed_dependencies(self, make_subproblem):
        """Mix of independent and dependent sub-problems."""
        sub_problems = [
            make_subproblem("sp1", "A"),  # Independent
            make_subproblem("sp2", "B"),  # Independent
            make_subproblem("sp3", "C", ["sp1"]),  # Depends on sp1
            make_subproblem("sp4", "D", ["sp1", "sp2"]),  # Depends on sp1 and sp2
        ]
        batches = topological_batch_sort(sub_problems)
        assert len(batches) == 2
        assert set(batches[0]) == {0, 1}  # sp1, sp2 parallel
        assert set(batches[1]) == {2, 3}  # sp3, sp4 parallel (both deps satisfied)

    def test_circular_dependency_raises(self, make_subproblem):
        """Circular dependency raises ValueError."""
        sub_problems = [
            make_subproblem("sp1", "A", ["sp2"]),  # Depends on sp2
            make_subproblem("sp2", "B", ["sp1"]),  # Depends on sp1 - circular!
        ]
        with pytest.raises(ValueError, match="Circular dependency"):
            topological_batch_sort(sub_problems)

    def test_self_dependency_raises(self, make_subproblem):
        """Self-dependency raises ValueError."""
        sub_problems = [
            make_subproblem("sp1", "A", ["sp1"]),  # Depends on itself
        ]
        with pytest.raises(ValueError, match="Circular dependency"):
            topological_batch_sort(sub_problems)

    def test_missing_dependency_raises(self, make_subproblem):
        """Missing dependency effectively behaves like circular dep (raises error)."""
        sub_problems = [
            make_subproblem("sp1", "A", ["nonexistent"]),  # Depends on non-existent
        ]
        # Missing deps ARE counted in in_degree but never decremented,
        # so in_degree never reaches 0, causing "circular dependency" error
        with pytest.raises(ValueError, match="Circular dependency"):
            topological_batch_sort(sub_problems)

    def test_multiple_dependency_chains(self, make_subproblem):
        """Multiple independent chains."""
        sub_problems = [
            make_subproblem("sp1", "A"),  # Chain 1 start
            make_subproblem("sp2", "B", ["sp1"]),  # Chain 1 end
            make_subproblem("sp3", "C"),  # Chain 2 start
            make_subproblem("sp4", "D", ["sp3"]),  # Chain 2 end
        ]
        batches = topological_batch_sort(sub_problems)
        assert len(batches) == 2
        assert set(batches[0]) == {0, 2}  # sp1, sp3 parallel
        assert set(batches[1]) == {1, 3}  # sp2, sp4 parallel
