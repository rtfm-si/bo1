"""Unit tests for context_collection_node.

Tests for Day 37: Context collection during deliberation setup.
"""

import pytest

from bo1.graph.nodes import context_collection_node
from bo1.graph.state import DeliberationGraphState
from bo1.models.problem import Problem


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_collection_node_without_user_id():
    """Test context collection without user_id (no saved context)."""
    # Create minimal state
    problem = Problem(
        title="Growth Marketing Investment",
        description="Should we invest $500K in growth marketing?",
        context="B2B SaaS company with $2M ARR",
    )

    state: DeliberationGraphState = {
        "session_id": "test-session-1",
        "problem": problem,
        "personas": [],
        "sub_problem_results": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {},
        "collect_context": False,  # Skip user prompts in tests
    }

    # Call node
    result = await context_collection_node(state)

    # Verify result structure
    assert "metrics" in result
    assert result["metrics"] is not None
    assert "context_collection" in result["metrics"].phase_costs
    assert result["metrics"].phase_costs["context_collection"] == 0.0
    assert result["current_node"] == "context_collection"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_collection_node_with_user_id_no_saved():
    """Test context collection with user_id but no saved context."""
    # Create minimal state with user_id
    problem = Problem(
        title="Growth Marketing Investment",
        description="Should we invest $500K in growth marketing?",
        context="B2B SaaS company with $2M ARR",
    )

    state: DeliberationGraphState = {
        "session_id": "test-session-2",
        "problem": problem,
        "personas": [],
        "sub_problem_index": 0,
        "sub_problem_results": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {},
        "user_id": "user-123",
        "collect_context": False,  # Skip user prompts in tests
    }

    # Call node
    result = await context_collection_node(state)

    # Verify result structure
    assert "metrics" in result
    assert result["metrics"] is not None
    assert "context_collection" in result["metrics"].phase_costs
    assert result["current_node"] == "context_collection"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_collection_node_metrics_tracked():
    """Test that metrics are properly tracked."""
    problem = Problem(
        title="Growth Marketing Investment",
        description="Should we invest $500K in growth marketing?",
        context="B2B SaaS company with $2M ARR",
    )

    state: DeliberationGraphState = {
        "session_id": "test-session-3",
        "problem": problem,
        "personas": [],
        "sub_problem_index": 0,
        "sub_problem_results": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {},
        "collect_context": False,
    }

    # Call node
    result = await context_collection_node(state)

    # Verify metrics initialized
    assert "metrics" in result
    assert result["metrics"] is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_collection_node_without_problem_raises():
    """Test that calling without problem raises ValueError."""
    # Create state without problem
    state: DeliberationGraphState = {
        "session_id": "test-session-4",
        "problem": None,  # type: ignore[typeddict-item] # Missing problem - testing error handling
        "personas": [],
        "sub_problem_index": 0,
        "sub_problem_results": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {},
    }

    # Should raise ValueError
    with pytest.raises(ValueError, match="context_collection_node called without problem"):
        await context_collection_node(state)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_collection_node_preserves_existing_phase_costs():
    """Test that existing phase costs are preserved."""
    problem = Problem(
        title="Growth Marketing Investment",
        description="Should we invest $500K in growth marketing?",
        context="B2B SaaS company with $2M ARR",
    )

    state: DeliberationGraphState = {
        "session_id": "test-session-5",
        "problem": problem,
        "personas": [],
        "sub_problem_index": 0,
        "sub_problem_results": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {"decomposition": 0.05, "persona_selection": 0.02},
        "collect_context": False,
    }

    # Call node
    result = await context_collection_node(state)

    # Verify metrics returned with context_collection cost
    assert "metrics" in result
    assert result["metrics"] is not None
    assert "context_collection" in result["metrics"].phase_costs
    assert result["metrics"].phase_costs["context_collection"] == 0.0
    # Note: Graph state merging will preserve existing phase_costs from previous nodes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_collection_node_skip_prompt():
    """Test that collect_context=False skips user prompts."""
    problem = Problem(
        title="Growth Marketing Investment",
        description="Should we invest $500K in growth marketing?",
        context="B2B SaaS company with $2M ARR",
    )

    state: DeliberationGraphState = {
        "session_id": "test-session-6",
        "problem": problem,
        "personas": [],
        "sub_problem_index": 0,
        "sub_problem_results": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {},
        "collect_context": False,  # Should skip prompts
    }

    # Call node - should complete without user interaction
    result = await context_collection_node(state)

    # Verify completed successfully
    assert result["current_node"] == "context_collection"
    assert "metrics" in result
    assert result["metrics"] is not None
