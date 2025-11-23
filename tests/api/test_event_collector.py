"""Tests for event_collector module - extraction logic verification."""

import pytest

from backend.api.event_collector import (
    _extract_completion_data,
    _extract_convergence_data,
    _extract_decomposition_data,
    _extract_facilitator_decision_data,
    _extract_meta_synthesis_data,
    _extract_moderator_intervention_data,
    _extract_persona_selection_data,
    _extract_subproblem_started_data,
    _extract_synthesis_data,
    _extract_voting_data,
)
from bo1.models.problem import SubProblem


@pytest.mark.unit
def test_extract_decomposition_data():
    """Test decomposition data extraction."""
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

    result = _extract_decomposition_data(output)

    assert "sub_problems" in result
    assert "count" in result
    assert result["count"] == 1
    assert result["sub_problems"][0]["id"] == "sp1"


@pytest.mark.unit
def test_extract_persona_selection_data():
    """Test persona selection data extraction."""
    output = {
        "personas": [
            type("Persona", (), {"code": "ceo", "name": "CEO"})(),
            type("Persona", (), {"code": "cto", "name": "CTO"})(),
        ],
        "sub_problem_index": 0,
    }

    result = _extract_persona_selection_data(output)

    assert result["personas"] == ["ceo", "cto"]
    assert result["count"] == 2
    assert result["sub_problem_index"] == 0


@pytest.mark.unit
def test_extract_facilitator_decision_data():
    """Test facilitator decision data extraction."""
    output = {
        "facilitator_decision": {
            "action": "continue",
            "reasoning": "Need more discussion",
            "next_speaker": "cto",
        },
        "round_number": 2,
        "sub_problem_index": 0,
    }

    result = _extract_facilitator_decision_data(output)

    assert result["action"] == "continue"
    assert result["reasoning"] == "Need more discussion"
    assert result["next_speaker"] == "cto"
    assert result["round"] == 2


@pytest.mark.unit
def test_extract_moderator_intervention_data():
    """Test moderator intervention data extraction."""
    output = {
        "contributions": [{"persona_code": "moderator_bias", "content": "Let's focus on facts"}],
        "round_number": 3,
        "sub_problem_index": 0,
    }

    result = _extract_moderator_intervention_data(output)

    assert result["moderator_type"] == "moderator_bias"
    assert result["content"] == "Let's focus on facts"
    assert result["round"] == 3


@pytest.mark.unit
def test_extract_convergence_data():
    """Test convergence data extraction."""
    output = {
        "should_stop": True,
        "stop_reason": "convergence",
        "round_number": 5,
        "max_rounds": 10,
        "sub_problem_index": 0,
        "metrics": {"convergence_score": 0.9},
    }

    result = _extract_convergence_data(output)

    assert result["converged"] is True
    assert result["score"] == 0.9
    assert result["threshold"] == 0.85
    assert result["round"] == 5


@pytest.mark.unit
def test_extract_voting_data():
    """Test voting data extraction."""
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

    result = _extract_voting_data(output)

    assert result["votes_count"] == 2
    assert result["consensus_level"] == "strong"
    assert abs(result["avg_confidence"] - 0.85) < 0.001  # Float comparison with tolerance


@pytest.mark.unit
def test_extract_synthesis_data():
    """Test synthesis data extraction."""
    output = {
        "synthesis": "This is a test synthesis with exactly ten words.",
        "sub_problem_index": 0,
    }

    result = _extract_synthesis_data(output)

    assert result["synthesis"] == "This is a test synthesis with exactly ten words."
    assert result["word_count"] == 9  # Actual word count
    assert result["sub_problem_index"] == 0


@pytest.mark.unit
def test_extract_meta_synthesis_data():
    """Test meta-synthesis data extraction."""
    output = {"synthesis": "Final synthesis across all sub-problems."}

    result = _extract_meta_synthesis_data(output)

    assert result["synthesis"] == "Final synthesis across all sub-problems."
    assert result["word_count"] == 5


@pytest.mark.unit
def test_extract_subproblem_started_data():
    """Test subproblem started data extraction."""
    # Case 1: Multi-subproblem scenario
    output = {
        "sub_problem_index": 1,
        "current_sub_problem": type("SubProblem", (), {"id": "sp2", "goal": "Test goal"})(),
        "problem": type("Problem", (), {"sub_problems": [None, None]})(),
    }

    result = _extract_subproblem_started_data(output)

    assert result["sub_problem_index"] == 1
    assert result["sub_problem_id"] == "sp2"
    assert result["total_sub_problems"] == 2

    # Case 2: Single subproblem (should return empty dict)
    output_single = {
        "sub_problem_index": 0,
        "current_sub_problem": type("SubProblem", (), {"id": "sp1", "goal": "Test goal"})(),
        "problem": type("Problem", (), {"sub_problems": [None]})(),
    }

    result_single = _extract_subproblem_started_data(output_single)

    assert result_single == {}


@pytest.mark.unit
def test_extract_completion_data():
    """Test completion data extraction."""
    output = {
        "metrics": {"total_cost": 0.15, "total_tokens": 5000},
        "round_number": 5,
        "stop_reason": "convergence",
        "contributions": [{}, {}, {}],
        "synthesis": "Final recommendation",
        "session_id": "test-session-123",
    }

    result = _extract_completion_data(output)

    assert result["session_id"] == "test-session-123"
    assert result["total_cost"] == 0.15
    assert result["total_rounds"] == 5
    assert result["total_contributions"] == 3
    assert result["stop_reason"] == "convergence"
