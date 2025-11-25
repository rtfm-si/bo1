"""Tests for event extraction framework - registry-based extraction verification."""

import pytest

from backend.api.event_extractors import get_event_registry
from bo1.models.problem import SubProblem


@pytest.mark.unit
def test_extract_decomposition_data():
    """Test decomposition data extraction using registry."""
    registry = get_event_registry()

    output = {
        "problem": type(
            "Problem",
            (),
            {
                "sub_problems": [
                    SubProblem(
                        id="sp1",
                        goal="Test goal",
                        rationale="Test rationale",
                        context="Test context",
                        complexity_score=5,
                        dependencies=[],
                    )
                ]
            },
        )()
    }

    result = registry.extract("decomposition", output)

    assert "sub_problems" in result
    assert "count" in result
    assert result["count"] == 1
    assert result["sub_problems"][0]["id"] == "sp1"


@pytest.mark.unit
def test_extract_persona_selection_data():
    """Test persona selection data extraction using registry."""
    registry = get_event_registry()

    output = {
        "personas": [
            type("Persona", (), {"code": "ceo", "name": "CEO"})(),
            type("Persona", (), {"code": "cto", "name": "CTO"})(),
        ],
        "sub_problem_index": 0,
    }

    result = registry.extract("persona_selection", output)

    assert result["personas"] == ["ceo", "cto"]
    assert result["count"] == 2
    assert result["sub_problem_index"] == 0


@pytest.mark.unit
def test_extract_facilitator_decision_data():
    """Test facilitator decision data extraction using registry."""
    registry = get_event_registry()

    output = {
        "facilitator_decision": {
            "action": "continue",
            "reasoning": "Need more discussion",
            "next_speaker": "cto",
        },
        "round_number": 2,
        "sub_problem_index": 0,
    }

    result = registry.extract("facilitator_decision", output)

    assert result["action"] == "continue"
    assert result["reasoning"] == "Need more discussion"
    assert result["next_speaker"] == "cto"
    assert result["round"] == 2


@pytest.mark.unit
def test_extract_moderator_intervention_data():
    """Test moderator intervention data extraction using registry."""
    registry = get_event_registry()

    output = {
        "contributions": [{"persona_code": "moderator_bias", "content": "Let's focus on facts"}],
        "round_number": 3,
        "sub_problem_index": 0,
    }

    result = registry.extract("moderator_intervention", output)

    assert result["moderator_type"] == "moderator_bias"
    assert result["content"] == "Let's focus on facts"
    assert result["round"] == 3


@pytest.mark.unit
def test_extract_convergence_data():
    """Test convergence data extraction using registry."""
    registry = get_event_registry()

    output = {
        "should_stop": True,
        "stop_reason": "convergence",
        "round_number": 5,
        "max_rounds": 10,
        "sub_problem_index": 0,
        "metrics": {"convergence_score": 0.9},
    }

    result = registry.extract("convergence", output)

    assert result["converged"] is True
    assert result["score"] == 0.9
    assert result["threshold"] == 0.85
    assert result["round"] == 5


@pytest.mark.unit
def test_extract_voting_data():
    """Test voting data extraction using registry."""
    registry = get_event_registry()

    output = {
        "votes": [
            {
                "persona_code": "ceo",
                "persona_name": "CEO",
                "recommendation": "Invest",
                "confidence": 0.8,
                "reasoning": "Good ROI",
                "conditions": [],
            },
            {
                "persona_code": "cfo",
                "persona_name": "CFO",
                "recommendation": "Invest",
                "confidence": 0.9,
                "reasoning": "Strong financials",
                "conditions": [],
            },
        ],
        "sub_problem_index": 0,
    }

    result = registry.extract("voting", output)

    assert result["votes_count"] == 2
    assert result["consensus_level"] == "strong"
    assert abs(result["avg_confidence"] - 0.85) < 0.001  # Float comparison with tolerance


@pytest.mark.unit
def test_extract_synthesis_data():
    """Test synthesis data extraction using registry."""
    registry = get_event_registry()

    output = {
        "synthesis": "This is a test synthesis with exactly ten words.",
        "sub_problem_index": 0,
    }

    result = registry.extract("synthesis", output)

    assert result["synthesis"] == "This is a test synthesis with exactly ten words."
    assert result["word_count"] == 9  # Actual word count
    assert result["sub_problem_index"] == 0


@pytest.mark.unit
def test_extract_meta_synthesis_data():
    """Test meta-synthesis data extraction using registry."""
    registry = get_event_registry()

    output = {"synthesis": "Final synthesis across all sub-problems."}

    result = registry.extract("meta_synthesis", output)

    assert result["synthesis"] == "Final synthesis across all sub-problems."
    assert result["word_count"] == 5


@pytest.mark.unit
def test_extract_subproblem_started_data():
    """Test subproblem started data extraction using registry."""
    registry = get_event_registry()

    # Case 1: Multi-subproblem scenario
    output = {
        "sub_problem_index": 1,
        "current_sub_problem": type("SubProblem", (), {"id": "sp2", "goal": "Test goal"})(),
        "problem": type("Problem", (), {"sub_problems": [None, None]})(),
    }

    result = registry.extract("subproblem_started", output)

    assert result["sub_problem_index"] == 1
    assert result["sub_problem_id"] == "sp2"
    assert result["total_sub_problems"] == 2

    # Case 2: Single subproblem (should return empty dict)
    output_single = {
        "sub_problem_index": 0,
        "current_sub_problem": type("SubProblem", (), {"id": "sp1", "goal": "Test goal"})(),
        "problem": type("Problem", (), {"sub_problems": [None]})(),
    }

    result_single = registry.extract("subproblem_started", output_single)

    assert result_single == {}


@pytest.mark.unit
def test_extract_completion_data():
    """Test completion data extraction using registry."""
    registry = get_event_registry()

    output = {
        "metrics": {"total_cost": 0.15, "total_tokens": 5000},
        "round_number": 5,
        "stop_reason": "convergence",
        "contributions": [{}, {}, {}],
        "synthesis": "Final recommendation",
        "session_id": "test-session-123",
    }

    result = registry.extract("completion", output)

    assert result["session_id"] == "test-session-123"
    assert result["total_cost"] == 0.15
    assert result["total_rounds"] == 5
    assert result["total_contributions"] == 3
    assert result["stop_reason"] == "convergence"


@pytest.mark.unit
def test_registry_get_event_types():
    """Test that registry returns all registered event types."""
    registry = get_event_registry()

    event_types = registry.get_event_types()

    # Should include all standard event types
    expected_types = [
        "decomposition",
        "persona_selection",
        "facilitator_decision",
        "moderator_intervention",
        "convergence",
        "voting",
        "synthesis",
        "meta_synthesis",
        "subproblem_started",
        "subproblem_complete",
        "completion",
    ]

    for expected_type in expected_types:
        assert expected_type in event_types


@pytest.mark.unit
def test_registry_unknown_event_type():
    """Test that registry raises error for unknown event type."""
    registry = get_event_registry()

    with pytest.raises(ValueError, match="Unknown event type"):
        registry.extract("unknown_event", {})


@pytest.mark.unit
def test_registry_is_registered():
    """Test registry is_registered method."""
    registry = get_event_registry()

    assert registry.is_registered("decomposition") is True
    assert registry.is_registered("unknown_event") is False
