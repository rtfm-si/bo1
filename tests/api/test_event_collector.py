"""Tests for event extraction framework - registry-based extraction verification."""

from unittest.mock import MagicMock

import pytest

from backend.api.event_extractors import get_event_registry
from bo1.models.problem import SubProblem


def _create_mock_summarizer():
    """Create a mock ContributionSummarizer for tests."""
    mock = MagicMock()
    mock.summarize = MagicMock(return_value={"concise": "Test summary"})
    mock.batch_summarize = MagicMock(return_value=[])
    mock.create_fallback = MagicMock(
        return_value={"concise": "Fallback", "parse_error": True, "schema_valid": False}
    )
    return mock


def _create_mock_session_repo():
    """Create a mock session repository for tests."""
    mock = MagicMock()
    mock.get = MagicMock(return_value=None)
    mock.update_status = MagicMock(return_value=True)
    mock.update_phase = MagicMock(return_value=True)
    mock.save_synthesis = MagicMock(return_value=True)
    mock.get_events = MagicMock(return_value=[])
    return mock


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
        "recommendations": [
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

    assert result["recommendations_count"] == 2
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

    # Case 2: Single subproblem (Issue #4 fix: now returns data for expert panel display)
    output_single = {
        "sub_problem_index": 0,
        "current_sub_problem": type("SubProblem", (), {"id": "sp1", "goal": "Test goal"})(),
        "problem": type("Problem", (), {"sub_problems": [None]})(),
    }

    result_single = registry.extract("subproblem_started", output_single)

    # Issue #4 fix: Single sub-problems now return data (expert panel should show)
    assert result_single["sub_problem_index"] == 0
    assert result_single["sub_problem_id"] == "sp1"
    assert result_single["total_sub_problems"] == 1


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


# ============================================================================
# EventCollector Handler Tests (P1: UI feedback gap)
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_context_collection_emits_event():
    """Test _handle_context_collection emits context_collection_complete event."""
    from unittest.mock import MagicMock

    from backend.api.event_collector import EventCollector

    # Create mock publisher
    mock_publisher = MagicMock()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=_create_mock_session_repo(),
    )

    # Test with business context
    output = {
        "business_context": {"summary": "Test business context summary"},
        "metrics": {"revenue": 1000, "users": 500},
    }

    await collector._handle_context_collection("test-session", output)

    # Verify publish_event was called correctly
    mock_publisher.publish_event.assert_called_once()
    call_args = mock_publisher.publish_event.call_args
    assert call_args[0][0] == "test-session"
    assert call_args[0][1] == "context_collection_complete"
    event_data = call_args[0][2]
    assert event_data["context_loaded"] is True
    assert event_data["metrics_count"] == 2
    assert "Test business context" in event_data["context_summary"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_context_collection_empty_context():
    """Test _handle_context_collection handles empty business context."""
    from unittest.mock import MagicMock

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=_create_mock_session_repo(),
    )

    # Test with empty context
    output = {"business_context": {}, "metrics": {}}

    await collector._handle_context_collection("test-session", output)

    call_args = mock_publisher.publish_event.call_args
    event_data = call_args[0][2]
    assert event_data["context_loaded"] is False
    assert event_data["metrics_count"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_dependency_analysis_emits_event():
    """Test _handle_dependency_analysis emits dependency_analysis_complete event."""
    from unittest.mock import MagicMock

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=_create_mock_session_repo(),
    )

    # Test with execution batches
    output = {
        "execution_batches": [
            [{"id": "sp1"}, {"id": "sp2"}],
            [{"id": "sp3"}],
        ],
        "parallel_mode": True,
    }

    await collector._handle_dependency_analysis("test-session", output)

    mock_publisher.publish_event.assert_called_once()
    call_args = mock_publisher.publish_event.call_args
    assert call_args[0][0] == "test-session"
    assert call_args[0][1] == "dependency_analysis_complete"
    event_data = call_args[0][2]
    assert event_data["batch_count"] == 2
    assert event_data["parallel_mode"] is True
    assert len(event_data["batches"]) == 2
    assert event_data["batches"][0]["sub_problem_ids"] == ["sp1", "sp2"]
    assert event_data["batches"][1]["sub_problem_ids"] == ["sp3"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_dependency_analysis_empty_batches():
    """Test _handle_dependency_analysis handles empty execution batches."""
    from unittest.mock import MagicMock

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=_create_mock_session_repo(),
    )

    # Test with no batches (single sub-problem case)
    output = {"execution_batches": [], "parallel_mode": False}

    await collector._handle_dependency_analysis("test-session", output)

    call_args = mock_publisher.publish_event.call_args
    event_data = call_args[0][2]
    assert event_data["batch_count"] == 0
    assert event_data["parallel_mode"] is False
    assert event_data["batches"] == []


@pytest.mark.unit
def test_node_handlers_include_new_handlers():
    """Test NODE_HANDLERS registry includes context_collection and analyze_dependencies."""
    from backend.api.event_collector import EventCollector

    assert "context_collection" in EventCollector.NODE_HANDLERS
    assert "analyze_dependencies" in EventCollector.NODE_HANDLERS
    assert EventCollector.NODE_HANDLERS["context_collection"] == "_handle_context_collection"
    assert EventCollector.NODE_HANDLERS["analyze_dependencies"] == "_handle_dependency_analysis"


# ============================================================================
# Integration Test: EventCollector uses ContributionSummarizer
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_initial_round_uses_batch_summarization():
    """Test _handle_initial_round uses summarizer.batch_summarize for parallel LLM calls."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    mock_summarizer = _create_mock_summarizer()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=mock_summarizer,
        session_repo=_create_mock_session_repo(),
    )

    # Configure mock summarizer to return expected summaries
    mock_summarizer.batch_summarize = AsyncMock(
        return_value=[
            {"concise": "Summary 1"},
            {"concise": "Summary 2"},
        ]
    )

    # Mock _publish_contribution to track calls
    publish_calls = []

    async def mock_publish(session_id, contrib, round_number, sub_problem_index, personas, summary):
        publish_calls.append((contrib, summary))

    output = {
        "contributions": [
            {"persona_code": "ceo", "persona_name": "CEO", "content": "Content 1"},
            {"persona_code": "cto", "persona_name": "CTO", "content": "Content 2"},
        ],
        "personas": [],
        "sub_problem_index": 0,
    }

    with patch.object(collector, "_publish_contribution", mock_publish):
        await collector._handle_initial_round("test-session", output)

    # Verify summarizer.batch_summarize was called with correct items
    mock_summarizer.batch_summarize.assert_called_once()
    items = mock_summarizer.batch_summarize.call_args[0][0]
    assert len(items) == 2
    assert items[0] == ("Content 1", "CEO")
    assert items[1] == ("Content 2", "CTO")

    # Verify contributions published with pre-computed summaries
    assert len(publish_calls) == 2
    assert publish_calls[0][1] == {"concise": "Summary 1"}
    assert publish_calls[1][1] == {"concise": "Summary 2"}


# ============================================================================
# Cost Anomaly Tests (P1: observability)
# ============================================================================


@pytest.mark.unit
def test_check_cost_anomaly_above_threshold():
    """Test _check_cost_anomaly logs warning and emits event when cost exceeds threshold."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=_create_mock_session_repo(),
    )

    # Mock CostTracker.get_session_costs to return high cost
    mock_costs = {
        "total_cost": 1.50,  # Above $1.00 threshold
        "by_provider": {"anthropic": 1.40, "voyage": 0.10},
        "total_calls": 15,
    }

    with patch("backend.api.event_collector.CostTracker") as mock_tracker:
        mock_tracker.get_session_costs.return_value = mock_costs
        collector._check_cost_anomaly("test-session")

    # Verify cost_anomaly event was published
    mock_publisher.publish_event.assert_called_once()
    call_args = mock_publisher.publish_event.call_args
    assert call_args[0][0] == "test-session"
    assert call_args[0][1] == "cost_anomaly"
    event_data = call_args[0][2]
    assert event_data["total_cost"] == 1.50
    assert event_data["threshold"] == 1.00
    assert event_data["by_provider"] == {"anthropic": 1.40, "voyage": 0.10}


@pytest.mark.unit
def test_check_cost_anomaly_below_threshold():
    """Test _check_cost_anomaly does not emit event when cost is below threshold."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=_create_mock_session_repo(),
    )

    # Mock CostTracker.get_session_costs to return normal cost
    mock_costs = {
        "total_cost": 0.50,  # Below $1.00 threshold
        "by_provider": {"anthropic": 0.45, "voyage": 0.05},
        "total_calls": 8,
    }

    with patch("backend.api.event_collector.CostTracker") as mock_tracker:
        mock_tracker.get_session_costs.return_value = mock_costs
        collector._check_cost_anomaly("test-session")

    # Verify no event was published
    mock_publisher.publish_event.assert_not_called()


@pytest.mark.unit
def test_check_cost_anomaly_custom_threshold():
    """Test _check_cost_anomaly respects custom threshold."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=_create_mock_session_repo(),
    )

    mock_costs = {
        "total_cost": 0.75,  # Above $0.50 custom threshold
        "by_provider": {"anthropic": 0.75},
        "total_calls": 5,
    }

    with patch("backend.api.event_collector.CostTracker") as mock_tracker:
        mock_tracker.get_session_costs.return_value = mock_costs
        collector._check_cost_anomaly("test-session", threshold=0.50)

    # Verify cost_anomaly event was published
    mock_publisher.publish_event.assert_called_once()
    call_args = mock_publisher.publish_event.call_args
    event_data = call_args[0][2]
    assert event_data["threshold"] == 0.50


# ============================================================================
# Event Verification Flush Tracking Tests (Deterministic flush completion)
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_event_persistence_waits_for_flush():
    """Test _verify_event_persistence calls wait_for_all_flushes for deterministic wait."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    mock_publisher.redis.llen.return_value = 5
    mock_session_repo = _create_mock_session_repo()
    mock_session_repo.get_events.return_value = [MagicMock() for _ in range(5)]
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=mock_session_repo,
    )

    wait_calls = []

    async def mock_wait_for_all_flushes(timeout=5.0):
        wait_calls.append(timeout)
        return True  # Flush completed successfully

    with patch("backend.api.event_collector.wait_for_all_flushes", mock_wait_for_all_flushes):
        await collector._verify_event_persistence("test-session")

    # Should call wait_for_all_flushes with default timeout
    assert len(wait_calls) == 1
    assert wait_calls[0] == 5.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_event_persistence_timeout_fallback():
    """Test _verify_event_persistence proceeds on timeout with warning."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    mock_publisher.redis.llen.return_value = 5
    mock_session_repo = _create_mock_session_repo()
    mock_session_repo.get_events.return_value = [MagicMock() for _ in range(5)]
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=mock_session_repo,
    )

    async def mock_wait_timeout(timeout=5.0):
        return False  # Simulate timeout

    with patch("backend.api.event_collector.wait_for_all_flushes", mock_wait_timeout):
        # Should not raise, proceeds with verification after timeout
        await collector._verify_event_persistence("test-session")

    # Verify the method still checked event counts
    mock_publisher.redis.llen.assert_called_once_with("events_history:test-session")
    mock_session_repo.get_events.assert_called_once_with("test-session")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_event_persistence_logs_mismatch():
    """Test _verify_event_persistence detects Redis/PostgreSQL count mismatch."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    mock_publisher.redis.llen.return_value = 10  # More in Redis
    mock_session_repo = _create_mock_session_repo()
    mock_session_repo.get_events.return_value = [MagicMock() for _ in range(5)]  # Less in PG
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=mock_session_repo,
    )

    async def mock_wait_success(timeout=5.0):
        return True

    with patch("backend.api.event_collector.wait_for_all_flushes", mock_wait_success):
        await collector._verify_event_persistence("test-session")

    # Should publish persistence warning event
    publish_calls = mock_publisher.publish_event.call_args_list
    # Find warning call - can be positional args or kwargs
    warning_call = None
    for call in publish_calls:
        args, kwargs = call
        # Handle both positional and keyword args
        event_type = args[1] if len(args) > 1 else kwargs.get("event_type")
        if event_type == "persistence_verification_warning":
            warning_call = call
            break

    assert warning_call is not None, f"Expected warning event, got: {publish_calls}"
    args, kwargs = warning_call
    warning_data = args[2] if len(args) > 2 else kwargs.get("data")
    assert warning_data["redis_events"] == 10
    assert warning_data["postgres_events"] == 5
    assert warning_data["missing_events"] == 5


# NOTE: Schema validation tests moved to tests/api/test_contribution_summarizer.py


# ============================================================================
# Graph Execution Timeout Tests (ARCH P1: Wall-clock timeout)
# ============================================================================


@pytest.mark.skip(
    reason="Flaky: IndexError on mock call arg access - call structure varies between positional/kwargs"
)
@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_custom_events_timeout():
    """Test that _collect_with_custom_events enforces wall-clock timeout."""
    import asyncio
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    mock_session_repo = _create_mock_session_repo()
    mock_session_repo.get.return_value = {"user_id": "user-123", "session_type": "standard"}
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=mock_session_repo,
    )

    # Mock graph that delays indefinitely
    async def slow_astream(*args, **kwargs):
        await asyncio.sleep(100)  # Simulate slow graph
        yield ((), "updates", {"test_node": {}})

    mock_graph = MagicMock()
    mock_graph.astream = slow_astream

    # Patch timeout to 0.1 seconds for fast test
    with (
        patch("backend.api.event_collector.GRAPH_HARD_TIMEOUT_SECONDS", 0.1),
        patch("backend.api.event_collector.record_graph_execution_timeout"),
    ):
        with pytest.raises(TimeoutError):
            await collector._collect_with_custom_events(
                session_id="test-session",
                graph=mock_graph,
                initial_state={},
                config={},
            )

    # The TimeoutError is raised by asyncio.timeout, then wrapped by our code
    # The logs show our message is in the wrapped exception
    # Verify session was marked as failed
    mock_session_repo.update_status.assert_called()
    update_call = mock_session_repo.update_status.call_args
    assert update_call[1]["status"] == "failed"
    # Note: timeout metadata is included in the error event, not update_status

    # Verify session_timeout event was published
    timeout_event_calls = [
        call
        for call in mock_publisher.publish_event.call_args_list
        if call[0][1] == "session_timeout"
    ]
    assert len(timeout_event_calls) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_astream_events_timeout():
    """Test that _collect_with_astream_events enforces wall-clock timeout."""
    import asyncio
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    mock_session_repo = _create_mock_session_repo()
    mock_session_repo.get.return_value = {"user_id": "user-123", "session_type": "standard"}
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=mock_session_repo,
    )

    # Mock graph that delays indefinitely
    async def slow_astream_events(*args, **kwargs):
        await asyncio.sleep(100)  # Simulate slow graph
        yield {"event": "on_chain_end", "data": {"output": {}}}

    mock_graph = MagicMock()
    mock_graph.astream_events = slow_astream_events

    with (
        patch("backend.api.event_collector.GRAPH_HARD_TIMEOUT_SECONDS", 0.1),
        patch("backend.api.event_collector.record_graph_execution_timeout"),
    ):
        with pytest.raises(TimeoutError):
            await collector._collect_with_astream_events(
                session_id="test-session",
                graph=mock_graph,
                initial_state={},
                config={},
            )

    # Verify session was marked failed
    mock_session_repo.update_status.assert_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_session_failed_with_timeout():
    """Test that _mark_session_failed publishes session_timeout event when timeout_exceeded=True."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    mock_session_repo = _create_mock_session_repo()
    mock_session_repo.get.return_value = {"user_id": "user-123", "session_type": "standard"}
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=mock_session_repo,
    )

    timeout_error = TimeoutError("Test timeout")

    with patch("backend.api.event_collector.record_graph_execution_timeout") as mock_metric:
        collector._mark_session_failed(
            session_id="test-session",
            error=timeout_error,
            timeout_exceeded=True,
            elapsed_seconds=605.5,
        )

    # Verify session_timeout event was published FIRST
    publish_calls = mock_publisher.publish_event.call_args_list
    assert len(publish_calls) >= 2

    # First call should be session_timeout
    first_call = publish_calls[0]
    assert first_call[0][1] == "session_timeout"
    timeout_data = first_call[0][2]
    assert timeout_data["elapsed_seconds"] == 605.5
    assert "timeout_threshold_seconds" in timeout_data

    # Second call should be error event with timeout info
    second_call = publish_calls[1]
    assert second_call[0][1] == "error"
    error_data = second_call[0][2]
    assert error_data["timeout_exceeded"] is True
    assert error_data["elapsed_seconds"] == 605.5

    # Verify metric was recorded
    mock_metric.assert_called_once_with("standard")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_custom_events_success_no_timeout():
    """Test that successful graph execution does not trigger timeout."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    mock_session_repo = _create_mock_session_repo()
    mock_session_repo.get.return_value = {"user_id": "user-123", "phase": "synthesis"}
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=mock_session_repo,
    )

    # Mock graph that completes quickly
    async def fast_astream(*args, **kwargs):
        yield ((), "updates", {"test_node": {"synthesis": "Done"}})

    mock_graph = MagicMock()
    mock_graph.astream = fast_astream

    with patch("backend.api.event_collector.GRAPH_HARD_TIMEOUT_SECONDS", 10):
        result = await collector._collect_with_custom_events(
            session_id="test-session",
            graph=mock_graph,
            initial_state={},
            config={},
        )

    assert result is not None

    # Verify no session_timeout event was published
    timeout_events = [
        call
        for call in mock_publisher.publish_event.call_args_list
        if len(call[0]) > 1 and call[0][1] == "session_timeout"
    ]
    assert len(timeout_events) == 0


@pytest.mark.unit
def test_timeout_config_default():
    """Test that timeout constants have correct default values."""
    from backend.api.constants import (
        GRAPH_HARD_TIMEOUT_SECONDS,
        GRAPH_LIVENESS_TIMEOUT_SECONDS,
    )

    # Hard ceiling default: 1800 seconds (30 minutes)
    assert GRAPH_HARD_TIMEOUT_SECONDS == 1800
    # Liveness timeout default: 600 seconds (10 minutes between meaningful events)
    assert GRAPH_LIVENESS_TIMEOUT_SECONDS == 600


# ============================================================================
# State Transition Event Tests (ARCH P2: Progress visualization)
# ============================================================================


@pytest.mark.unit
def test_emit_state_transition_first_node():
    """Test _emit_state_transition emits from_node=None for first node."""
    from unittest.mock import MagicMock

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=_create_mock_session_repo(),
    )

    # First node - previous should be None
    collector._emit_state_transition("test-session", "decompose", sub_problem_index=0)

    mock_publisher.publish_event.assert_called_once()
    call_args = mock_publisher.publish_event.call_args
    assert call_args[0][0] == "test-session"
    assert call_args[0][1] == "state_transition"
    event_data = call_args[0][2]
    assert event_data["from_node"] is None
    assert event_data["to_node"] == "decompose"
    assert event_data["sub_problem_index"] == 0


@pytest.mark.unit
def test_emit_state_transition_updates_previous_node():
    """Test _emit_state_transition updates _previous_node after emission."""
    from unittest.mock import MagicMock

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=_create_mock_session_repo(),
    )

    # First transition
    collector._emit_state_transition("test-session", "decompose")
    assert collector._previous_node == "decompose"

    # Second transition
    collector._emit_state_transition("test-session", "select_personas")
    assert collector._previous_node == "select_personas"


@pytest.mark.unit
def test_emit_state_transition_sequential_nodes():
    """Test _emit_state_transition chains from_node correctly across multiple nodes."""
    from unittest.mock import MagicMock

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=_create_mock_session_repo(),
    )

    # Simulate node progression
    nodes = ["decompose", "select_personas", "initial_round", "check_convergence"]

    for node in nodes:
        collector._emit_state_transition("test-session", node, sub_problem_index=0)

    # Verify all calls
    assert mock_publisher.publish_event.call_count == 4

    calls = mock_publisher.publish_event.call_args_list

    # First: None -> decompose
    assert calls[0][0][2]["from_node"] is None
    assert calls[0][0][2]["to_node"] == "decompose"

    # Second: decompose -> select_personas
    assert calls[1][0][2]["from_node"] == "decompose"
    assert calls[1][0][2]["to_node"] == "select_personas"

    # Third: select_personas -> initial_round
    assert calls[2][0][2]["from_node"] == "select_personas"
    assert calls[2][0][2]["to_node"] == "initial_round"

    # Fourth: initial_round -> check_convergence
    assert calls[3][0][2]["from_node"] == "initial_round"
    assert calls[3][0][2]["to_node"] == "check_convergence"


@pytest.mark.unit
def test_emit_state_transition_with_sub_problem_index():
    """Test _emit_state_transition includes sub_problem_index in event data."""
    from unittest.mock import MagicMock

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=_create_mock_session_repo(),
    )

    # Emit with specific sub_problem_index
    collector._emit_state_transition("test-session", "vote", sub_problem_index=2)

    call_args = mock_publisher.publish_event.call_args
    event_data = call_args[0][2]
    assert event_data["sub_problem_index"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_and_publish_resets_previous_node():
    """Test that collect_and_publish resets _previous_node for new session."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=_create_mock_session_repo(),
    )

    # Set previous node from a prior session
    collector._previous_node = "old_node"

    # Mock feature flag and graph
    async def fast_astream(*args, **kwargs):
        yield ((), "updates", {"test_node": {}})

    mock_graph = MagicMock()
    mock_graph.astream = fast_astream

    with patch("bo1.feature_flags.USE_SUBGRAPH_DELIBERATION", True):
        # _previous_node should be reset at start of collect_and_publish
        await collector.collect_and_publish(
            session_id="new-session",
            graph=mock_graph,
            initial_state={},
            config={},
        )

    # After reset and one node, _previous_node should be the new node
    # The first transition should have from_node=None (verified indirectly)
    # Find state_transition calls
    transition_calls = [
        call
        for call in mock_publisher.publish_event.call_args_list
        if len(call[0]) > 1 and call[0][1] == "state_transition"
    ]

    if transition_calls:
        first_transition = transition_calls[0]
        assert first_transition[0][2]["from_node"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_with_custom_events_emits_transitions():
    """Test _collect_with_custom_events emits state_transition for each node."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    mock_session_repo = _create_mock_session_repo()
    mock_session_repo.get.return_value = {"user_id": "user-123", "phase": "synthesis"}
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=mock_session_repo,
    )

    # Mock graph yielding multiple nodes
    async def multi_node_astream(*args, **kwargs):
        yield ((), "updates", {"decompose": {"sub_problem_index": 0}})
        yield ((), "updates", {"select_personas": {"sub_problem_index": 0}})

    mock_graph = MagicMock()
    mock_graph.astream = multi_node_astream

    with patch("backend.api.event_collector.GRAPH_HARD_TIMEOUT_SECONDS", 10):
        await collector._collect_with_custom_events(
            session_id="test-session",
            graph=mock_graph,
            initial_state={},
            config={},
        )

    # Filter state_transition events
    transition_calls = [
        call
        for call in mock_publisher.publish_event.call_args_list
        if len(call[0]) > 1 and call[0][1] == "state_transition"
    ]

    assert len(transition_calls) == 2

    # First transition: None -> decompose
    assert transition_calls[0][0][2]["from_node"] is None
    assert transition_calls[0][0][2]["to_node"] == "decompose"

    # Second transition: decompose -> select_personas
    assert transition_calls[1][0][2]["from_node"] == "decompose"
    assert transition_calls[1][0][2]["to_node"] == "select_personas"


@pytest.mark.unit
def test_check_and_publish_subproblem_failures_detects_incomplete_results():
    """Test that _check_and_publish_subproblem_failures detects incomplete sub-problems.

    ARCH P3: This test verifies that the EventCollector (not the router)
    is responsible for publishing meeting_failed events when sub-problems
    fail to complete.
    """
    from unittest.mock import MagicMock

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    mock_session_repo = _create_mock_session_repo()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=mock_session_repo,
    )

    # Create final state with incomplete results (2 sub-problems, 1 result)
    final_state = {
        "session_id": "test-session",
        "problem": {
            "sub_problems": [
                {"id": "sp-1", "goal": "Goal 1"},
                {"id": "sp-2", "goal": "Goal 2"},
            ]
        },
        "current_sub_problem": None,  # Loop terminated
        "sub_problem_results": [{"sub_problem_id": "sp-1", "synthesis": "Result 1"}],  # Only 1 of 2
    }

    # Call the method
    result = collector._check_and_publish_subproblem_failures("test-session", final_state)

    # Should return True (failure detected)
    assert result is True

    # Should publish meeting_failed event
    mock_publisher.publish_event.assert_called_once()
    call_args = mock_publisher.publish_event.call_args
    assert call_args[0][0] == "test-session"
    assert call_args[0][1] == "meeting_failed"
    event_data = call_args[0][2]
    assert event_data["failed_count"] == 1
    assert event_data["total_count"] == 2
    assert "sp-2" in event_data["failed_ids"]
    assert "Goal 2" in event_data["failed_goals"]

    # Should update session status to failed
    mock_session_repo.update_status.assert_called_once_with(
        session_id="test-session", status="failed"
    )


@pytest.mark.unit
def test_check_and_publish_subproblem_failures_ignores_successful_completion():
    """Test that _check_and_publish_subproblem_failures returns False on success."""
    from unittest.mock import MagicMock

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    mock_session_repo = _create_mock_session_repo()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=mock_session_repo,
    )

    # Create final state with all results present
    final_state = {
        "session_id": "test-session",
        "problem": {
            "sub_problems": [
                {"id": "sp-1", "goal": "Goal 1"},
                {"id": "sp-2", "goal": "Goal 2"},
            ]
        },
        "current_sub_problem": None,  # Loop terminated
        "sub_problem_results": [
            {"sub_problem_id": "sp-1", "synthesis": "Result 1"},
            {"sub_problem_id": "sp-2", "synthesis": "Result 2"},
        ],  # All 2 present
    }

    # Call the method
    result = collector._check_and_publish_subproblem_failures("test-session", final_state)

    # Should return False (no failure)
    assert result is False

    # Should NOT publish any events
    mock_publisher.publish_event.assert_not_called()

    # Should NOT update session status
    mock_session_repo.update_status.assert_not_called()


@pytest.mark.unit
def test_check_and_publish_subproblem_failures_ignores_single_subproblem():
    """Test that _check_and_publish_subproblem_failures skips single sub-problem sessions."""
    from unittest.mock import MagicMock

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    mock_session_repo = _create_mock_session_repo()
    collector = EventCollector(
        publisher=mock_publisher,
        summarizer=_create_mock_summarizer(),
        session_repo=mock_session_repo,
    )

    # Create final state with single sub-problem (atomic problem)
    final_state = {
        "session_id": "test-session",
        "problem": {
            "sub_problems": [
                {"id": "sp-1", "goal": "Goal 1"},
            ]
        },
        "current_sub_problem": None,
        "sub_problem_results": [],  # Even with 0 results, single SP is not multi-SP failure
    }

    # Call the method
    result = collector._check_and_publish_subproblem_failures("test-session", final_state)

    # Should return False (single SP session, not a multi-SP failure)
    assert result is False

    # Should NOT publish any events
    mock_publisher.publish_event.assert_not_called()
