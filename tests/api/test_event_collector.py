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
    collector = EventCollector(publisher=mock_publisher)

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
    collector = EventCollector(publisher=mock_publisher)

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
    collector = EventCollector(publisher=mock_publisher)

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
    collector = EventCollector(publisher=mock_publisher)

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
# Batch Summarization Tests (PERF: P1 parallel summarization)
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_summarize_contributions_parallel():
    """Test _batch_summarize_contributions runs summaries in parallel."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(publisher=mock_publisher)

    # Mock _summarize_contribution to return unique summaries
    async def mock_summarize(content, name):
        return {"concise": f"Summary for {name}", "looking_for": "", "value_added": ""}

    with patch.object(collector, "_summarize_contribution", side_effect=mock_summarize):
        items = [
            ("Content 1", "Expert A"),
            ("Content 2", "Expert B"),
            ("Content 3", "Expert C"),
        ]

        results = await collector._batch_summarize_contributions(items)

        assert len(results) == 3
        assert results[0]["concise"] == "Summary for Expert A"
        assert results[1]["concise"] == "Summary for Expert B"
        assert results[2]["concise"] == "Summary for Expert C"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_summarize_contributions_handles_partial_failures():
    """Test batch summarization handles individual failures gracefully."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(publisher=mock_publisher)

    call_count = 0

    async def mock_summarize(content, name):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise ValueError("Simulated LLM failure")
        return {"concise": f"Summary for {name}"}

    with patch.object(collector, "_summarize_contribution", side_effect=mock_summarize):
        items = [
            ("Content 1", "Expert A"),
            ("Content 2", "Expert B"),
            ("Content 3", "Expert C"),
        ]

        results = await collector._batch_summarize_contributions(items)

        # All results returned, failed one gets fallback
        assert len(results) == 3
        assert results[0]["concise"] == "Summary for Expert A"
        assert results[1].get("parse_error") is True  # Fallback has parse_error flag
        assert results[2]["concise"] == "Summary for Expert C"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_summarize_contributions_empty_list():
    """Test batch summarization handles empty input."""
    from unittest.mock import MagicMock

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(publisher=mock_publisher)

    results = await collector._batch_summarize_contributions([])

    assert results == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_initial_round_uses_batch_summarization():
    """Test _handle_initial_round uses batch summarization for parallel LLM calls."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    collector = EventCollector(publisher=mock_publisher)

    # Mock batch summarization
    mock_batch = AsyncMock(
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

    with patch.object(collector, "_batch_summarize_contributions", mock_batch):
        with patch.object(collector, "_publish_contribution", mock_publish):
            with patch("backend.api.event_collector.session_repository"):
                await collector._handle_initial_round("test-session", output)

    # Verify batch summarization was called with correct items
    mock_batch.assert_called_once()
    items = mock_batch.call_args[0][0]
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
    collector = EventCollector(publisher=mock_publisher)

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
    collector = EventCollector(publisher=mock_publisher)

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
    collector = EventCollector(publisher=mock_publisher)

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
# Event Verification Delay Tests (ARCH: P2 configurable delay)
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_event_persistence_uses_configurable_delay():
    """Test _verify_event_persistence respects event_verification_delay_seconds setting."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector

    mock_publisher = MagicMock()
    mock_publisher.redis.llen.return_value = 5
    collector = EventCollector(publisher=mock_publisher)

    # Mock session_repository
    mock_events = [MagicMock() for _ in range(5)]

    # Track sleep calls
    sleep_calls = []

    async def mock_sleep(seconds):
        sleep_calls.append(seconds)

    with patch("backend.api.event_collector.asyncio.sleep", mock_sleep):
        with patch("backend.api.event_collector.session_repository") as mock_repo:
            mock_repo.get_events.return_value = mock_events
            # Use default settings (2.0 seconds)
            await collector._verify_event_persistence("test-session")

    assert len(sleep_calls) == 1
    assert sleep_calls[0] == 2.0  # Default delay


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_event_persistence_skips_sleep_when_delay_zero():
    """Test _verify_event_persistence skips sleep when delay is 0."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector
    from bo1.config import Settings

    mock_publisher = MagicMock()
    mock_publisher.redis.llen.return_value = 5
    collector = EventCollector(publisher=mock_publisher)

    mock_events = [MagicMock() for _ in range(5)]

    sleep_calls = []

    async def mock_sleep(seconds):
        sleep_calls.append(seconds)

    # Create settings with delay=0
    mock_settings = MagicMock(spec=Settings)
    mock_settings.event_verification_delay_seconds = 0.0

    with patch("backend.api.event_collector.asyncio.sleep", mock_sleep):
        with patch("backend.api.event_collector.get_settings", return_value=mock_settings):
            with patch("backend.api.event_collector.session_repository") as mock_repo:
                mock_repo.get_events.return_value = mock_events
                await collector._verify_event_persistence("test-session")

    # Sleep should NOT be called when delay is 0
    assert len(sleep_calls) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_event_persistence_uses_custom_delay():
    """Test _verify_event_persistence uses custom delay value."""
    from unittest.mock import MagicMock, patch

    from backend.api.event_collector import EventCollector
    from bo1.config import Settings

    mock_publisher = MagicMock()
    mock_publisher.redis.llen.return_value = 5
    collector = EventCollector(publisher=mock_publisher)

    mock_events = [MagicMock() for _ in range(5)]

    sleep_calls = []

    async def mock_sleep(seconds):
        sleep_calls.append(seconds)

    # Create settings with custom delay
    mock_settings = MagicMock(spec=Settings)
    mock_settings.event_verification_delay_seconds = 0.5

    with patch("backend.api.event_collector.asyncio.sleep", mock_sleep):
        with patch("backend.api.event_collector.get_settings", return_value=mock_settings):
            with patch("backend.api.event_collector.session_repository") as mock_repo:
                mock_repo.get_events.return_value = mock_events
                await collector._verify_event_persistence("test-session")

    assert len(sleep_calls) == 1
    assert sleep_calls[0] == 0.5
