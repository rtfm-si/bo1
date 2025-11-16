"""Tests for LangGraph node implementations."""

import pytest

from bo1.graph.nodes import (
    decompose_node,
    initial_round_node,
    select_personas_node,
)
from bo1.graph.state import create_initial_state
from tests.utils.assertions import (
    assert_metrics_tracked,
    assert_personas_selected,
    assert_sub_problems_created,
    assert_valid_contributions,
)

pytestmark = pytest.mark.requires_llm


@pytest.fixture
def initial_state(sample_problem_marketing):
    """Create initial graph state for testing."""
    return create_initial_state(
        session_id="test_session_001",
        problem=sample_problem_marketing,
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

    # Verify sub-problems created using assertion helper
    problem = updates["problem"]
    assert_sub_problems_created(problem, min_count=1, max_count=5)

    # Verify current sub-problem set
    current_sp = updates["current_sub_problem"]
    assert current_sp is not None
    assert current_sp.id == problem.sub_problems[0].id

    # Verify cost tracked using assertion helper
    assert_metrics_tracked(updates, ["problem_decomposition"])


@pytest.mark.asyncio
async def test_select_personas_node(initial_state):
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

    # Verify personas selected using assertion helper
    personas = updates["personas"]
    assert_personas_selected(personas, min_count=3, max_count=5)

    # Verify cost tracked using assertion helper
    assert_metrics_tracked(updates, ["persona_selection"])


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

    # Verify contributions created using assertion helper
    contributions = updates["contributions"]
    personas = state["personas"]
    assert_valid_contributions(contributions, personas)

    # Verify round number incremented
    assert updates["round_number"] == 1

    # Verify cost tracked using assertion helper
    assert_metrics_tracked(updates, ["initial_round"])


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
