"""Unit tests for event publisher Prometheus metrics.

Tests:
- record_event_persistence_batch() observes batch_size and duration
- set_event_persistence_retry_queue_depth() sets gauge
- record_event_persistence_retry() increments counter with outcome label
- _flush_batch() calls metrics on successful persistence
- get_queue_depth() updates gauge
- retry_event() records retry outcome
"""

from unittest.mock import MagicMock, patch

import pytest


class TestEventPersistenceMetrics:
    """Test event persistence Prometheus metrics in metrics.py."""

    def test_record_event_persistence_batch_observes_histogram(self):
        """Test that batch metrics are observed."""
        from backend.api.middleware.metrics import (
            bo1_event_persistence_batch_size,
            bo1_event_persistence_duration_seconds,
            record_event_persistence_batch,
        )

        # Get initial sample count
        initial_batch_count = bo1_event_persistence_batch_size._sum._value
        initial_duration_count = bo1_event_persistence_duration_seconds._sum._value

        record_event_persistence_batch(batch_size=10, duration_seconds=0.25)

        # Verify histograms were observed (sum increases)
        assert bo1_event_persistence_batch_size._sum._value > initial_batch_count
        assert bo1_event_persistence_duration_seconds._sum._value > initial_duration_count

    def test_set_event_persistence_retry_queue_depth(self):
        """Test that retry queue depth gauge is set."""
        from backend.api.middleware.metrics import (
            bo1_event_persistence_retry_queue_depth,
            set_event_persistence_retry_queue_depth,
        )

        set_event_persistence_retry_queue_depth(15)
        assert bo1_event_persistence_retry_queue_depth._value._value == 15

        set_event_persistence_retry_queue_depth(0)
        assert bo1_event_persistence_retry_queue_depth._value._value == 0

    def test_record_event_persistence_retry_success(self):
        """Test retry counter increments with success label."""
        from backend.api.middleware.metrics import (
            bo1_event_persistence_retries_total,
            record_event_persistence_retry,
        )

        initial = bo1_event_persistence_retries_total.labels(outcome="success")._value._value
        record_event_persistence_retry(success=True)
        assert (
            bo1_event_persistence_retries_total.labels(outcome="success")._value._value
            == initial + 1
        )

    def test_record_event_persistence_retry_failure(self):
        """Test retry counter increments with failure label."""
        from backend.api.middleware.metrics import (
            bo1_event_persistence_retries_total,
            record_event_persistence_retry,
        )

        initial = bo1_event_persistence_retries_total.labels(outcome="failure")._value._value
        record_event_persistence_retry(success=False)
        assert (
            bo1_event_persistence_retries_total.labels(outcome="failure")._value._value
            == initial + 1
        )


class TestFlushBatchMetrics:
    """Test _flush_batch() calls metrics."""

    @pytest.fixture
    def mock_session_repository(self):
        """Mock the session repository."""
        with patch("backend.api.event_publisher.session_repository") as mock:
            mock.save_events_batch.return_value = 5
            yield mock

    @pytest.fixture
    def mock_metrics(self):
        """Mock the metrics module used by event_publisher."""
        with patch("backend.api.event_publisher.metrics") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_flush_batch_records_persistence_metrics(
        self, mock_session_repository, mock_metrics
    ):
        """Test that _flush_batch records persistence metrics on success."""
        from backend.api import event_publisher
        from backend.api.event_publisher import _flush_batch

        # Reset global state
        event_publisher._batch_buffer = [
            ("session1", "event_type1", 1, {"data": "test1"}),
            ("session1", "event_type2", 2, {"data": "test2"}),
        ]
        event_publisher._batch_lock = None  # Force fresh lock

        with patch(
            "backend.api.middleware.metrics.record_event_persistence_batch"
        ) as mock_record_batch:
            await _flush_batch()

            # Verify metrics were recorded
            mock_record_batch.assert_called_once()
            call_args = mock_record_batch.call_args
            assert call_args[0][0] == 2  # batch_size
            assert call_args[0][1] >= 0  # duration_seconds

    @pytest.mark.asyncio
    async def test_flush_batch_empty_buffer_no_metrics(self, mock_session_repository, mock_metrics):
        """Test that empty buffer does not record metrics."""
        from backend.api import event_publisher
        from backend.api.event_publisher import _flush_batch

        event_publisher._batch_buffer = []
        event_publisher._batch_lock = None

        with patch(
            "backend.api.middleware.metrics.record_event_persistence_batch"
        ) as mock_record_batch:
            await _flush_batch()

            # Verify no metrics recorded
            mock_record_batch.assert_not_called()


class TestGetQueueDepthMetrics:
    """Test get_queue_depth() updates Prometheus gauge."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock = MagicMock()
        mock.zcard.return_value = 7
        return mock

    @pytest.mark.asyncio
    async def test_get_queue_depth_updates_gauge(self, mock_redis):
        """Test that get_queue_depth updates the retry queue gauge."""
        from backend.api.event_publisher import get_queue_depth

        with patch(
            "backend.api.middleware.metrics.set_event_persistence_retry_queue_depth"
        ) as mock_set:
            depth = await get_queue_depth(mock_redis)

            assert depth == 7
            mock_set.assert_called_once_with(7)

    @pytest.mark.asyncio
    async def test_get_queue_depth_error_returns_negative_one(self):
        """Test that get_queue_depth returns -1 on Redis error."""
        from backend.api.event_publisher import get_queue_depth

        mock_redis = MagicMock()
        mock_redis.zcard.side_effect = Exception("Redis connection error")

        depth = await get_queue_depth(mock_redis)

        assert depth == -1


class TestRetryEventMetrics:
    """Test retry_event() records Prometheus metrics."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        return MagicMock()

    @pytest.fixture
    def sample_event(self):
        """Sample failed event."""
        return {
            "session_id": "test_session",
            "event_type": "contribution",
            "sequence": 1,
            "event_data": {"content": "test"},
            "retry_count": 0,
        }

    @pytest.mark.asyncio
    async def test_retry_event_success_records_metric(self, mock_redis, sample_event):
        """Test successful retry records success metric."""
        from backend.api.event_publisher import retry_event

        with (
            patch("backend.api.event_publisher.session_repository") as mock_repo,
            patch("backend.api.middleware.metrics.record_event_persistence_retry") as mock_record,
        ):
            mock_repo.save_event.return_value = None

            result = await retry_event(mock_redis, sample_event)

            assert result is True
            mock_record.assert_called_once_with(success=True)

    @pytest.mark.asyncio
    async def test_retry_event_failure_records_metric(self, mock_redis, sample_event):
        """Test failed retry records failure metric."""
        from backend.api.event_publisher import retry_event

        with (
            patch("backend.api.event_publisher.session_repository") as mock_repo,
            patch("backend.api.middleware.metrics.record_event_persistence_retry") as mock_record,
        ):
            mock_repo.save_event.side_effect = Exception("DB error")

            result = await retry_event(mock_redis, sample_event)

            assert result is False
            mock_record.assert_called_once_with(success=False)
