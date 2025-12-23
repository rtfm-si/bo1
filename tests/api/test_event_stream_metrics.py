"""Unit tests for event stream metrics (OBS-P2).

Tests for:
- bo1_event_publish_latency_seconds histogram
- bo1_event_type_published_total{event_type} counter
- bo1_event_batch_queue_depth gauge
"""

from unittest.mock import MagicMock, patch

import pytest


class TestEventPublishLatencyMetric:
    """Tests for the event publish latency histogram."""

    def test_record_event_publish_latency(self) -> None:
        """Test that publish latency is recorded in histogram."""
        from backend.api.middleware.metrics import (
            bo1_event_publish_latency_seconds,
            record_event_publish_latency,
        )

        # Get initial value
        initial_sum = bo1_event_publish_latency_seconds._sum.get()

        # Record a latency
        record_event_publish_latency(0.005)

        # Verify histogram was updated
        new_sum = bo1_event_publish_latency_seconds._sum.get()
        assert new_sum > initial_sum

    def test_record_multiple_latencies(self) -> None:
        """Test that multiple latency recordings are accumulated."""
        from backend.api.middleware.metrics import (
            bo1_event_publish_latency_seconds,
            record_event_publish_latency,
        )

        initial_sum = bo1_event_publish_latency_seconds._sum.get()

        # Record multiple latencies
        record_event_publish_latency(0.001)
        record_event_publish_latency(0.010)
        record_event_publish_latency(0.050)

        new_sum = bo1_event_publish_latency_seconds._sum.get()
        # Verify sum increased by approximately the total of all latencies
        assert new_sum >= initial_sum + 0.061


class TestEventTypeCounterMetric:
    """Tests for the event type published counter."""

    def test_record_event_type_published(self) -> None:
        """Test that event type counter is incremented."""
        from backend.api.middleware.metrics import (
            bo1_event_type_published_total,
            record_event_type_published,
        )

        # Get initial value for specific event type
        initial_count = bo1_event_type_published_total.labels(
            event_type="test_contribution"
        )._value.get()

        # Record an event
        record_event_type_published("test_contribution")

        # Verify counter was incremented
        new_count = bo1_event_type_published_total.labels(
            event_type="test_contribution"
        )._value.get()
        assert new_count == initial_count + 1

    def test_different_event_types_tracked_separately(self) -> None:
        """Test that different event types get distinct labels."""
        from backend.api.middleware.metrics import (
            bo1_event_type_published_total,
            record_event_type_published,
        )

        # Get initial values
        type_a_initial = bo1_event_type_published_total.labels(
            event_type="test_type_a"
        )._value.get()
        type_b_initial = bo1_event_type_published_total.labels(
            event_type="test_type_b"
        )._value.get()

        # Record different event types
        record_event_type_published("test_type_a")
        record_event_type_published("test_type_a")
        record_event_type_published("test_type_b")

        # Verify each counter was incremented correctly
        type_a_new = bo1_event_type_published_total.labels(event_type="test_type_a")._value.get()
        type_b_new = bo1_event_type_published_total.labels(event_type="test_type_b")._value.get()

        assert type_a_new == type_a_initial + 2
        assert type_b_new == type_b_initial + 1


class TestEventBatchQueueDepthMetric:
    """Tests for the event batch queue depth gauge."""

    def test_set_queue_depth(self) -> None:
        """Test that queue depth gauge is set correctly."""
        from backend.api.middleware.metrics import (
            bo1_event_batch_queue_depth,
            set_event_batch_queue_depth,
        )

        # Set a depth
        set_event_batch_queue_depth(25)

        # Verify gauge value
        assert bo1_event_batch_queue_depth._value.get() == 25

    def test_queue_depth_can_decrease(self) -> None:
        """Test that queue depth can decrease (after flush)."""
        from backend.api.middleware.metrics import (
            bo1_event_batch_queue_depth,
            set_event_batch_queue_depth,
        )

        # Set high depth
        set_event_batch_queue_depth(50)
        assert bo1_event_batch_queue_depth._value.get() == 50

        # Set lower depth (simulating flush)
        set_event_batch_queue_depth(10)
        assert bo1_event_batch_queue_depth._value.get() == 10

    def test_queue_depth_can_be_zero(self) -> None:
        """Test that queue depth can be set to zero."""
        from backend.api.middleware.metrics import (
            bo1_event_batch_queue_depth,
            set_event_batch_queue_depth,
        )

        set_event_batch_queue_depth(0)
        assert bo1_event_batch_queue_depth._value.get() == 0


class TestEventPublisherInstrumentation:
    """Tests for EventPublisher metric integration."""

    @pytest.fixture
    def mock_redis(self) -> MagicMock:
        """Create a mock Redis client."""
        mock = MagicMock()
        mock.rpush.return_value = 1
        mock.expire.return_value = True
        mock.publish.return_value = 1
        return mock

    def test_publish_event_records_latency_and_type(self, mock_redis: MagicMock) -> None:
        """Test that publish_event records both latency and event type metrics."""
        from backend.api.event_publisher import EventPublisher
        from backend.api.middleware.metrics import (
            bo1_event_publish_latency_seconds,
            bo1_event_type_published_total,
        )

        publisher = EventPublisher(mock_redis)

        # Get initial values
        initial_latency_sum = bo1_event_publish_latency_seconds._sum.get()
        initial_type_count = bo1_event_type_published_total.labels(
            event_type="test_round_start"
        )._value.get()

        # Publish an event
        with patch("backend.api.event_publisher.asyncio.create_task"):
            publisher.publish_event(
                session_id="test-session-123",
                event_type="test_round_start",
                data={"round": 1},
            )

        # Verify metrics were recorded
        new_latency_sum = bo1_event_publish_latency_seconds._sum.get()
        new_type_count = bo1_event_type_published_total.labels(
            event_type="test_round_start"
        )._value.get()

        # Latency sum should have increased (by at least some small amount)
        assert new_latency_sum >= initial_latency_sum
        assert new_type_count == initial_type_count + 1

    def test_multiple_event_types_tracked(self, mock_redis: MagicMock) -> None:
        """Test that multiple event types get tracked correctly."""
        from backend.api.event_publisher import EventPublisher
        from backend.api.middleware.metrics import bo1_event_type_published_total

        publisher = EventPublisher(mock_redis)

        # Get initial values
        contribution_initial = bo1_event_type_published_total.labels(
            event_type="contribution_metric_test"
        )._value.get()
        round_start_initial = bo1_event_type_published_total.labels(
            event_type="round_start_metric_test"
        )._value.get()

        # Publish different event types
        with patch("backend.api.event_publisher.asyncio.create_task"):
            publisher.publish_event("test-session", "contribution_metric_test", {"content": "test"})
            publisher.publish_event("test-session", "round_start_metric_test", {"round": 1})
            publisher.publish_event(
                "test-session", "contribution_metric_test", {"content": "test2"}
            )

        # Verify each type tracked separately
        contribution_new = bo1_event_type_published_total.labels(
            event_type="contribution_metric_test"
        )._value.get()
        round_start_new = bo1_event_type_published_total.labels(
            event_type="round_start_metric_test"
        )._value.get()

        assert contribution_new == contribution_initial + 2
        assert round_start_new == round_start_initial + 1


class TestEventBatcherQueueDepthIntegration:
    """Tests for EventBatcher queue depth metric integration."""

    def test_get_queue_depth_updates_gauge(self) -> None:
        """Test that get_queue_depth updates the Prometheus gauge."""
        from backend.api.middleware.metrics import bo1_event_batch_queue_depth
        from backend.services.event_batcher import EventBatcher

        batcher = EventBatcher()

        # Manually add some events to buffer (accessing private attr for test)
        batcher._buffer = [
            ("ses1", "type1", 1, {}),
            ("ses2", "type2", 2, {}),
            ("ses3", "type3", 3, {}),
        ]

        # Call get_queue_depth
        depth = batcher.get_queue_depth()

        # Verify both return value and gauge
        assert depth == 3
        assert bo1_event_batch_queue_depth._value.get() == 3

    def test_queue_depth_gauge_updated_on_empty_buffer(self) -> None:
        """Test that gauge is set to 0 when buffer is empty."""
        from backend.api.middleware.metrics import bo1_event_batch_queue_depth
        from backend.services.event_batcher import EventBatcher

        batcher = EventBatcher()
        batcher._buffer = []

        depth = batcher.get_queue_depth()

        assert depth == 0
        assert bo1_event_batch_queue_depth._value.get() == 0
