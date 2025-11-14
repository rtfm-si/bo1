"""Tests for LangGraph node implementations."""

import pytest

from bo1.graph.nodes import (
    decompose_node,
    initial_round_node,
    select_personas_node,
)
from bo1.graph.state import create_initial_state
from bo1.models.problem import Problem

pytestmark = pytest.mark.requires_llm


@pytest.fixture
def sample_problem():
    """Create a sample problem for testing."""
    return Problem(
        title="Marketing Budget Decision",
        description="Should I invest $50K in SEO or paid ads for my SaaS product?",
        context="Solo founder, B2B SaaS, $100K ARR, 6-month timeline",
        sub_problems=[],
    )


@pytest.fixture
def initial_state(sample_problem):
    """Create initial graph state for testing."""
    return create_initial_state(
        session_id="test_session_001",
        problem=sample_problem,
        max_rounds=5,
    )


@pytest.mark.asyncio
async def test_decompose_node(initial_state):
    """Test decompose_node creates sub-problems."""
    # Run decompose node
    updates = await decompose_node(initial_state)

    # Verify updates
    assert "problem" in updates
    assert "current_sub_problem" in updates
    assert "metrics" in updates

    # Verify sub-problems created
    problem = updates["problem"]
    assert len(problem.sub_problems) > 0
    assert len(problem.sub_problems) <= 5

    # Verify current sub-problem set
    current_sp = updates["current_sub_problem"]
    assert current_sp is not None
    assert current_sp.id == problem.sub_problems[0].id

    # Verify cost tracked
    metrics = updates["metrics"]
    assert hasattr(metrics, "phase_costs")
    assert "problem_decomposition" in metrics.phase_costs
    assert metrics.phase_costs["problem_decomposition"] > 0
    assert metrics.total_cost > 0


@pytest.mark.asyncio
async def test_select_personas_node(initial_state, sample_problem):
    """Test select_personas_node selects expert personas."""
    # First run decompose to get sub-problems
    decompose_updates = await decompose_node(initial_state)

    # Update state with decompose results
    state = {**initial_state, **decompose_updates}

    # Run select personas node
    updates = await select_personas_node(state)

    # Verify updates
    assert "personas" in updates
    assert "metrics" in updates

    # Verify personas selected
    personas = updates["personas"]
    assert len(personas) >= 3
    assert len(personas) <= 5

    # Verify persona profiles loaded
    for persona in personas:
        assert persona.code is not None
        assert persona.display_name is not None
        assert persona.system_prompt is not None

    # Verify cost tracked
    metrics = updates["metrics"]
    assert hasattr(metrics, "phase_costs")
    assert "persona_selection" in metrics.phase_costs
    assert metrics.phase_costs["persona_selection"] > 0


@pytest.mark.asyncio
async def test_initial_round_node(initial_state):
    """Test initial_round_node generates contributions."""
    # Run decompose
    decompose_updates = await decompose_node(initial_state)
    state = {**initial_state, **decompose_updates}

    # Run select personas
    select_updates = await select_personas_node(state)
    state = {**state, **select_updates}

    # Run initial round
    updates = await initial_round_node(state)

    # Verify updates
    assert "contributions" in updates
    assert "metrics" in updates
    assert "round_number" in updates

    # Verify contributions created
    contributions = updates["contributions"]
    personas = state["personas"]
    assert len(contributions) == len(personas)

    # Verify each contribution
    for contrib in contributions:
        assert contrib.persona_code is not None
        assert contrib.content is not None
        assert len(contrib.content) > 0

    # Verify round number incremented
    assert updates["round_number"] == 1

    # Verify cost tracked
    metrics = updates["metrics"]
    assert hasattr(metrics, "phase_costs")
    assert "initial_round" in metrics.phase_costs
    assert metrics.phase_costs["initial_round"] > 0


@pytest.mark.asyncio
async def test_full_linear_graph_flow(initial_state):
    """Test full linear flow: decompose → select → initial_round."""
    # Run decompose
    decompose_updates = await decompose_node(initial_state)
    state = {**initial_state, **decompose_updates}

    # Run select personas
    select_updates = await select_personas_node(state)
    state = {**state, **select_updates}

    # Run initial round
    initial_updates = await initial_round_node(state)
    final_state = {**state, **initial_updates}

    # Verify final state has all components
    assert final_state["problem"].sub_problems is not None
    assert len(final_state["problem"].sub_problems) > 0
    assert len(final_state["personas"]) > 0
    assert len(final_state["contributions"]) > 0
    assert final_state["round_number"] == 1

    # Verify total cost tracked across all phases
    metrics = final_state["metrics"]
    total_cost = metrics.total_cost
    assert total_cost > 0
    assert total_cost == sum(metrics.phase_costs.values())

    # Verify all phases have costs
    phase_costs = metrics.phase_costs
    assert "problem_decomposition" in phase_costs
    assert "persona_selection" in phase_costs
    assert "initial_round" in phase_costs
