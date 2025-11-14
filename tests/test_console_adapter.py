"""Tests for console adapter (LangGraph interface)."""

import pytest

from bo1.interfaces.console import run_console_deliberation
from bo1.models.problem import Problem


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_console_deliberation_basic():
    """Test basic console deliberation flow."""
    problem = Problem(
        title="CRM Investment Decision",
        description="Should we invest $10K in a new CRM system?",
        context="Budget: $10K, Current CRM: spreadsheets",
    )

    # Run deliberation
    state = await run_console_deliberation(
        problem=problem, session_id=None, max_rounds=3, debug=True
    )

    # Verify state
    assert state is not None
    assert state["session_id"] is not None
    assert state["problem"] == problem
    assert state["round_number"] >= 0
    assert state["metrics"]["total_cost"] > 0

    # Should have completed initial round at minimum
    assert len(state["contributions"]) > 0
    assert len(state["personas"]) > 0


@pytest.mark.asyncio
async def test_console_deliberation_session_id():
    """Test that session ID is generated and accessible."""
    problem = Problem(
        title="Test Problem",
        description="Test problem for session ID validation",
        context="Test context",
    )

    state = await run_console_deliberation(
        problem=problem, session_id=None, max_rounds=1, debug=False
    )

    assert "session_id" in state
    assert state["session_id"] is not None
    assert isinstance(state["session_id"], str)
    assert len(state["session_id"]) > 0


@pytest.mark.asyncio
async def test_display_results_structure():
    """Test that final state has required fields for display."""
    problem = Problem(
        title="Test Problem",
        description="Test problem for display structure",
        context="Test context",
    )

    state = await run_console_deliberation(
        problem=problem, session_id=None, max_rounds=1, debug=False
    )

    # Verify all required fields for display
    assert "phase" in state
    assert "round_number" in state
    assert "metrics" in state
    # metrics is a DeliberationMetrics object, not a dict
    assert state["metrics"].total_cost >= 0
    assert "stop_reason" in state or state.get("stop_reason") is None
    assert "session_id" in state
