"""Shared test assertion helpers for Board of One.

This module provides reusable assertion functions to eliminate duplicate
test validation code across the test suite.
"""

from typing import Any

from bo1.graph.state import DeliberationGraphState
from bo1.models.persona import PersonaProfile
from bo1.models.state import ContributionMessage, DeliberationMetrics


def assert_metrics_tracked(updates: dict[str, Any], expected_phases: list[str]) -> None:
    """Assert metrics are properly tracked with expected phases.

    Args:
        updates: State updates dictionary from a node execution
        expected_phases: List of phase names that should have cost tracked

    Raises:
        AssertionError: If metrics are invalid or phases are missing
    """
    assert "metrics" in updates, "metrics key not found in updates"
    metrics = updates["metrics"]
    assert hasattr(metrics, "phase_costs"), "metrics missing phase_costs attribute"
    assert metrics.total_cost > 0, "total_cost should be positive"

    for phase in expected_phases:
        assert phase in metrics.phase_costs, f"Phase '{phase}' not found in phase_costs"
        assert metrics.phase_costs[phase] > 0, f"Phase '{phase}' cost should be positive"


def assert_phase_cost_positive(metrics: DeliberationMetrics, phase: str) -> None:
    """Assert a specific phase has positive cost.

    Args:
        metrics: DeliberationMetrics object
        phase: Phase name to check

    Raises:
        AssertionError: If phase is missing or has invalid cost
    """
    assert phase in metrics.phase_costs, f"Phase '{phase}' not found in phase_costs"
    assert metrics.phase_costs[phase] > 0, f"Phase '{phase}' cost should be positive"


def assert_valid_contributions(
    contributions: list[ContributionMessage],
    personas: list[PersonaProfile],
    min_content_length: int = 1,
) -> None:
    """Assert all contributions are valid and match persona count.

    Args:
        contributions: List of contribution messages to validate
        personas: List of personas that should have contributed
        min_content_length: Minimum content length (default: 1)

    Raises:
        AssertionError: If contributions are invalid or don't match personas
    """
    assert len(contributions) == len(personas), (
        f"Expected {len(personas)} contributions, got {len(contributions)}"
    )

    for contrib in contributions:
        assert contrib.persona_code is not None, "Contribution missing persona_code"
        assert contrib.persona_name is not None, "Contribution missing persona_name"
        assert contrib.content is not None, "Contribution missing content"
        assert len(contrib.content) >= min_content_length, (
            f"Contribution content too short: {len(contrib.content)} < {min_content_length}"
        )
        assert contrib.round_number >= 0, "Contribution round_number should be non-negative"


def assert_state_valid(state: DeliberationGraphState) -> None:
    """Assert state has all required fields and valid values.

    Args:
        state: DeliberationGraphState to validate

    Raises:
        AssertionError: If state is invalid or missing required fields
    """
    # Required fields
    assert "session_id" in state, "session_id missing from state"
    assert state["session_id"] is not None, "session_id should not be None"

    assert "problem" in state, "problem missing from state"
    assert state["problem"] is not None, "problem should not be None"

    assert "round_number" in state, "round_number missing from state"
    assert state["round_number"] >= 0, "round_number should be non-negative"

    assert "max_rounds" in state, "max_rounds missing from state"
    assert state["max_rounds"] > 0, "max_rounds should be positive"

    # Contributions should be a list (even if empty)
    assert "contributions" in state, "contributions missing from state"
    assert isinstance(state["contributions"], list), "contributions should be a list"


def assert_personas_selected(
    personas: list[PersonaProfile],
    min_count: int = 3,
    max_count: int = 5,
) -> None:
    """Assert personas were properly selected with valid data.

    Args:
        personas: List of selected personas
        min_count: Minimum expected personas (default: 3)
        max_count: Maximum expected personas (default: 5)

    Raises:
        AssertionError: If persona selection is invalid
    """
    assert len(personas) >= min_count, (
        f"Expected at least {min_count} personas, got {len(personas)}"
    )
    assert len(personas) <= max_count, f"Expected at most {max_count} personas, got {len(personas)}"

    for persona in personas:
        assert persona.code is not None, "Persona missing code"
        assert persona.display_name is not None, "Persona missing display_name"
        assert persona.system_prompt is not None, "Persona missing system_prompt"


def assert_sub_problems_created(
    problem: Any,
    min_count: int = 1,
    max_count: int = 5,
) -> None:
    """Assert sub-problems were created with valid structure.

    Args:
        problem: Problem object with sub_problems
        min_count: Minimum expected sub-problems (default: 1)
        max_count: Maximum expected sub-problems (default: 5)

    Raises:
        AssertionError: If sub-problems are invalid
    """
    assert hasattr(problem, "sub_problems"), "Problem missing sub_problems attribute"
    assert len(problem.sub_problems) >= min_count, (
        f"Expected at least {min_count} sub-problems, got {len(problem.sub_problems)}"
    )
    assert len(problem.sub_problems) <= max_count, (
        f"Expected at most {max_count} sub-problems, got {len(problem.sub_problems)}"
    )

    for sp in problem.sub_problems:
        assert sp.id is not None, "Sub-problem missing id"
        assert sp.goal is not None, "Sub-problem missing goal"
        assert len(sp.goal) > 0, "Sub-problem goal should not be empty"
