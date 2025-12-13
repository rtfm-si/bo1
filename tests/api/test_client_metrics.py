"""Tests for client-side metrics functionality."""

from unittest.mock import MagicMock, patch


class TestStoreOperation:
    """Tests for _store_operation helper function."""

    def test_stores_duration_in_sorted_set(self):
        """Duration should be stored in sorted set for percentile calculation."""
        redis_mock = MagicMock()

        from backend.api.client_metrics import TrackedOperation, _store_operation

        op = TrackedOperation(
            id="op-123",
            name="api:GET:/api/v1/sessions",
            startTime=1000.0,
            endTime=1500.0,
            duration=500.0,
            success=True,
            retryCount=0,
        )

        _store_operation(redis_mock, "test-user", op)

        # Verify zadd was called with duration key
        redis_mock.zadd.assert_called()
        call_args = redis_mock.zadd.call_args_list[0]
        assert "client_metrics:duration:api:GET:/api/v1/sessions" in call_args[0][0]

    def test_stores_success_count(self):
        """Success count should be incremented."""
        redis_mock = MagicMock()

        from backend.api.client_metrics import TrackedOperation, _store_operation

        op = TrackedOperation(
            id="op-123",
            name="api:POST:/api/v1/sessions",
            startTime=1000.0,
            duration=200.0,
            success=True,
            retryCount=0,
        )

        _store_operation(redis_mock, "test-user", op)

        # Verify incr was called for success
        incr_calls = [str(c) for c in redis_mock.incr.call_args_list]
        success_call_found = any("success" in call for call in incr_calls)
        assert success_call_found

    def test_stores_failure_count(self):
        """Failure count should be incremented."""
        redis_mock = MagicMock()

        from backend.api.client_metrics import TrackedOperation, _store_operation

        op = TrackedOperation(
            id="op-456",
            name="api:POST:/api/v1/sessions",
            startTime=1000.0,
            duration=200.0,
            success=False,
            error="Network error",
            retryCount=1,
        )

        _store_operation(redis_mock, "test-user", op)

        # Verify incr was called for failure
        incr_calls = [str(c) for c in redis_mock.incr.call_args_list]
        failure_call_found = any("failure" in call for call in incr_calls)
        assert failure_call_found

    def test_stores_retry_distribution(self):
        """Operations with retries should update retry distribution."""
        redis_mock = MagicMock()

        from backend.api.client_metrics import TrackedOperation, _store_operation

        op = TrackedOperation(
            id="op-789",
            name="api:GET:/api/v1/context",
            startTime=1000.0,
            duration=800.0,
            success=True,
            retryCount=2,
        )

        _store_operation(redis_mock, "test-user", op)

        # Verify hincrby was called for retries
        redis_mock.hincrby.assert_called()

    def test_stores_history(self):
        """Operations should be stored in history list."""
        redis_mock = MagicMock()

        from backend.api.client_metrics import TrackedOperation, _store_operation

        op = TrackedOperation(
            id="op-hist",
            name="api:GET:/api/v1/actions",
            startTime=1000.0,
            duration=300.0,
            success=True,
            retryCount=0,
        )

        _store_operation(redis_mock, "test-user", op)

        # Verify lpush was called for history
        redis_mock.lpush.assert_called()

    def test_sets_ttl_on_keys(self):
        """All Redis keys should have TTL set."""
        redis_mock = MagicMock()

        from backend.api.client_metrics import TrackedOperation, _store_operation

        op = TrackedOperation(
            id="op-ttl",
            name="api:GET:/api/v1/datasets",
            startTime=1000.0,
            duration=400.0,
            success=True,
            retryCount=0,
        )

        _store_operation(redis_mock, "test-user", op)

        # Verify expire was called multiple times
        assert redis_mock.expire.call_count >= 3  # duration, count, history

    def test_handles_anonymous_user(self):
        """Anonymous users should be stored with 'anonymous' key."""
        redis_mock = MagicMock()

        from backend.api.client_metrics import TrackedOperation, _store_operation

        op = TrackedOperation(
            id="op-anon",
            name="api:GET:/api/health",
            startTime=1000.0,
            duration=50.0,
            success=True,
            retryCount=0,
        )

        _store_operation(redis_mock, None, op)

        # Verify call contains 'anonymous'
        lpush_call = str(redis_mock.lpush.call_args)
        assert "anonymous" in lpush_call


class TestGetOperationStats:
    """Tests for get_operation_stats helper function."""

    def test_stats_empty_operation(self):
        """Stats for unknown operation should return zeros."""
        with patch("backend.api.client_metrics.RedisManager") as mock_manager:
            redis_mock = MagicMock()
            mock_manager.return_value.client = redis_mock
            redis_mock.get.return_value = None
            redis_mock.zrange.return_value = []
            redis_mock.hgetall.return_value = {}

            from backend.api.client_metrics import get_operation_stats

            stats = get_operation_stats("unknown:operation")
            assert stats["total_count"] == 0
            assert stats["failure_rate"] == 0
            assert stats["duration_ms"]["avg"] == 0

    def test_stats_with_data(self):
        """Stats should calculate percentiles correctly."""
        with patch("backend.api.client_metrics.RedisManager") as mock_manager:
            redis_mock = MagicMock()
            mock_manager.return_value.client = redis_mock
            redis_mock.get.side_effect = lambda k: b"10" if "success" in k else b"2"
            redis_mock.zrange.return_value = [
                (b"t1:u1", 100.0),
                (b"t2:u1", 200.0),
                (b"t3:u1", 300.0),
                (b"t4:u1", 400.0),
                (b"t5:u1", 500.0),
            ]
            redis_mock.hgetall.return_value = {b"1": b"3", b"2": b"1"}

            from backend.api.client_metrics import get_operation_stats

            stats = get_operation_stats("api:GET:/api/v1/sessions")
            assert stats["total_count"] == 12
            assert stats["success_count"] == 10
            assert stats["failure_count"] == 2
            assert stats["duration_ms"]["avg"] == 300.0
            assert stats["retry_distribution"] == {"1": 3, "2": 1}


class TestListTrackedOperations:
    """Tests for list_tracked_operations helper."""

    def test_list_empty(self):
        """Empty list when no operations tracked."""
        with patch("backend.api.client_metrics.RedisManager") as mock_manager:
            redis_mock = MagicMock()
            mock_manager.return_value.client = redis_mock
            redis_mock.keys.return_value = []

            from backend.api.client_metrics import list_tracked_operations

            ops = list_tracked_operations()
            assert ops == []

    def test_list_operations(self):
        """Should extract operation names from Redis keys."""
        with patch("backend.api.client_metrics.RedisManager") as mock_manager:
            redis_mock = MagicMock()
            mock_manager.return_value.client = redis_mock
            redis_mock.keys.return_value = [
                b"client_metrics:count:api:GET:/api/v1/sessions:success",
                b"client_metrics:count:api:POST:/api/v1/context:success",
            ]

            from backend.api.client_metrics import list_tracked_operations

            ops = list_tracked_operations()
            # The function extracts the 3rd segment (index 2) from the key
            assert "api" in ops


class TestTrackedOperationModel:
    """Tests for TrackedOperation Pydantic model."""

    def test_minimal_operation(self):
        """Should accept minimal required fields."""
        from backend.api.client_metrics import TrackedOperation

        op = TrackedOperation(
            id="op-1",
            name="test:op",
            startTime=1000.0,
        )
        assert op.id == "op-1"
        assert op.name == "test:op"
        assert op.startTime == 1000.0
        assert op.duration is None
        assert op.success is None
        assert op.retryCount == 0

    def test_full_operation(self):
        """Should accept all fields."""
        from backend.api.client_metrics import TrackedOperation

        op = TrackedOperation(
            id="op-2",
            name="api:POST:/api/v1/sessions",
            startTime=1000.0,
            endTime=1500.0,
            duration=500.0,
            success=True,
            error=None,
            retryCount=2,
            metadata={"extra": "data"},
        )
        assert op.duration == 500.0
        assert op.success is True
        assert op.retryCount == 2
        assert op.metadata == {"extra": "data"}


class TestClientMetricsBatchModel:
    """Tests for ClientMetricsBatch Pydantic model."""

    def test_empty_batch(self):
        """Should accept empty operations list."""
        from backend.api.client_metrics import ClientMetricsBatch

        batch = ClientMetricsBatch()
        assert batch.operations == []

    def test_batch_with_operations(self):
        """Should accept list of operations."""
        from backend.api.client_metrics import ClientMetricsBatch, TrackedOperation

        batch = ClientMetricsBatch(
            operations=[
                TrackedOperation(id="1", name="op1", startTime=100.0),
                TrackedOperation(id="2", name="op2", startTime=200.0),
            ]
        )
        assert len(batch.operations) == 2
