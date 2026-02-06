"""Unit tests for parallel_subproblems_node and related functions.

Tests for parallel sub-problem execution covering:
1. analyze_dependencies_node - dependency analysis and batch creation
2. topological_batch_sort - batch sorting with dependencies
3. _execute_batch - parallel execution within batches
4. parallel_subproblems_node - full node execution
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bo1.graph.nodes.subproblems import (
    analyze_dependencies_node,
    topological_batch_sort,
)
from bo1.graph.state import DeliberationGraphState
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import DeliberationMetrics


def make_subproblem(sp_id: str, goal: str, dependencies: list[str] = None) -> SubProblem:
    """Helper to create SubProblem objects."""
    return SubProblem(
        id=sp_id,
        goal=goal,
        context="",
        complexity_score=5,
        dependencies=dependencies or [],
    )


@pytest.fixture
def problem_with_independent_sps() -> Problem:
    """Problem with 3 independent sub-problems (no dependencies)."""
    return Problem(
        title="Marketing Strategy",
        description="Plan marketing approach",
        context="B2B SaaS",
        sub_problems=[
            make_subproblem("sp_001", "Analyze CAC"),
            make_subproblem("sp_002", "Evaluate channels"),
            make_subproblem("sp_003", "Plan budget"),
        ],
    )


@pytest.fixture
def problem_with_dependencies() -> Problem:
    """Problem with dependent sub-problems (chain: sp_001 -> sp_002 -> sp_003)."""
    return Problem(
        title="Marketing Strategy",
        description="Plan marketing approach",
        context="B2B SaaS",
        sub_problems=[
            make_subproblem("sp_001", "Analyze CAC", []),
            make_subproblem("sp_002", "Choose channel", ["sp_001"]),
            make_subproblem("sp_003", "Allocate budget", ["sp_001", "sp_002"]),
        ],
    )


@pytest.fixture
def problem_with_circular_deps() -> Problem:
    """Problem with circular dependencies (invalid)."""
    return Problem(
        title="Circular Problem",
        description="Has circular deps",
        context="Test",
        sub_problems=[
            make_subproblem("sp_001", "A", ["sp_003"]),
            make_subproblem("sp_002", "B", ["sp_001"]),
            make_subproblem("sp_003", "C", ["sp_002"]),
        ],
    )


class TestTopologicalBatchSort:
    """Tests for topological_batch_sort function."""

    def test_empty_list(self):
        """Empty list returns empty batches."""
        result = topological_batch_sort([])
        assert result == []

    def test_independent_subproblems_same_batch(self, problem_with_independent_sps):
        """Independent sub-problems should be in the same batch."""
        result = topological_batch_sort(problem_with_independent_sps.sub_problems)

        # All 3 should be in a single batch (parallel execution)
        assert len(result) == 1
        assert set(result[0]) == {0, 1, 2}

    def test_dependent_subproblems_separate_batches(self, problem_with_dependencies):
        """Dependent sub-problems should be in separate batches."""
        result = topological_batch_sort(problem_with_dependencies.sub_problems)

        # Chain: sp_001 -> sp_002 -> sp_003
        # Expected: [[0], [1], [2]]
        assert len(result) == 3
        assert result[0] == [0]  # sp_001 first
        assert result[1] == [1]  # sp_002 second
        assert result[2] == [2]  # sp_003 third

    def test_partial_dependencies(self):
        """Mixed independent and dependent sub-problems."""
        sps = [
            make_subproblem("sp_001", "A", []),  # Independent
            make_subproblem("sp_002", "B", ["sp_001"]),  # Depends on A
            make_subproblem("sp_003", "C", []),  # Independent
        ]

        result = topological_batch_sort(sps)

        # A and C can run together, then B
        assert len(result) == 2
        assert set(result[0]) == {0, 2}  # sp_001 and sp_003
        assert result[1] == [1]  # sp_002

    def test_circular_dependency_raises(self, problem_with_circular_deps):
        """Circular dependencies should raise ValueError."""
        with pytest.raises(ValueError, match="Circular dependency"):
            topological_batch_sort(problem_with_circular_deps.sub_problems)


class TestAnalyzeDependenciesNode:
    """Tests for analyze_dependencies_node."""

    @pytest.mark.asyncio
    async def test_sequential_mode_single_subproblem(self):
        """Single sub-problem uses sequential mode."""
        problem = Problem(
            title="Single SP",
            description="One sub-problem",
            context="Test",
            sub_problems=[make_subproblem("sp_001", "Only one")],
        )
        state: DeliberationGraphState = {
            "session_id": "test-session",
            "problem": problem,
        }

        result = await analyze_dependencies_node(state)

        assert result["execution_batches"] == [[0]]
        assert result["parallel_mode"] is False
        assert result["current_sub_problem"] is not None

    @pytest.mark.asyncio
    async def test_creates_parallel_batches(self, problem_with_dependencies):
        """Creates execution batches for multi-sub-problem cases."""
        state: DeliberationGraphState = {
            "session_id": "test-session",
            "problem": problem_with_dependencies,
        }

        result = await analyze_dependencies_node(state)

        # Multi-subproblem: use subgraph (parallel_mode=True)
        assert result["parallel_mode"] is True
        assert len(result["execution_batches"]) == 3  # Chain deps
        assert result["current_node"] == "analyze_dependencies"

    @pytest.mark.asyncio
    async def test_independent_subproblems_single_batch(self, problem_with_independent_sps):
        """Independent sub-problems go in a single batch for parallel execution."""
        state: DeliberationGraphState = {
            "session_id": "test-session",
            "problem": problem_with_independent_sps,
        }

        result = await analyze_dependencies_node(state)

        # All 3 independent sub-problems in one batch
        assert result["parallel_mode"] is True
        assert len(result["execution_batches"]) == 1
        assert set(result["execution_batches"][0]) == {0, 1, 2}

    @pytest.mark.asyncio
    async def test_circular_dependency_fallback(self, problem_with_circular_deps):
        """Circular dependencies fall back to sequential mode."""
        state: DeliberationGraphState = {
            "session_id": "test-session",
            "problem": problem_with_circular_deps,
        }

        result = await analyze_dependencies_node(state)

        # Fallback to sequential on circular deps
        assert result["parallel_mode"] is False
        assert result["execution_batches"] == [[0], [1], [2]]
        assert "dependency_error" in result

    @pytest.mark.asyncio
    async def test_handles_dict_problem(self, problem_with_independent_sps):
        """Handles problem as dict (from checkpoint recovery)."""
        state: DeliberationGraphState = {
            "session_id": "test-session",
            "problem": problem_with_independent_sps.model_dump(),  # Dict form
        }

        result = await analyze_dependencies_node(state)

        # Should work with dict input
        assert result["parallel_mode"] is True
        assert len(result["execution_batches"]) == 1


class TestParallelSubproblemsNode:
    """Tests for the main parallel_subproblems_node."""

    @pytest.fixture
    def mock_subproblem_graph(self):
        """Mock the subproblem graph."""

        async def mock_ainvoke(state, config=None):
            """Return a mock final state."""
            sp_id = state.get("sub_problem", {})
            if isinstance(sp_id, SubProblem):
                sp_id = sp_id.id
            else:
                sp_id = sp_id.get("id", "unknown")

            return {
                "sub_problem_id": sp_id,
                "sub_problem_goal": "Test goal",
                "synthesis": "Test synthesis",
                "votes": [],
                "contribution_count": 5,
                "cost": 0.05,
                "expert_panel": ["expert_1"],
                "expert_summaries": {},
            }

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=mock_ainvoke)
        return mock_graph

    @pytest.fixture
    def mock_stream_writer(self):
        """Mock stream writer that collects events."""
        events = []

        def writer(event):
            events.append(event)

        writer.events = events
        return writer

    @pytest.mark.asyncio
    async def test_batch_mode_execution(
        self, problem_with_independent_sps, mock_subproblem_graph, mock_stream_writer
    ):
        """Test batch mode executes sub-problems correctly."""
        from bo1.graph.nodes.subproblems import _parallel_subproblems_subgraph
        from bo1.models.state import SubProblemResult

        state: DeliberationGraphState = {
            "session_id": "test-session",
            "problem": problem_with_independent_sps,
            "execution_batches": [[0, 1, 2]],  # All parallel
            "user_id": "test_user",
            "metrics": DeliberationMetrics(),
        }

        # Mock result creation
        def make_result(sp_idx, sp):
            return SubProblemResult(
                sub_problem_id=sp.id,
                sub_problem_goal=sp.goal,
                synthesis=f"Synthesis for {sp.id}",
                votes=[],
                contribution_count=3,
                cost=0.02,
                duration_seconds=1.0,
                expert_panel=["expert"],
                expert_summaries={},
            )

        with patch("langgraph.config.get_stream_writer", return_value=mock_stream_writer):
            with patch(
                "bo1.graph.deliberation.subgraph.get_subproblem_graph",
                return_value=mock_subproblem_graph,
            ):
                with patch("bo1.feature_flags.ENABLE_SPECULATIVE_PARALLELISM", False):
                    with patch("bo1.data.get_active_personas", return_value=[]):
                        with patch(
                            "bo1.graph.nodes.subproblems._execute_batch",
                            new_callable=AsyncMock,
                        ) as mock_batch:
                            mock_batch.return_value = [
                                make_result(i, sp)
                                for i, sp in enumerate(problem_with_independent_sps.sub_problems)
                            ]

                            result = await _parallel_subproblems_subgraph(state)

        # Verify results
        assert "sub_problem_results" in result
        assert result["current_sub_problem"] is None
        assert result["current_node"] == "parallel_subproblems"

    @pytest.mark.asyncio
    async def test_emits_all_subproblems_complete_event(
        self, problem_with_independent_sps, mock_stream_writer
    ):
        """Test that all_subproblems_complete event is emitted."""
        from bo1.graph.nodes.subproblems import _parallel_subproblems_subgraph
        from bo1.models.state import SubProblemResult

        state: DeliberationGraphState = {
            "session_id": "test-session",
            "problem": problem_with_independent_sps,
            "execution_batches": [[0, 1, 2]],
            "user_id": "test_user",
            "metrics": DeliberationMetrics(),
        }

        mock_results = [
            SubProblemResult(
                sub_problem_id=f"sp_{i:03d}",
                sub_problem_goal=f"Goal {i}",
                synthesis=f"Synthesis {i}",
                votes=[],
                contribution_count=3,
                cost=0.02,
                duration_seconds=1.0,
                expert_panel=["expert"],
                expert_summaries={},
            )
            for i in range(3)
        ]

        with patch("langgraph.config.get_stream_writer", return_value=mock_stream_writer):
            with patch("bo1.feature_flags.ENABLE_SPECULATIVE_PARALLELISM", False):
                with patch("bo1.data.get_active_personas", return_value=[]):
                    with patch("bo1.graph.deliberation.subgraph.get_subproblem_graph"):
                        with patch(
                            "bo1.graph.nodes.subproblems._execute_batch",
                            new_callable=AsyncMock,
                            return_value=mock_results,
                        ):
                            await _parallel_subproblems_subgraph(state)

        # Check for completion event
        event_types = [e.get("event_type") for e in mock_stream_writer.events]
        assert "all_subproblems_complete" in event_types

        # Verify event details
        complete_event = next(
            e
            for e in mock_stream_writer.events
            if e.get("event_type") == "all_subproblems_complete"
        )
        assert complete_event["total_sub_problems"] == 3
        assert complete_event["execution_mode"] == "batch"


class TestExecuteBatch:
    """Tests for _execute_batch function."""

    @pytest.mark.asyncio
    async def test_executes_subproblems_in_parallel(self, problem_with_independent_sps):
        """Batch executes all sub-problems concurrently."""
        from bo1.graph.nodes.subproblems import _execute_batch
        from bo1.models.state import SubProblemResult

        events = []

        def mock_writer(e):
            events.append(e)

        async def mock_run_single(sp_idx, *args, **kwargs):
            return (
                sp_idx,
                SubProblemResult(
                    sub_problem_id=f"sp_{sp_idx:03d}",
                    sub_problem_goal=f"Goal {sp_idx}",
                    synthesis=f"Synthesis {sp_idx}",
                    votes=[],
                    contribution_count=3,
                    cost=0.02,
                    duration_seconds=1.0,
                    expert_panel=["expert"],
                    expert_summaries={},
                ),
                1.0,
            )

        with patch(
            "bo1.graph.nodes.subproblems.batch._run_single_subproblem", side_effect=mock_run_single
        ):
            with patch("bo1.graph.deliberation.subgraph.build_expert_memory", return_value={}):
                results = await _execute_batch(
                    batch=[0, 1, 2],
                    batch_idx=0,
                    total_batches=1,
                    sub_problems=problem_with_independent_sps.sub_problems,
                    subproblem_graph=MagicMock(),
                    session_id="test",
                    problem=problem_with_independent_sps,
                    all_personas=[],
                    all_results=[],
                    user_id="test",
                    writer=mock_writer,
                )

        assert len(results) == 3
        # Check events
        assert any(e.get("event_type") == "batch_started" for e in events)
        assert any(e.get("event_type") == "batch_complete" for e in events)

    @pytest.mark.asyncio
    async def test_handles_subproblem_failure(self, problem_with_independent_sps):
        """Batch raises RuntimeError when a sub-problem fails."""
        from bo1.graph.nodes.subproblems import _execute_batch

        events = []

        def mock_writer(e):
            events.append(e)

        async def mock_run_single_with_failure(sp_idx, *args, **kwargs):
            if sp_idx == 1:
                raise RuntimeError("Sub-problem 1 failed")
            return (sp_idx, MagicMock(), 1.0)

        with patch(
            "bo1.graph.nodes.subproblems.batch._run_single_subproblem",
            side_effect=mock_run_single_with_failure,
        ):
            with patch("bo1.graph.deliberation.subgraph.build_expert_memory", return_value={}):
                with pytest.raises(RuntimeError, match="failed in batch"):
                    await _execute_batch(
                        batch=[0, 1, 2],
                        batch_idx=0,
                        total_batches=1,
                        sub_problems=problem_with_independent_sps.sub_problems,
                        subproblem_graph=MagicMock(),
                        session_id="test",
                        problem=problem_with_independent_sps,
                        all_personas=[],
                        all_results=[],
                        user_id="test",
                        writer=mock_writer,
                    )

        # Should emit failure event
        assert any(e.get("event_type") == "subproblem_failed" for e in events)
