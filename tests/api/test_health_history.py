"""Unit tests for health check history storage.

Tests cover:
- Buffer behavior (add, retrieve, overflow)
- Thread safety
- Record structure and serialization
- Empty history handling
- Time window calculation
"""

import threading
from datetime import UTC, datetime, timedelta

from backend.api.health_history import (
    HealthCheckHistory,
    HealthCheckRecord,
    get_health_history,
    reset_health_history,
)


class TestHealthCheckRecord:
    """Tests for HealthCheckRecord dataclass."""

    def test_record_creation(self) -> None:
        """Test basic record creation."""
        now = datetime.now(UTC)
        record = HealthCheckRecord(
            timestamp=now,
            status="healthy",
            components={"db": True, "redis": True},
            latency_ms=5.5,
        )

        assert record.timestamp == now
        assert record.status == "healthy"
        assert record.components == {"db": True, "redis": True}
        assert record.latency_ms == 5.5

    def test_record_default_values(self) -> None:
        """Test record with default values."""
        now = datetime.now(UTC)
        record = HealthCheckRecord(timestamp=now, status="healthy")

        assert record.components == {}
        assert record.latency_ms == 0.0

    def test_record_to_dict(self) -> None:
        """Test JSON serialization."""
        now = datetime.now(UTC)
        record = HealthCheckRecord(
            timestamp=now,
            status="degraded",
            components={"llm_anthropic": False},
            latency_ms=10.123,
        )

        result = record.to_dict()

        assert result["timestamp"] == now.isoformat()
        assert result["status"] == "degraded"
        assert result["components"] == {"llm_anthropic": False}
        assert result["latency_ms"] == 10.12  # Rounded to 2 decimals

    def test_record_to_dict_rounding(self) -> None:
        """Test latency rounding in to_dict."""
        record = HealthCheckRecord(
            timestamp=datetime.now(UTC),
            status="healthy",
            latency_ms=5.999999,
        )

        result = record.to_dict()
        assert result["latency_ms"] == 6.0


class TestHealthCheckHistory:
    """Tests for HealthCheckHistory class."""

    def test_empty_history(self) -> None:
        """Test empty history returns empty list."""
        history = HealthCheckHistory(max_size=5)

        assert history.get_history() == []
        assert history.get_count() == 0

    def test_single_record(self) -> None:
        """Test adding a single record."""
        history = HealthCheckHistory(max_size=5)
        record = HealthCheckRecord(
            timestamp=datetime.now(UTC),
            status="healthy",
        )

        history.record(record)

        assert history.get_count() == 1
        records = history.get_history()
        assert len(records) == 1
        assert records[0] == record

    def test_multiple_records_order(self) -> None:
        """Test records returned newest first."""
        history = HealthCheckHistory(max_size=5)
        now = datetime.now(UTC)

        # Add 3 records with incrementing timestamps
        for i in range(3):
            record = HealthCheckRecord(
                timestamp=now + timedelta(seconds=i),
                status="healthy",
                latency_ms=float(i),
            )
            history.record(record)

        records = history.get_history()

        # Should be newest first
        assert len(records) == 3
        assert records[0].latency_ms == 2.0  # Last added
        assert records[1].latency_ms == 1.0
        assert records[2].latency_ms == 0.0  # First added

    def test_buffer_overflow_eviction(self) -> None:
        """Test oldest record evicted when buffer full."""
        history = HealthCheckHistory(max_size=3)
        now = datetime.now(UTC)

        # Add 5 records to overflow the buffer
        for i in range(5):
            record = HealthCheckRecord(
                timestamp=now + timedelta(seconds=i),
                status="healthy",
                latency_ms=float(i),
            )
            history.record(record)

        # Only last 3 should remain
        assert history.get_count() == 3
        records = history.get_history()
        assert records[0].latency_ms == 4.0  # Most recent
        assert records[1].latency_ms == 3.0
        assert records[2].latency_ms == 2.0  # Oldest kept

    def test_time_window_empty(self) -> None:
        """Test time window returns None for empty history."""
        history = HealthCheckHistory(max_size=5)

        oldest, newest = history.get_time_window()

        assert oldest is None
        assert newest is None

    def test_time_window_single_record(self) -> None:
        """Test time window with single record."""
        history = HealthCheckHistory(max_size=5)
        now = datetime.now(UTC)
        history.record(HealthCheckRecord(timestamp=now, status="healthy"))

        oldest, newest = history.get_time_window()

        assert oldest == now
        assert newest == now

    def test_time_window_multiple_records(self) -> None:
        """Test time window with multiple records."""
        history = HealthCheckHistory(max_size=5)
        now = datetime.now(UTC)

        for i in range(3):
            history.record(
                HealthCheckRecord(
                    timestamp=now + timedelta(seconds=i),
                    status="healthy",
                )
            )

        oldest, newest = history.get_time_window()

        assert oldest == now
        assert newest == now + timedelta(seconds=2)

    def test_clear(self) -> None:
        """Test clearing history."""
        history = HealthCheckHistory(max_size=5)
        history.record(HealthCheckRecord(timestamp=datetime.now(UTC), status="healthy"))

        assert history.get_count() == 1
        history.clear()
        assert history.get_count() == 0
        assert history.get_history() == []

    def test_max_size_property(self) -> None:
        """Test max_size property."""
        history = HealthCheckHistory(max_size=10)
        assert history.max_size == 10

    def test_thread_safety(self) -> None:
        """Test concurrent access is safe."""
        history = HealthCheckHistory(max_size=100)
        errors: list[Exception] = []

        def writer() -> None:
            try:
                for _ in range(50):
                    history.record(
                        HealthCheckRecord(
                            timestamp=datetime.now(UTC),
                            status="healthy",
                        )
                    )
            except Exception as e:
                errors.append(e)

        def reader() -> None:
            try:
                for _ in range(50):
                    history.get_history()
                    history.get_count()
                    history.get_time_window()
            except Exception as e:
                errors.append(e)

        # Launch concurrent threads
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert errors == []
        # Should have some records
        assert history.get_count() > 0


class TestSingleton:
    """Tests for singleton pattern."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_health_history()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        reset_health_history()

    def test_singleton_returns_same_instance(self) -> None:
        """Test get_health_history returns same instance."""
        h1 = get_health_history()
        h2 = get_health_history()

        assert h1 is h2

    def test_reset_clears_singleton(self) -> None:
        """Test reset_health_history creates new instance."""
        h1 = get_health_history()
        h1.record(HealthCheckRecord(timestamp=datetime.now(UTC), status="healthy"))

        reset_health_history()
        h2 = get_health_history()

        assert h1 is not h2
        assert h2.get_count() == 0

    def test_singleton_thread_safe(self) -> None:
        """Test singleton initialization is thread-safe."""
        instances: list[HealthCheckHistory] = []
        errors: list[Exception] = []

        def get_instance() -> None:
            try:
                instances.append(get_health_history())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        # All instances should be the same
        assert all(i is instances[0] for i in instances)
