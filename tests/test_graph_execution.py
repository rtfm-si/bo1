"""Tests for full LangGraph execution."""

import pytest
from langgraph.checkpoint.memory import MemorySaver

from bo1.graph.config import create_deliberation_graph
from bo1.graph.state import create_initial_state
from tests.utils.assertions import assert_personas_selected, assert_sub_problems_created

pytestmark = pytest.mark.requires_llm


@pytest.mark.asyncio
async def test_graph_compiles():
    """Test that the graph compiles without errors."""
    # Use MemorySaver for tests instead of RedisSaver
    checkpointer = MemorySaver()
    graph = create_deliberation_graph(checkpointer=checkpointer)
    assert graph is not None


@pytest.mark.asyncio
async def test_graph_executes_end_to_end(sample_problem_marketing):
    """Test full graph execution from start to END (vote + synthesis)."""
    # Create initial state
    initial_state = create_initial_state(
        session_id="test_graph_001",
        problem=sample_problem_marketing,
        max_rounds=5,
    )

    # Create and compile graph with MemorySaver
    checkpointer = MemorySaver()
    graph = create_deliberation_graph(checkpointer=checkpointer)

    # Execute graph
    config = {"configurable": {"thread_id": "test_graph_001"}}
    result = await graph.ainvoke(initial_state, config=config)

    # Verify execution completed
    assert result is not None

    # Verify all nodes executed using assertion helpers
    assert "problem" in result
    assert_sub_problems_created(result["problem"], min_count=1, max_count=5)

    assert "personas" in result
    assert_personas_selected(result["personas"], min_count=3, max_count=5)

    assert "contributions" in result
    assert len(result["contributions"]) >= len(result["personas"])  # At least initial round

    assert result["round_number"] >= 1  # At least one round completed

    # Verify voting and synthesis completed (Day 31)
    assert "votes" in result
    assert len(result["votes"]) > 0, "Votes should be collected"

    assert "synthesis" in result
    assert result["synthesis"] is not None, "Synthesis should be generated"
    assert len(result["synthesis"]) > 100, "Synthesis should be substantive"

    # Verify cost tracking
    assert result["metrics"].total_cost > 0
    phase_costs = result["metrics"].phase_costs
    assert "problem_decomposition" in phase_costs
    assert "persona_selection" in phase_costs
    assert "initial_round" in phase_costs
    assert "voting" in phase_costs, "Voting phase should be tracked"
    assert "synthesis" in phase_costs, "Synthesis phase should be tracked"


@pytest.mark.asyncio
async def test_graph_checkpoint_saved(sample_problem):
    """Test that checkpoints are saved during execution."""
    # Create initial state
    initial_state = create_initial_state(
        session_id="test_checkpoint_001",
        problem=sample_problem,
        max_rounds=5,
    )

    # Create and compile graph with MemorySaver checkpointer
    checkpointer = MemorySaver()
    graph = create_deliberation_graph(checkpointer=checkpointer)

    # Execute graph
    config = {"configurable": {"thread_id": "test_checkpoint_001"}}
    result = await graph.ainvoke(initial_state, config=config)

    # Verify result
    assert result is not None

    # Load state from checkpoint
    loaded_state = await graph.aget_state(config)

    # Verify checkpoint contains result
    assert loaded_state is not None
    assert loaded_state.values is not None
    assert "problem" in loaded_state.values
    assert "personas" in loaded_state.values
    assert "contributions" in loaded_state.values
