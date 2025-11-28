"""Integration tests for SSE event streaming infrastructure."""

import json

import pytest

from backend.api.event_collector import EventCollector
from backend.api.event_publisher import EventPublisher
from bo1.state.redis_manager import RedisManager


@pytest.fixture
def redis_manager():
    """Create RedisManager for testing."""
    manager = RedisManager()
    if not manager.is_available:
        pytest.skip("Redis not available")
    return manager


@pytest.fixture
def event_publisher(redis_manager):
    """Create EventPublisher for testing."""
    return EventPublisher(redis_manager.redis)


@pytest.fixture
def event_collector(event_publisher):
    """Create EventCollector for testing."""
    return EventCollector(event_publisher)


@pytest.mark.integration
def test_event_publisher_publishes_to_redis(redis_manager, event_publisher):
    """Test that EventPublisher successfully publishes events to Redis."""
    session_id = "test_session_123"
    channel = f"events:{session_id}"

    # Subscribe to the channel
    pubsub = redis_manager.redis.pubsub()
    pubsub.subscribe(channel)

    # Skip subscription confirmation message
    msg = pubsub.get_message(timeout=1.0)
    assert msg is not None
    assert msg["type"] == "subscribe"

    # Publish an event
    event_publisher.publish_event(
        session_id=session_id, event_type="test_event", data={"test": "data", "value": 123}
    )

    # Receive the event
    msg = pubsub.get_message(timeout=2.0)
    assert msg is not None
    assert msg["type"] == "message"

    # Parse the event
    payload = json.loads(msg["data"])
    assert payload["event_type"] == "test_event"
    assert payload["session_id"] == session_id
    assert payload["data"]["test"] == "data"
    assert payload["data"]["value"] == 123
    assert "timestamp" in payload

    # Cleanup
    pubsub.unsubscribe(channel)
    pubsub.close()


@pytest.mark.integration
def test_event_collector_handler_methods_exist(event_collector):
    """Test that EventCollector has all required handler methods."""
    required_handlers = [
        "_handle_decomposition",
        "_handle_persona_selection",
        "_handle_initial_round",
        "_handle_facilitator_decision",
        "_handle_parallel_round",
        "_handle_moderator",
        "_handle_convergence",
        "_handle_voting",
        "_handle_synthesis",
        "_handle_subproblem_complete",
        "_handle_meta_synthesis",
    ]

    for handler in required_handlers:
        assert hasattr(event_collector, handler), f"Missing handler: {handler}"
        assert callable(getattr(event_collector, handler))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_collector_decomposition_handler(redis_manager, event_collector):
    """Test that decomposition handler publishes correct events."""
    session_id = "test_decomp_123"
    channel = f"events:{session_id}"

    # Subscribe to the channel
    pubsub = redis_manager.redis.pubsub()
    pubsub.subscribe(channel)

    # Skip subscription confirmation
    pubsub.get_message(timeout=1.0)

    # Create mock output using actual SubProblem class
    from bo1.models.problem import SubProblem

    class MockProblem:
        def __init__(self):
            self.sub_problems = [
                SubProblem(
                    id="sp1",
                    goal="Test goal 1",
                    context="Test context 1",
                    complexity_score=5,
                ),
                SubProblem(
                    id="sp2",
                    goal="Test goal 2",
                    context="Test context 2",
                    complexity_score=6,
                ),
            ]

    output = {"problem": MockProblem()}

    # Call the handler
    await event_collector._handle_decomposition(session_id, output)

    # First, receive discussion_quality_status event (published before decomposition_complete)
    msg = pubsub.get_message(timeout=2.0)
    assert msg is not None
    assert msg["type"] == "message"
    quality_payload = json.loads(msg["data"])
    assert quality_payload["event_type"] == "discussion_quality_status"

    # Then receive decomposition_complete event
    msg = pubsub.get_message(timeout=2.0)
    assert msg is not None
    assert msg["type"] == "message"

    # Parse the completion event
    payload = json.loads(msg["data"])
    assert payload["event_type"] == "decomposition_complete"
    assert payload["session_id"] == session_id
    assert payload["data"]["count"] == 2
    assert len(payload["data"]["sub_problems"]) == 2
    assert payload["data"]["sub_problems"][0]["goal"] == "Test goal 1"

    # Cleanup
    pubsub.unsubscribe(channel)
    pubsub.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
