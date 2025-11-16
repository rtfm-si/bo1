"""Tests for checkpoint recovery and resume functionality.

This module tests the pause/resume capability of LangGraph deliberations
using Redis checkpointing.
"""

import uuid

import pytest
from langgraph.checkpoint.memory import MemorySaver

from bo1.graph.config import create_deliberation_graph
from bo1.graph.state import create_initial_state
from bo1.models.problem import Problem


@pytest.mark.integration
class TestCheckpointRecovery:
    """Test suite for checkpoint recovery functionality."""

    @pytest.fixture
    def problem(self):
        """Create a test problem."""
        return Problem(
            title="Test Investment Decision",
            description="Should we invest $50K in AI automation?",
            context="Small business with 10 employees, $500K annual revenue",
        )

    @pytest.fixture
    def session_id(self):
        """Generate a unique session ID."""
        return str(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_checkpoint_created_after_state_update(self, problem, session_id):
        """Test that checkpoint is created after state update."""
        # Create graph with in-memory checkpointer for testing
        checkpointer = MemorySaver()
        graph = create_deliberation_graph(checkpointer=checkpointer)

        # Create initial state
        initial_state = create_initial_state(session_id=session_id, problem=problem, max_rounds=3)

        config = {"configurable": {"thread_id": session_id}}

        # Update state directly (simulating node execution)
        updated_state = dict(initial_state)
        updated_state["round_number"] = 2
        updated_state["phase"] = "discussion"

        # Save state to create checkpoint
        await graph.aupdate_state(config, updated_state)

        # Verify checkpoint exists
        checkpoint_state = await graph.aget_state(config)
        assert checkpoint_state is not None
        assert checkpoint_state.values is not None
        assert checkpoint_state.values["round_number"] == 2
        assert checkpoint_state.values["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self, problem, session_id):
        """Test that deliberation can resume from a checkpoint."""
        # Create graph with in-memory checkpointer
        checkpointer = MemorySaver()
        graph = create_deliberation_graph(checkpointer=checkpointer)

        # Create initial state
        initial_state = create_initial_state(session_id=session_id, problem=problem, max_rounds=3)

        config = {"configurable": {"thread_id": session_id}}

        # First checkpoint: Simulate round 1 completion
        state_round_1 = dict(initial_state)
        state_round_1["round_number"] = 1
        state_round_1["phase"] = "discussion"

        await graph.aupdate_state(config, state_round_1)

        # Verify checkpoint was saved
        checkpoint_state = await graph.aget_state(config)
        assert checkpoint_state is not None
        assert checkpoint_state.values is not None
        assert checkpoint_state.values.get("round_number") == 1

        # Simulate continuing: Update to round 2
        state_round_2 = dict(checkpoint_state.values)
        state_round_2["round_number"] = 2

        await graph.aupdate_state(config, state_round_2, as_node="decompose")

        # Verify we can retrieve updated state
        checkpoint_state_after = await graph.aget_state(config)
        assert checkpoint_state_after is not None
        assert checkpoint_state_after.values.get("round_number") == 2

    @pytest.mark.asyncio
    async def test_checkpoint_preserves_state(self, problem, session_id):
        """Test that checkpoint preserves all state fields."""
        # Create graph with in-memory checkpointer
        checkpointer = MemorySaver()
        graph = create_deliberation_graph(checkpointer=checkpointer)

        # Create initial state with specific values
        initial_state = create_initial_state(session_id=session_id, problem=problem, max_rounds=5)

        # Set some values we want to verify are preserved
        initial_state["round_number"] = 2
        initial_state["should_stop"] = False

        config = {"configurable": {"thread_id": session_id}}

        # Update state in graph (simulating execution)
        await graph.aupdate_state(config, initial_state)

        # Retrieve checkpoint
        checkpoint_state = await graph.aget_state(config)

        # Verify all fields are preserved
        assert checkpoint_state is not None
        assert checkpoint_state.values["session_id"] == session_id
        assert checkpoint_state.values["round_number"] == 2
        assert checkpoint_state.values["should_stop"] is False
        assert checkpoint_state.values["max_rounds"] == 5

    @pytest.mark.asyncio
    async def test_resume_with_invalid_session_id(self):
        """Test that resuming with invalid session ID fails gracefully."""
        # Create graph with in-memory checkpointer
        checkpointer = MemorySaver()
        graph = create_deliberation_graph(checkpointer=checkpointer)

        # Try to get state for non-existent session
        invalid_session_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": invalid_session_id}}

        checkpoint_state = await graph.aget_state(config)

        # Should return empty state or None for non-existent checkpoint
        # MemorySaver returns a state with empty values
        assert checkpoint_state.values == {}

    @pytest.mark.asyncio
    async def test_checkpoint_cost_tracking_preserved(self, problem, session_id):
        """Test that cost tracking is preserved across checkpoints."""
        # Create graph with in-memory checkpointer
        checkpointer = MemorySaver()
        graph = create_deliberation_graph(checkpointer=checkpointer)

        # Create initial state
        initial_state = create_initial_state(session_id=session_id, problem=problem, max_rounds=3)

        # Set metrics with cost
        from bo1.models.state import DeliberationMetrics

        initial_state["metrics"] = DeliberationMetrics(
            total_cost=1.25, total_tokens=5000, cache_hits=10
        )

        config = {"configurable": {"thread_id": session_id}}

        # Save state
        await graph.aupdate_state(config, initial_state)

        # Retrieve checkpoint
        checkpoint_state = await graph.aget_state(config)

        # Verify metrics are preserved
        assert checkpoint_state is not None
        metrics = checkpoint_state.values["metrics"]

        # Handle both dict and DeliberationMetrics object
        if hasattr(metrics, "total_cost"):
            assert metrics.total_cost == 1.25
            assert metrics.total_tokens == 5000
            assert metrics.cache_hits == 10
        else:
            assert metrics["total_cost"] == 1.25
            assert metrics["total_tokens"] == 5000
            assert metrics["cache_hits"] == 10

    @pytest.mark.asyncio
    async def test_multiple_sessions_independent(self, problem):
        """Test that multiple sessions maintain independent checkpoints."""
        # Create graph with shared checkpointer
        checkpointer = MemorySaver()
        graph = create_deliberation_graph(checkpointer=checkpointer)

        # Create two different sessions
        session_id_1 = str(uuid.uuid4())
        session_id_2 = str(uuid.uuid4())

        state_1 = create_initial_state(session_id=session_id_1, problem=problem, max_rounds=3)
        state_2 = create_initial_state(session_id=session_id_2, problem=problem, max_rounds=5)

        state_1["round_number"] = 1
        state_2["round_number"] = 2

        config_1 = {"configurable": {"thread_id": session_id_1}}
        config_2 = {"configurable": {"thread_id": session_id_2}}

        # Save both states
        await graph.aupdate_state(config_1, state_1)
        await graph.aupdate_state(config_2, state_2)

        # Retrieve both checkpoints
        checkpoint_1 = await graph.aget_state(config_1)
        checkpoint_2 = await graph.aget_state(config_2)

        # Verify they're independent
        assert checkpoint_1.values["session_id"] == session_id_1
        assert checkpoint_1.values["round_number"] == 1
        assert checkpoint_1.values["max_rounds"] == 3

        assert checkpoint_2.values["session_id"] == session_id_2
        assert checkpoint_2.values["round_number"] == 2
        assert checkpoint_2.values["max_rounds"] == 5
