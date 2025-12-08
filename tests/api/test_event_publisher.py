"""Unit tests for EventPublisher (Redis PubSub).

Tests:
- Event publishing to Redis channels
- Channel naming format
- JSON serialization
- Error handling
- Timestamp and session_id injection
"""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
import redis

from backend.api.event_publisher import EventPublisher


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    return MagicMock(spec=redis.Redis)


@pytest.fixture
def publisher(mock_redis):
    """EventPublisher instance with mocked Redis."""
    return EventPublisher(mock_redis)


@patch("backend.api.event_publisher.session_repository")
def test_publish_event_basic(mock_repo, publisher, mock_redis):
    """Test basic event publishing."""
    session_id = "bo1_test123"
    event_type = "decomposition_complete"
    data = {"sub_problems": [{"id": "sp_001", "goal": "Test goal"}], "count": 1}

    publisher.publish_event(session_id, event_type, data)

    # Verify Redis publish was called
    mock_redis.publish.assert_called_once()

    # Verify channel name format
    call_args = mock_redis.publish.call_args
    channel = call_args[0][0]
    assert channel == f"events:{session_id}"


@patch("backend.api.event_publisher.session_repository")
def test_publish_event_json_serialization(mock_repo, publisher, mock_redis):
    """Test that event payload is correctly JSON serialized."""
    session_id = "bo1_test123"
    event_type = "contribution"
    data = {
        "persona_code": "CFO",
        "persona_name": "Zara Kim",
        "content": "Financial analysis...",
        "round": 1,
    }

    with patch("backend.api.event_publisher.datetime") as mock_datetime:
        mock_now = datetime(2025, 1, 21, 10, 30, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now

        publisher.publish_event(session_id, event_type, data)

        # Get published message
        call_args = mock_redis.publish.call_args
        message_str = call_args[0][1]
        message = json.loads(message_str)

        # Verify structure
        assert message["event_type"] == event_type
        assert message["session_id"] == session_id
        assert message["timestamp"] == mock_now.isoformat()
        assert message["data"] == data


def test_publish_event_adds_metadata(publisher, mock_redis):
    """Test that timestamp and session_id are automatically added."""
    session_id = "bo1_test123"
    event_type = "persona_selected"
    data = {"persona": {"code": "CFO"}}

    publisher.publish_event(session_id, event_type, data)

    # Get published message
    call_args = mock_redis.publish.call_args
    message_str = call_args[0][1]
    message = json.loads(message_str)

    # Verify metadata fields
    assert "event_type" in message
    assert "session_id" in message
    assert "timestamp" in message
    assert "data" in message

    # Verify timestamp is ISO format
    datetime.fromisoformat(message["timestamp"])  # Should not raise


def test_publish_event_error_handling(publisher, mock_redis):
    """Test that publish errors are logged but don't raise."""
    session_id = "bo1_test123"
    event_type = "contribution"
    data = {"content": "Test"}

    # Make Redis publish raise an exception
    mock_redis.publish.side_effect = redis.RedisError("Connection failed")

    # Should not raise - errors are logged and swallowed
    publisher.publish_event(session_id, event_type, data)

    # Verify Redis publish was attempted
    mock_redis.publish.assert_called_once()


def test_publish_event_json_serialization_error(publisher, mock_redis):
    """Test handling of JSON serialization errors."""
    session_id = "bo1_test123"
    event_type = "test_event"

    # Create data that can't be JSON serialized (e.g., set)
    data = {"invalid": {1, 2, 3}}  # Sets are not JSON serializable

    # Should not raise - errors are logged and swallowed
    publisher.publish_event(session_id, event_type, data)

    # Verify Redis publish was NOT called (due to JSON error)
    assert mock_redis.publish.call_count == 0


@patch("backend.api.event_publisher.session_repository")
def test_publish_multiple_events(mock_repo, publisher, mock_redis):
    """Test publishing multiple events to same session."""
    session_id = "bo1_test123"
    events = [
        ("decomposition_started", {}),
        ("decomposition_complete", {"count": 2}),
        ("persona_selected", {"persona": {"code": "CFO"}}),
    ]

    for event_type, data in events:
        publisher.publish_event(session_id, event_type, data)

    # Verify all events were published
    assert mock_redis.publish.call_count == len(events)

    # Verify all used same channel
    for call in mock_redis.publish.call_args_list:
        channel = call[0][0]
        assert channel == f"events:{session_id}"


def test_publish_event_channel_format(publisher, mock_redis):
    """Test that channel name format is correct."""
    test_cases = [
        "bo1_abc123",
        "bo1_xyz789",
        "session_with_underscores",
        "session-with-dashes",
    ]

    for session_id in test_cases:
        mock_redis.reset_mock()
        publisher.publish_event(session_id, "test_event", {})

        call_args = mock_redis.publish.call_args
        channel = call_args[0][0]
        assert channel == f"events:{session_id}"


@patch("backend.api.event_publisher.session_repository")
def test_publish_event_empty_data(mock_repo, publisher, mock_redis):
    """Test publishing event with empty data."""
    session_id = "bo1_test123"
    event_type = "decomposition_started"
    data = {}

    publisher.publish_event(session_id, event_type, data)

    # Verify event was published
    mock_redis.publish.assert_called_once()

    # Verify message structure
    call_args = mock_redis.publish.call_args
    message_str = call_args[0][1]
    message = json.loads(message_str)

    assert message["data"] == {}
    assert "timestamp" in message
    assert "session_id" in message


@patch("backend.api.event_publisher.session_repository")
def test_publish_event_complex_data(mock_repo, publisher, mock_redis):
    """Test publishing event with complex nested data."""
    session_id = "bo1_test123"
    event_type = "phase_cost_breakdown"
    data = {
        "phase_costs": {
            "decomposition": 0.0023,
            "persona_selection": 0.0015,
            "round_1": 0.0187,
        },
        "total_cost": 0.0225,
        "metadata": {"model": "claude-sonnet-4-5", "cached": True},
    }

    publisher.publish_event(session_id, event_type, data)

    # Verify Redis publish was called
    mock_redis.publish.assert_called_once()

    # Verify complex data was serialized correctly
    call_args = mock_redis.publish.call_args
    message_str = call_args[0][1]
    message = json.loads(message_str)

    assert message["data"] == data
    # Verify nested structure preserved
    assert message["data"]["phase_costs"]["decomposition"] == 0.0023
    assert message["data"]["metadata"]["cached"] is True
