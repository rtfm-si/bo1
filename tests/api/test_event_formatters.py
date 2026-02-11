"""Unit tests for SSE event formatter functions.

Tests all event formatters to ensure they produce correct SSE format
and include all required data fields.
"""

from backend.api.events import (
    SSE_EVENT_VERSION,
    complete_event,
    contribution_event,
    convergence_event,
    decomposition_complete_event,
    decomposition_started_event,
    error_event,
    facilitator_decision_event,
    persona_vote_event,
    session_started_event,
    synthesis_complete_event,
    voting_started_event,
)


def test_session_started_event():
    """Test session_started event formatter."""
    result = session_started_event(
        session_id="bo1_test123",
        problem_statement="Test problem",
        max_rounds=10,
        user_id="user_xyz",
    )

    assert result.startswith("event: session_started\n")
    assert "data: " in result
    assert "bo1_test123" in result
    assert "Test problem" in result


def test_decomposition_started_event():
    """Test decomposition_started event formatter."""
    result = decomposition_started_event(session_id="bo1_test123")

    assert result.startswith("event: decomposition_started\n")
    assert "data: " in result
    assert "bo1_test123" in result


def test_decomposition_complete_event():
    """Test decomposition_complete event formatter."""
    sub_problems = [
        {
            "id": "sp_001",
            "goal": "Test goal 1",
            "rationale": "Test rationale 1",
            "complexity_score": 7,
            "dependencies": [],
        },
    ]

    result = decomposition_complete_event(session_id="bo1_test123", sub_problems=sub_problems)

    assert result.startswith("event: decomposition_complete\n")
    assert "data: " in result
    assert "sp_001" in result
    assert '"count": 1' in result


def test_contribution_event():
    """Test contribution event formatter."""
    result = contribution_event(
        session_id="bo1_test123",
        persona_code="CFO",
        persona_name="Zara Kim",
        contribution="Financial analysis...",
        round_number=1,
    )

    assert result.startswith("event: contribution\n")
    assert "data: " in result
    assert "CFO" in result
    assert "Financial analysis..." in result


def test_facilitator_decision_event():
    """Test facilitator_decision event formatter."""
    result = facilitator_decision_event(
        session_id="bo1_test123",
        action="continue",
        reasoning="Need more discussion",
        round_number=2,
    )

    assert result.startswith("event: facilitator_decision\n")
    assert "data: " in result
    assert "continue" in result
    assert "Need more discussion" in result


def test_convergence_event():
    """Test convergence event formatter."""
    result = convergence_event(
        session_id="bo1_test123",
        score=0.73,
        converged=False,
        round_number=3,
    )

    assert result.startswith("event: convergence\n")
    assert "data: " in result
    assert "0.73" in result


def test_voting_started_event():
    """Test voting_started event formatter."""
    result = voting_started_event(session_id="bo1_test123", experts=["CFO", "CTO", "OPER"])

    assert result.startswith("event: voting_started\n")
    assert "data: " in result
    assert "CFO" in result


def test_persona_vote_event():
    """Test persona_vote event formatter."""
    result = persona_vote_event(
        session_id="bo1_test123",
        persona_code="CFO",
        persona_name="Zara Kim",
        recommendation="Invest with phased rollout",
        confidence=0.85,
        reasoning="ROI analysis positive",
        conditions=["Secure executive buy-in", "Establish KPIs"],
    )

    assert result.startswith("event: persona_vote\n")
    assert "data: " in result
    assert "Invest with phased rollout" in result
    assert "0.85" in result


def test_synthesis_complete_event():
    """Test synthesis_complete event formatter."""
    result = synthesis_complete_event(
        session_id="bo1_test123",
        synthesis="# Final Recommendation\n\nInvest...",
        word_count=1250,
    )

    assert result.startswith("event: synthesis_complete\n")
    assert "data: " in result
    assert "Final Recommendation" in result


def test_complete_event():
    """Test complete event formatter."""
    result = complete_event(
        session_id="bo1_test123",
        final_output="Synthesis complete",
        total_cost=0.1004,
        total_rounds=5,
    )

    assert result.startswith("event: complete\n")
    assert "data: " in result
    assert "0.1004" in result


def test_error_event():
    """Test error event formatter."""
    result = error_event(
        session_id="bo1_test123",
        error="Redis connection timeout",
        error_type="ConnectionError",
    )

    assert result.startswith("event: error\n")
    assert "data: " in result
    assert "Redis connection timeout" in result
    assert "ConnectionError" in result


def test_sse_format_compliance():
    """Test that all formatters produce valid SSE format."""
    # Test a few key formatters
    formatters_and_calls = [
        session_started_event(
            session_id="test",
            problem_statement="p",
            max_rounds=5,
            user_id="u",
        ),
        decomposition_started_event(session_id="test"),
        convergence_event(
            session_id="test",
            score=0.5,
            converged=False,
            round_number=1,
        ),
    ]

    for result in formatters_and_calls:
        lines = result.split("\n")

        # Check SSE format
        assert lines[0].startswith("event: "), "Invalid SSE format"
        assert any(line.startswith("data: ") for line in lines), "Missing data field"
        assert result.endswith("\n\n"), "Missing double newline"


def test_all_events_have_session_id():
    """Test that all events include session_id in the data."""
    import json

    test_session = "test_session_123"

    # Test various events
    events = [
        session_started_event(test_session, "Problem", 5, "user"),
        decomposition_started_event(test_session),
        contribution_event(test_session, "CFO", "Zara", "Content", 1),
        complete_event(test_session, "Done", 0.1, 5),
    ]

    for event in events:
        # Extract data field
        data_line = [line for line in event.split("\n") if line.startswith("data: ")][0]
        data_json = data_line[6:]  # Remove "data: " prefix
        data = json.loads(data_json)

        assert "session_id" in data
        assert data["session_id"] == test_session


def test_all_events_have_timestamp():
    """Test that all events include timestamp."""
    import json

    events = [
        session_started_event("test", "Problem", 5, "user"),
        decomposition_started_event("test"),
        contribution_event("test", "CFO", "Zara", "Content", 1),
    ]

    for event in events:
        data_line = [line for line in event.split("\n") if line.startswith("data: ")][0]
        data_json = data_line[6:]
        data = json.loads(data_json)

        assert "timestamp" in data
        # Verify timestamp is ISO format
        from datetime import datetime

        datetime.fromisoformat(data["timestamp"])  # Should not raise


def test_format_sse_event_includes_version():
    """Test that format_sse_event includes event_version in payload (P1: SSE versioning)."""
    import json

    from backend.api.events import SSE_EVENT_VERSION, format_sse_event

    result = format_sse_event("test_event", {"message": "hello"})

    # Parse the data JSON
    data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
    data_json = data_line[6:]
    data = json.loads(data_json)

    # Verify event_version is present and correct
    assert "event_version" in data
    assert data["event_version"] == SSE_EVENT_VERSION
    assert data["message"] == "hello"


def test_all_events_include_version():
    """Test that all event formatters include event_version."""
    import json

    events = [
        session_started_event("test", "Problem", 5, "user"),
        decomposition_started_event("test"),
        contribution_event("test", "CFO", "Zara", "Content", 1),
        error_event("test", "Test error"),
        complete_event("test", "Final output", 0.25, 5),
    ]

    for event in events:
        data_line = [line for line in event.split("\n") if line.startswith("data: ")][0]
        data_json = data_line[6:]
        data = json.loads(data_json)

        assert "event_version" in data, f"event_version missing in event: {event[:50]}..."
        assert data["event_version"] == SSE_EVENT_VERSION
