"""Unit tests for clarification_node.

Tests for Day 37: Clarification handling during deliberation.
"""

from unittest.mock import MagicMock, patch

import pytest

from bo1.graph.nodes import clarification_node
from bo1.graph.state import DeliberationGraphState
from bo1.models.problem import Problem


# Helper to mock interactive mode (non-headless)
def mock_interactive_mode():
    """Return patches to simulate interactive (non-headless) mode."""
    return [
        patch("bo1.graph.nodes.context.sys.stdin.isatty", return_value=True),
        patch.dict("os.environ", {"BO1_HEADLESS": ""}),
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clarification_node_without_pending():
    """Test clarification node called without pending_clarification."""
    problem = Problem(
        title="Growth Marketing Investment",
        description="Should we invest $500K in growth marketing?",
        context="B2B SaaS company with $2M ARR",
    )

    state: DeliberationGraphState = {
        "session_id": "test-session-1",
        "problem": problem,
        "personas": [],
        "sub_problem_index": 0,
        "sub_problem_results": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {},
        "pending_clarification": None,  # No pending clarification
    }

    # Call node
    result = await clarification_node(state)

    # Should return minimal result
    assert result["current_node"] == "clarification"
    assert "pending_clarification" not in result or result.get("pending_clarification") is None


@pytest.mark.unit
@pytest.mark.asyncio
@patch("sys.stdin.isatty", return_value=True)
@patch("bo1.ui.console.Console")
async def test_clarification_node_answer_immediately(mock_console_class, mock_isatty):
    """Test answering clarification immediately."""
    # Setup mock console
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_console.input.side_effect = ["1", "We have $2M ARR"]  # Choice 1 (answer), then answer

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
        "pending_clarification": {
            "question": "What is your current ARR?",
            "reason": "Need to assess marketing budget relative to revenue",
        },
    }

    # Call node
    result = await clarification_node(state)

    # Verify answer stored in business_context with timestamp
    assert "business_context" in result
    assert "clarifications" in result["business_context"]
    clarification = result["business_context"]["clarifications"]["What is your current ARR?"]
    # New format: dict with answer, timestamp, and round_number
    assert clarification["answer"] == "We have $2M ARR"
    assert "timestamp" in clarification
    assert "round_number" in clarification

    # Verify pending_clarification cleared
    assert result.get("pending_clarification") is None

    # Verify current_node set
    assert result["current_node"] == "clarification"


@pytest.mark.unit
@pytest.mark.asyncio
@patch("sys.stdin.isatty", return_value=True)
@patch("bo1.ui.console.Console")
async def test_clarification_node_pause_session(mock_console_class, mock_isatty):
    """Test pausing session for clarification."""
    # Setup mock console
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_console.input.return_value = "2"  # Choice 2 (pause)

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
        "pending_clarification": {
            "question": "What is your customer CAC?",
            "reason": "Need to compare to marketing spend",
        },
    }

    # Call node
    result = await clarification_node(state)

    # Verify session paused
    assert result.get("should_stop") is True

    # Verify pending_clarification preserved
    assert result.get("pending_clarification") is not None
    assert result["pending_clarification"]["question"] == "What is your customer CAC?"

    # Verify current_node set
    assert result["current_node"] == "clarification"


@pytest.mark.unit
@pytest.mark.asyncio
@patch("sys.stdin.isatty", return_value=True)
@patch("bo1.ui.console.Console")
async def test_clarification_node_skip_question(mock_console_class, mock_isatty):
    """Test skipping clarification question."""
    # Setup mock console
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_console.input.return_value = "3"  # Choice 3 (skip)

    problem = Problem(
        title="Growth Marketing Investment",
        description="Should we invest $500K in growth marketing?",
        context="B2B SaaS company with $2M ARR",
    )

    state: DeliberationGraphState = {
        "session_id": "test-session-4",
        "problem": problem,
        "personas": [],
        "sub_problem_index": 0,
        "sub_problem_results": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {},
        "pending_clarification": {
            "question": "What is your churn rate?",
            "reason": "Optional for analysis",
        },
    }

    # Call node
    result = await clarification_node(state)

    # Verify pending_clarification cleared
    assert result.get("pending_clarification") is None

    # Verify session NOT paused
    assert result.get("should_stop") is not True

    # Verify current_node set
    assert result["current_node"] == "clarification"


@pytest.mark.unit
@pytest.mark.asyncio
@patch("sys.stdin.isatty", return_value=True)
@patch("bo1.ui.console.Console")
async def test_clarification_node_preserves_existing_context(mock_console_class, mock_isatty):
    """Test that existing business_context is preserved when answering."""
    # Setup mock console
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_console.input.side_effect = ["1", "15% monthly"]  # Answer clarification

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
        "phase_costs": {},
        "business_context": {
            "company_name": "Acme Inc",
            "industry": "SaaS",
            "clarifications": {
                "Previous question": "Previous answer",
            },
        },
        "pending_clarification": {
            "question": "What is your growth rate?",
            "reason": "Need to assess marketing impact",
        },
    }

    # Call node
    result = await clarification_node(state)

    # Verify existing clarifications preserved (old format still supported)
    assert result["business_context"]["clarifications"]["Previous question"] == "Previous answer"

    # Verify new clarification added with new format (dict with timestamp)
    new_clarification = result["business_context"]["clarifications"]["What is your growth rate?"]
    assert new_clarification["answer"] == "15% monthly"
    assert "timestamp" in new_clarification


@pytest.mark.unit
@pytest.mark.asyncio
@patch("sys.stdin.isatty", return_value=True)
@patch("bo1.ui.console.Console")
async def test_clarification_node_handles_non_dict_context(mock_console_class, mock_isatty):
    """Test that non-dict business_context is handled gracefully."""
    # Setup mock console
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_console.input.side_effect = ["1", "B2B SaaS"]  # Answer clarification

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
        "business_context": "not a dict",  # type: ignore[typeddict-item] # Invalid format - testing error handling
        "pending_clarification": {
            "question": "What is your business model?",
            "reason": "Critical for analysis",
        },
    }

    # Call node - should handle gracefully
    result = await clarification_node(state)

    # Verify new business_context created with new format
    assert isinstance(result["business_context"], dict)
    clarification = result["business_context"]["clarifications"]["What is your business model?"]
    assert clarification["answer"] == "B2B SaaS"
    assert "timestamp" in clarification
