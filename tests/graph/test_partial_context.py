"""Unit tests for PartialContextProvider (speculative parallelization)."""

import asyncio

import pytest

from bo1.graph.deliberation.partial_context import (
    PartialContext,
    PartialContextProvider,
    SubProblemProgress,
)


class TestSubProblemProgress:
    """Test SubProblemProgress dataclass."""

    def test_initial_progress(self):
        """Test initial state of SubProblemProgress."""
        progress = SubProblemProgress(
            sp_index=0,
            sp_id="sp_001",
            goal="Test goal",
        )

        assert progress.sp_index == 0
        assert progress.sp_id == "sp_001"
        assert progress.goal == "Test goal"
        assert progress.completed_rounds == 0
        assert progress.max_rounds == 6
        assert progress.is_complete is False
        assert progress.final_synthesis is None
        assert progress.round_summaries == []

    def test_progress_percentage(self):
        """Test progress percentage calculation."""
        progress = SubProblemProgress(
            sp_index=0,
            sp_id="sp_001",
            goal="Test goal",
            max_rounds=6,
        )

        # Initial state
        assert progress.get_progress_percentage() == 0.0

        # After 2 rounds
        progress.completed_rounds = 2
        assert progress.get_progress_percentage() == pytest.approx(2 / 6)

        # After completion
        progress.is_complete = True
        assert progress.get_progress_percentage() == 1.0


class TestPartialContextProvider:
    """Test PartialContextProvider functionality."""

    @pytest.mark.asyncio
    async def test_register_subproblem(self):
        """Test registering a sub-problem."""
        provider = PartialContextProvider(early_start_threshold=2)

        await provider.register_subproblem(
            sp_index=0,
            sp_id="sp_001",
            goal="Market analysis",
            max_rounds=6,
            expert_panel=["growth_hacker", "finance_strategist"],
        )

        progress = await provider.get_all_progress()
        assert 0 in progress
        assert progress[0].sp_id == "sp_001"
        assert progress[0].goal == "Market analysis"
        assert progress[0].expert_panel == ["growth_hacker", "finance_strategist"]

    @pytest.mark.asyncio
    async def test_update_round_context(self):
        """Test updating context after round completion."""
        provider = PartialContextProvider(early_start_threshold=2)

        await provider.register_subproblem(
            sp_index=0,
            sp_id="sp_001",
            goal="Market analysis",
        )

        # Update after round 1
        await provider.update_round_context(
            sp_index=0,
            round_num=1,
            round_summary="Initial exploration of market segments",
        )

        progress = await provider.get_all_progress()
        assert progress[0].completed_rounds == 1
        assert len(progress[0].round_summaries) == 1

        # Update after round 2
        await provider.update_round_context(
            sp_index=0,
            round_num=2,
            round_summary="Deep dive into B2C market opportunity",
            early_insights=["B2C market is 10x larger", "Higher CAC but better LTV"],
        )

        progress = await provider.get_all_progress()
        assert progress[0].completed_rounds == 2
        assert len(progress[0].round_summaries) == 2
        assert len(progress[0].early_insights) == 2

    @pytest.mark.asyncio
    async def test_mark_complete(self):
        """Test marking sub-problem as complete."""
        provider = PartialContextProvider()

        await provider.register_subproblem(
            sp_index=0,
            sp_id="sp_001",
            goal="Market analysis",
        )

        await provider.mark_complete(
            sp_index=0,
            final_synthesis="B2C represents a significant growth opportunity...",
            final_recommendation="Pursue hybrid model with B2C focus",
        )

        progress = await provider.get_all_progress()
        assert progress[0].is_complete is True
        assert progress[0].final_synthesis == "B2C represents a significant growth opportunity..."
        assert progress[0].final_recommendation == "Pursue hybrid model with B2C focus"

    @pytest.mark.asyncio
    async def test_wait_for_ready_immediate(self):
        """Test wait_for_ready returns immediately when threshold met."""
        provider = PartialContextProvider(early_start_threshold=2)

        await provider.register_subproblem(sp_index=0, sp_id="sp_001", goal="SP0")

        # Complete 2 rounds (reaches threshold)
        await provider.update_round_context(sp_index=0, round_num=1, round_summary="R1")
        await provider.update_round_context(sp_index=0, round_num=2, round_summary="R2")

        # Should return immediately
        result = await provider.wait_for_ready(dependency_indices=[0], timeout=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_ready_timeout(self):
        """Test wait_for_ready times out when threshold not met."""
        provider = PartialContextProvider(early_start_threshold=2)

        await provider.register_subproblem(sp_index=0, sp_id="sp_001", goal="SP0")

        # Only 1 round (below threshold)
        await provider.update_round_context(sp_index=0, round_num=1, round_summary="R1")

        # Should timeout
        result = await provider.wait_for_ready(dependency_indices=[0], timeout=0.1)
        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_ready_no_dependencies(self):
        """Test wait_for_ready returns True with no dependencies."""
        provider = PartialContextProvider()

        result = await provider.wait_for_ready(dependency_indices=[], timeout=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_partial_context(self):
        """Test getting partial context from dependencies."""
        provider = PartialContextProvider(early_start_threshold=2)

        # Register SP0 and SP1
        await provider.register_subproblem(sp_index=0, sp_id="sp_001", goal="Market analysis")
        await provider.register_subproblem(sp_index=1, sp_id="sp_002", goal="Tech feasibility")

        # SP0 completes 2 rounds
        await provider.update_round_context(
            sp_index=0,
            round_num=1,
            round_summary="Initial market exploration",
        )
        await provider.update_round_context(
            sp_index=0,
            round_num=2,
            round_summary="Deep dive into segments",
            early_insights=["B2C market is large"],
        )

        # Get context for SP1 (depends on SP0)
        context = await provider.get_partial_context(
            sp_index=1,
            dependency_indices=[0],
        )

        assert isinstance(context, PartialContext)
        assert context.all_dependencies_ready is True
        assert context.all_dependencies_complete is False
        assert 0 in context.dependency_progress
        assert "Market analysis" in context.available_context
        assert "B2C market is large" in context.available_context

    @pytest.mark.asyncio
    async def test_get_partial_context_complete_dependency(self):
        """Test context when dependency is complete."""
        provider = PartialContextProvider(early_start_threshold=2)

        await provider.register_subproblem(sp_index=0, sp_id="sp_001", goal="Market analysis")

        # SP0 completes fully
        await provider.update_round_context(sp_index=0, round_num=1, round_summary="R1")
        await provider.update_round_context(sp_index=0, round_num=2, round_summary="R2")
        await provider.mark_complete(
            sp_index=0,
            final_synthesis="Full synthesis here",
            final_recommendation="Go with B2C model",
        )

        context = await provider.get_partial_context(
            sp_index=1,
            dependency_indices=[0],
        )

        assert context.all_dependencies_ready is True
        assert context.all_dependencies_complete is True
        assert "Go with B2C model" in context.available_context
        assert "Complete" in context.available_context

    @pytest.mark.asyncio
    async def test_concurrent_updates(self):
        """Test thread-safety with concurrent updates."""
        provider = PartialContextProvider(early_start_threshold=2)

        # Register multiple sub-problems
        for i in range(5):
            await provider.register_subproblem(sp_index=i, sp_id=f"sp_{i:03d}", goal=f"SP{i}")

        # Simulate concurrent round updates
        async def update_rounds(sp_index: int):
            for round_num in range(1, 7):
                await provider.update_round_context(
                    sp_index=sp_index,
                    round_num=round_num,
                    round_summary=f"SP{sp_index} Round {round_num}",
                )
                await asyncio.sleep(0.01)  # Small delay to simulate work

        # Run all updates concurrently
        await asyncio.gather(*[update_rounds(i) for i in range(5)])

        # Verify all completed correctly
        progress = await provider.get_all_progress()
        for i in range(5):
            assert progress[i].completed_rounds == 6
            assert len(progress[i].round_summaries) == 6


class TestSpeculativeExecution:
    """Test speculative execution scenarios."""

    @pytest.mark.asyncio
    async def test_dependency_chain_sp0_sp1_sp2(self):
        """Test dependency chain: SP0 -> SP1 -> SP2."""
        provider = PartialContextProvider(early_start_threshold=2)

        # Register all sub-problems
        await provider.register_subproblem(sp_index=0, sp_id="sp_001", goal="Market Analysis")
        await provider.register_subproblem(sp_index=1, sp_id="sp_002", goal="Product Strategy")
        await provider.register_subproblem(sp_index=2, sp_id="sp_003", goal="Go-to-Market")

        # SP0 starts and completes round 1
        await provider.update_round_context(sp_index=0, round_num=1, round_summary="SP0 R1")

        # SP1 (depends on SP0) checks if ready - should be False
        context = await provider.get_partial_context(sp_index=1, dependency_indices=[0])
        assert context.all_dependencies_ready is False

        # SP0 completes round 2 (threshold)
        await provider.update_round_context(
            sp_index=0,
            round_num=2,
            round_summary="SP0 R2 - market is favorable",
            early_insights=["Strong B2C demand"],
        )

        # SP1 can now start with partial context
        context = await provider.get_partial_context(sp_index=1, dependency_indices=[0])
        assert context.all_dependencies_ready is True
        assert context.all_dependencies_complete is False
        assert "Strong B2C demand" in context.available_context

        # SP1 starts and completes round 2
        await provider.update_round_context(sp_index=1, round_num=1, round_summary="SP1 R1")
        await provider.update_round_context(sp_index=1, round_num=2, round_summary="SP1 R2")

        # SP2 (depends on SP0, SP1) checks if ready
        context = await provider.get_partial_context(sp_index=2, dependency_indices=[0, 1])
        assert context.all_dependencies_ready is True  # Both at threshold

        # SP0 completes fully
        await provider.mark_complete(
            sp_index=0, final_synthesis="SP0 done", final_recommendation="Pursue B2C"
        )

        # SP2 now has one complete dependency
        context = await provider.get_partial_context(sp_index=2, dependency_indices=[0, 1])
        assert context.all_dependencies_complete is False  # SP1 not complete yet
        assert "Pursue B2C" in context.available_context

    @pytest.mark.asyncio
    async def test_independent_subproblems(self):
        """Test that independent sub-problems don't wait on each other."""
        provider = PartialContextProvider(early_start_threshold=2)

        await provider.register_subproblem(sp_index=0, sp_id="sp_001", goal="SP0")
        await provider.register_subproblem(sp_index=1, sp_id="sp_002", goal="SP1")

        # With no dependencies, SP1 should be ready immediately
        result = await provider.wait_for_ready(dependency_indices=[], timeout=0.1)
        assert result is True

        # Even with empty context
        context = await provider.get_partial_context(sp_index=1, dependency_indices=[])
        assert context.all_dependencies_ready is True
        assert context.all_dependencies_complete is True
