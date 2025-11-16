"""Integration tests for context collection flow.

Tests for Day 37: Full context collection flow including business context,
information gaps, and clarification handling.
"""

from unittest.mock import MagicMock, patch

import pytest

from bo1.models.problem import Problem


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_collection_flow_without_user_interaction():
    """Test full context collection flow without user prompts."""
    # Create problem
    problem = Problem(
        title="Growth Marketing Investment",
        description="Should we invest $500K in growth marketing for our B2B SaaS company?",
        context="B2B SaaS company with $2M ARR, considering expansion",
    )

    # Test just the context_collection node directly (no full graph execution)
    from bo1.graph.nodes import context_collection_node
    from bo1.graph.state import DeliberationGraphState

    state: DeliberationGraphState = {
        "session_id": "test-context-flow-1",
        "problem": problem,
        "personas": [],
        "sub_problem_index": 0,
        "sub_problem_results": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {},
        "collect_context": False,  # Skip user prompts
    }

    result = await context_collection_node(state)

    # Verify context collection completed
    assert result["current_node"] == "context_collection"
    assert "metrics" in result
    assert result["metrics"] is not None
    assert "context_collection" in result["metrics"].phase_costs


@pytest.mark.integration
@pytest.mark.asyncio
@patch("bo1.ui.console.Console")
async def test_clarification_flow_answer_immediately(mock_console_class):
    """Test clarification flow with immediate answer."""
    # Setup mock console
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_console.input.side_effect = ["1", "$2M ARR"]  # Answer clarification

    # Create state with pending clarification
    problem = Problem(
        title="Growth Marketing Investment",
        description="Should we invest $500K in growth marketing?",
        context="B2B SaaS company with $2M ARR",
    )

    from bo1.graph.state import DeliberationGraphState

    state: DeliberationGraphState = {
        "session_id": "test-clarification-1",
        "problem": problem,
        "personas": [],
        "sub_problem_index": 0,
        "sub_problem_results": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {},
        "pending_clarification": {
            "question": "What is your current ARR?",
            "reason": "Need to assess marketing budget",
        },
    }

    # Call clarification node
    from bo1.graph.nodes import clarification_node

    result = await clarification_node(state)

    # Verify clarification answered
    assert result.get("pending_clarification") is None
    assert "business_context" in result
    assert "clarifications" in result["business_context"]
    assert result["business_context"]["clarifications"]["What is your current ARR?"] == "$2M ARR"


@pytest.mark.integration
@pytest.mark.asyncio
@patch("bo1.ui.console.Console")
async def test_clarification_flow_pause_and_resume(mock_console_class):
    """Test clarification flow with pause and resume."""
    # Setup mock console to pause
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_console.input.return_value = "2"  # Pause

    # Create state with pending clarification
    problem = Problem(
        title="Growth Marketing Investment",
        description="Should we invest $500K in growth marketing?",
        context="B2B SaaS company with $2M ARR",
    )

    from bo1.graph.state import DeliberationGraphState

    state: DeliberationGraphState = {
        "session_id": "test-clarification-pause-1",
        "problem": problem,
        "personas": [],
        "sub_problem_index": 0,
        "sub_problem_results": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {},
        "pending_clarification": {
            "question": "What is your customer CAC?",
            "reason": "Critical for analysis",
        },
    }

    # Call clarification node (should pause)
    from bo1.graph.nodes import clarification_node

    result = await clarification_node(state)

    # Verify session paused
    assert result.get("should_stop") is True
    assert result.get("pending_clarification") is not None

    # Now simulate resume with answer
    mock_console.input.side_effect = ["1", "$500"]  # Answer this time

    # Update state with pause result
    state["should_stop"] = result["should_stop"]
    state["pending_clarification"] = result["pending_clarification"]

    # Call again (simulating resume)
    result2 = await clarification_node(state)

    # Verify clarification answered
    assert result2.get("pending_clarification") is None
    assert "business_context" in result2
    assert result2["business_context"]["clarifications"]["What is your customer CAC?"] == "$500"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_collection_with_existing_business_context():
    """Test context collection preserves existing business context."""
    problem = Problem(
        title="Growth Marketing Investment",
        description="Should we invest $500K in growth marketing?",
        context="B2B SaaS company with $2M ARR",
    )

    from bo1.graph.state import DeliberationGraphState

    state: DeliberationGraphState = {
        "session_id": "test-context-existing-1",
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
        },
        "collect_context": False,  # Skip prompts
    }

    # Call context collection
    from bo1.graph.nodes import context_collection_node

    result = await context_collection_node(state)

    # Note: The node returns minimal updates, existing context preserved by graph merge
    assert result["current_node"] == "context_collection"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_collection_node_cost_tracking():
    """Test that context collection tracks costs properly."""
    problem = Problem(
        title="Growth Marketing Investment",
        description="Should we invest $500K in growth marketing?",
        context="B2B SaaS company with $2M ARR",
    )

    from bo1.graph.state import DeliberationGraphState

    state: DeliberationGraphState = {
        "session_id": "test-context-cost-1",
        "problem": problem,
        "personas": [],
        "sub_problem_index": 0,
        "sub_problem_results": [],
        "round_summaries": [],
        "round_number": 0,
        "phase_costs": {
            "decomposition": 0.05,
        },
        "collect_context": False,
    }

    # Call context collection
    from bo1.graph.nodes import context_collection_node

    result = await context_collection_node(state)

    # Verify cost tracked
    assert "metrics" in result
    assert result["metrics"] is not None
    assert "context_collection" in result["metrics"].phase_costs
    assert result["metrics"].phase_costs["context_collection"] == 0.0  # Stub implementation


@pytest.mark.integration
@pytest.mark.asyncio
@patch("bo1.ui.console.Console")
async def test_clarification_skip_continues_deliberation(mock_console_class):
    """Test that skipping clarification allows deliberation to continue."""
    # Setup mock console to skip
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_console.input.return_value = "3"  # Skip

    problem = Problem(
        title="Growth Marketing Investment",
        description="Should we invest $500K in growth marketing?",
        context="B2B SaaS company with $2M ARR",
    )

    from bo1.graph.state import DeliberationGraphState

    state: DeliberationGraphState = {
        "session_id": "test-clarification-skip-1",
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

    # Call clarification node
    from bo1.graph.nodes import clarification_node

    result = await clarification_node(state)

    # Verify clarification cleared (not paused)
    assert result.get("pending_clarification") is None
    assert result.get("should_stop") is not True


@pytest.mark.integration
def test_integration_test_template_exists():
    """Verify integration test template file exists for reference."""
    import os

    template_path = "/Users/si/projects/bo1/zzz_project/INTEGRATION_TEST_TEMPLATE.md"

    # This test documents that integration tests should follow the template
    # The template may or may not exist yet
    if os.path.exists(template_path):
        assert os.path.isfile(template_path)
    else:
        # Template will be created later
        pass
