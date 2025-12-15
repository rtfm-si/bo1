"""Unit tests for pool degradation manager.

Tests:
- Degradation threshold detection
- Queue capacity limits
- Timeout behavior
- Metrics tracking
- Graceful recovery when pool frees up
"""

import pytest

from bo1.constants import PoolDegradationConfig
from bo1.state.pool_degradation import (
    DegradationStats,
    PoolDegradationManager,
    PoolExhaustionError,
    get_degradation_manager,
    reset_degradation_manager,
)


@pytest.fixture(autouse=True)
def reset_manager():
    """Reset global manager before each test."""
    reset_degradation_manager()
    yield
    reset_degradation_manager()


class TestPoolDegradationManager:
    """Tests for PoolDegradationManager class."""

    def test_initial_state_not_degraded(self):
        """Manager starts in non-degraded state."""
        manager = PoolDegradationManager()
        assert not manager.is_degraded()
        assert not manager.should_shed_load()
        stats = manager.get_stats()
        assert stats.queue_depth == 0
        assert stats.requests_queued_total == 0

    def test_enters_degradation_at_threshold(self):
        """Pool enters degradation mode at 90% utilization."""
        manager = PoolDegradationManager()

        # 18/20 = 90% utilization - at threshold
        manager.update_pool_state(
            used_connections=18,
            free_connections=2,
            max_connections=20,
        )
        assert manager.is_degraded()
        assert not manager.should_shed_load()

    def test_enters_load_shedding_at_95_percent(self):
        """Pool starts shedding load at 95% utilization."""
        manager = PoolDegradationManager()

        # 19/20 = 95% utilization
        manager.update_pool_state(
            used_connections=19,
            free_connections=1,
            max_connections=20,
        )
        assert manager.is_degraded()
        assert manager.should_shed_load()

    def test_exits_degradation_when_pool_frees(self):
        """Pool exits degradation mode when utilization drops."""
        manager = PoolDegradationManager()

        # Enter degradation
        manager.update_pool_state(18, 2, 20)
        assert manager.is_degraded()

        # Pool frees up to 80%
        manager.update_pool_state(16, 4, 20)
        assert not manager.is_degraded()
        assert not manager.should_shed_load()

    def test_queue_depth_tracked(self):
        """Queue depth is tracked during degradation."""
        manager = PoolDegradationManager()

        with manager.queued_request():
            stats = manager.get_stats()
            assert stats.queue_depth == 1

        stats = manager.get_stats()
        assert stats.queue_depth == 0
        assert stats.requests_queued_total == 1

    def test_queue_full_raises_error(self):
        """Raises PoolExhaustionError when queue is full."""
        manager = PoolDegradationManager()

        # Fill the queue
        contexts = []
        for _ in range(PoolDegradationConfig.QUEUE_MAX_SIZE):
            ctx = manager.queued_request()
            ctx.__enter__()
            contexts.append(ctx)

        # Next request should fail
        with pytest.raises(PoolExhaustionError) as exc_info:
            with manager.queued_request():
                pass

        assert exc_info.value.queue_depth == PoolDegradationConfig.QUEUE_MAX_SIZE
        assert "queue full" in str(exc_info.value).lower()

        # Clean up contexts
        for ctx in contexts:
            ctx.__exit__(None, None, None)

    def test_retry_after_has_jitter(self):
        """Retry-After header includes randomized jitter."""
        manager = PoolDegradationManager()

        retry_values = set()
        for _ in range(20):
            retry_values.add(manager.get_retry_after())

        # Should have multiple values due to jitter
        base = PoolDegradationConfig.RETRY_AFTER_BASE_SECONDS
        max_jitter = PoolDegradationConfig.RETRY_AFTER_JITTER_SECONDS

        assert all(base <= v <= base + max_jitter for v in retry_values)
        # With 20 samples, we should see at least some variance
        assert len(retry_values) > 1

    def test_shed_load_counter_incremented(self):
        """Load shedding events are counted."""
        manager = PoolDegradationManager()

        manager.record_shed_load()
        manager.record_shed_load()

        stats = manager.get_stats()
        assert stats.requests_shed_total == 2

    def test_queue_timeout_counter_incremented(self):
        """Queue timeout events are counted."""
        manager = PoolDegradationManager()

        manager.record_queue_timeout()

        stats = manager.get_stats()
        assert stats.queue_timeouts_total == 1

    def test_utilization_percentage_calculated_correctly(self):
        """Pool utilization percentage is calculated correctly."""
        manager = PoolDegradationManager()

        manager.update_pool_state(10, 10, 20)
        stats = manager.get_stats()
        assert stats.pool_utilization_pct == 50.0

        manager.update_pool_state(5, 15, 20)
        stats = manager.get_stats()
        assert stats.pool_utilization_pct == 25.0


class TestPoolExhaustionError:
    """Tests for PoolExhaustionError exception."""

    def test_error_includes_queue_depth(self):
        """Error includes queue depth information."""
        error = PoolExhaustionError(
            message="Test error",
            queue_depth=10,
            wait_estimate=5.0,
        )
        assert error.queue_depth == 10
        assert error.wait_estimate == 5.0
        assert "Test error" in str(error)

    def test_default_values(self):
        """Error has sensible defaults."""
        error = PoolExhaustionError()
        assert error.queue_depth == 0
        assert error.wait_estimate == 0.0
        assert "exhausted" in str(error).lower()


class TestGlobalManager:
    """Tests for global manager singleton."""

    def test_get_manager_returns_same_instance(self):
        """get_degradation_manager returns same instance."""
        manager1 = get_degradation_manager()
        manager2 = get_degradation_manager()
        assert manager1 is manager2

    def test_reset_creates_new_instance(self):
        """reset_degradation_manager creates new instance."""
        manager1 = get_degradation_manager()
        manager1.record_shed_load()  # Modify state

        reset_degradation_manager()

        manager2 = get_degradation_manager()
        assert manager2.get_stats().requests_shed_total == 0


class TestDegradationStats:
    """Tests for DegradationStats dataclass."""

    def test_default_values(self):
        """Stats has sensible defaults."""
        stats = DegradationStats()
        assert not stats.is_degraded
        assert not stats.should_shed_load
        assert stats.pool_utilization_pct == 0.0
        assert stats.queue_depth == 0
        assert stats.requests_queued_total == 0
        assert stats.requests_shed_total == 0
        assert stats.queue_timeouts_total == 0
        assert stats.last_degradation_start is None
        assert stats.degradation_duration_seconds == 0.0
