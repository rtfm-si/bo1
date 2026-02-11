"""Tests for performance monitoring service."""

import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from backend.services.performance_monitor import (
    DegradationResult,
    MetricStats,
    PerformanceMetric,
    PerformanceMonitor,
    TrendAnalysis,
    get_performance_monitor,
    record_metric,
)
from backend.services.performance_thresholds import (
    DEFAULT_THRESHOLDS,
    ThresholdService,
    get_threshold_service,
)


class TestPerformanceMetricDataclass:
    """Tests for PerformanceMetric dataclass."""

    def test_creates_with_required_fields(self) -> None:
        """Test creation with required fields only."""
        metric = PerformanceMetric(
            metric_name="test_metric",
            value=100.5,
            timestamp=datetime.now(UTC),
        )
        assert metric.metric_name == "test_metric"
        assert metric.value == 100.5
        assert metric.source is None
        assert metric.labels == {}

    def test_creates_with_all_fields(self) -> None:
        """Test creation with all optional fields."""
        ts = datetime.now(UTC)
        metric = PerformanceMetric(
            metric_name="api_response_time",
            value=250.0,
            timestamp=ts,
            source="api_gateway",
            labels={"endpoint": "/api/sessions"},
        )
        assert metric.source == "api_gateway"
        assert metric.labels == {"endpoint": "/api/sessions"}


class TestMetricStatsDataclass:
    """Tests for MetricStats dataclass."""

    def test_creates_with_all_fields(self) -> None:
        """Test creation with all statistical fields."""
        stats = MetricStats(
            metric_name="test",
            count=100,
            avg=50.0,
            min_val=10.0,
            max_val=90.0,
            p50=45.0,
            p95=85.0,
            p99=89.0,
            window_minutes=30,
        )
        assert stats.count == 100
        assert stats.p95 == 85.0
        assert stats.calculated_at is not None


class TestDegradationResult:
    """Tests for DegradationResult dataclass."""

    def test_healthy_result(self) -> None:
        """Test healthy degradation result."""
        result = DegradationResult(
            metric_name="api_response_time",
            degradation_score=0.0,
            current_avg=100.0,
            baseline_avg=100.0,
            ratio=1.0,
            is_degraded=False,
            severity="none",
            details="All good",
        )
        assert not result.is_degraded
        assert result.severity == "none"

    def test_degraded_result(self) -> None:
        """Test degraded result."""
        result = DegradationResult(
            metric_name="api_response_time",
            degradation_score=0.6,
            current_avg=160.0,
            baseline_avg=100.0,
            ratio=1.6,
            is_degraded=True,
            severity="warn",
            details="50% slower",
        )
        assert result.is_degraded
        assert result.severity == "warn"


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor class."""

    def test_record_metric_with_mock_redis(self) -> None:
        """Test recording a metric with mocked Redis."""
        mock_redis = MagicMock()
        mock_redis.zadd.return_value = 1
        mock_redis.ttl.return_value = -1

        monitor = PerformanceMonitor(redis_client=mock_redis)
        result = monitor.record_metric("test_metric", 100.0, "test_source")

        assert result is True
        mock_redis.zadd.assert_called_once()
        mock_redis.expire.assert_called_once()

    def test_record_metric_redis_unavailable(self) -> None:
        """Test graceful handling when Redis unavailable."""
        monitor = PerformanceMonitor()
        monitor._redis_available = False

        result = monitor.record_metric("test_metric", 100.0)
        assert result is False

    def test_get_metric_values_empty(self) -> None:
        """Test getting values when none exist."""
        mock_redis = MagicMock()
        mock_redis.zrangebyscore.return_value = []

        monitor = PerformanceMonitor(redis_client=mock_redis)
        values = monitor.get_metric_values("test_metric", 5)

        assert values == []

    def test_get_metric_values_with_data(self) -> None:
        """Test getting values with data."""
        import json

        mock_redis = MagicMock()
        now = time.time()
        mock_redis.zrangebyscore.return_value = [
            json.dumps({"value": 100.0, "ts": now - 60}),
            json.dumps({"value": 150.0, "ts": now - 30}),
        ]

        monitor = PerformanceMonitor(redis_client=mock_redis)
        values = monitor.get_metric_values("test_metric", 5)

        assert len(values) == 2
        assert values[0][0] == 100.0
        assert values[1][0] == 150.0

    def test_get_metric_stats_no_data(self) -> None:
        """Test stats calculation with no data."""
        mock_redis = MagicMock()
        mock_redis.zrangebyscore.return_value = []

        monitor = PerformanceMonitor(redis_client=mock_redis)
        stats = monitor.get_metric_stats("test_metric", 30)

        assert stats is None

    def test_get_metric_stats_with_data(self) -> None:
        """Test stats calculation with data."""
        import json

        mock_redis = MagicMock()
        now = time.time()
        # Create 10 values from 100 to 1000
        mock_redis.zrangebyscore.return_value = [
            json.dumps({"value": float(i * 100), "ts": now - (i * 10)}) for i in range(1, 11)
        ]

        monitor = PerformanceMonitor(redis_client=mock_redis)
        stats = monitor.get_metric_stats("test_metric", 30)

        assert stats is not None
        assert stats.count == 10
        assert stats.min_val == 100.0
        assert stats.max_val == 1000.0
        # Average of 100,200,...,1000 = 550
        assert stats.avg == 550.0

    def test_get_degradation_score_insufficient_data(self) -> None:
        """Test degradation score with insufficient data."""
        mock_redis = MagicMock()
        mock_redis.zrangebyscore.return_value = []

        monitor = PerformanceMonitor(redis_client=mock_redis)
        result = monitor.get_degradation_score("test_metric")

        assert result.degradation_score == 0.0
        assert "Insufficient" in result.details

    def test_get_degradation_score_no_degradation(self) -> None:
        """Test degradation score when metrics are stable."""
        import json

        mock_redis = MagicMock()
        now = time.time()

        # Create stable metrics - 30 values all around 100
        mock_redis.zrangebyscore.return_value = [
            json.dumps({"value": 100.0 + (i % 10), "ts": now - (i * 60)}) for i in range(30)
        ]

        monitor = PerformanceMonitor(redis_client=mock_redis)
        result = monitor.get_degradation_score("test_metric")

        # With stable data, ratio should be close to 1.0
        assert result.ratio < 1.2
        assert result.severity == "none"

    def test_analyze_trends(self) -> None:
        """Test trend analysis across multiple metrics."""
        mock_redis = MagicMock()
        mock_redis.zrangebyscore.return_value = []  # No data = healthy (no degradation)

        monitor = PerformanceMonitor(redis_client=mock_redis)
        trend = monitor.analyze_trends()

        assert isinstance(trend, TrendAnalysis)
        assert trend.overall_health == "healthy"
        assert trend.degraded_count == 0
        assert trend.critical_count == 0

    def test_cleanup_old_metrics(self) -> None:
        """Test cleanup of old metrics."""
        mock_redis = MagicMock()
        mock_redis.zremrangebyscore.return_value = 5
        mock_redis.scan_iter.return_value = ["perf:metrics:test1", "perf:metrics:test2"]

        monitor = PerformanceMonitor(redis_client=mock_redis)
        removed = monitor.cleanup_old_metrics()

        assert removed == 10  # 5 from each key


class TestThresholdConfig:
    """Tests for ThresholdConfig dataclass."""

    def test_default_thresholds_exist(self) -> None:
        """Test that default thresholds are defined."""
        assert "api_response_time_ms" in DEFAULT_THRESHOLDS
        assert "error_rate_percent" in DEFAULT_THRESHOLDS
        assert "db_pool_usage_percent" in DEFAULT_THRESHOLDS

    def test_api_response_time_thresholds(self) -> None:
        """Test API response time thresholds."""
        config = DEFAULT_THRESHOLDS["api_response_time_ms"]
        assert config.warn_value == 2000  # 2 seconds
        assert config.critical_value == 5000  # 5 seconds
        assert config.unit == "ms"

    def test_error_rate_thresholds(self) -> None:
        """Test error rate thresholds."""
        config = DEFAULT_THRESHOLDS["error_rate_percent"]
        assert config.warn_value == 5.0  # 5%
        assert config.critical_value == 10.0  # 10%


class TestThresholdService:
    """Tests for ThresholdService class."""

    def test_get_threshold_from_defaults(self) -> None:
        """Test getting threshold from defaults."""
        service = ThresholdService()
        config = service.get_threshold("api_response_time_ms")

        assert config.metric_name == "api_response_time_ms"
        assert config.warn_value == 2000

    def test_get_threshold_unknown_metric(self) -> None:
        """Test getting threshold for unknown metric."""
        service = ThresholdService()
        config = service.get_threshold("unknown_metric")

        assert config.metric_name == "unknown_metric"
        assert config.enabled is False
        assert "Unknown metric" in config.description

    def test_check_threshold_below_warn(self) -> None:
        """Test checking value below warning threshold."""
        service = ThresholdService()
        severity, exceeded = service.check_threshold("api_response_time_ms", 1000)

        assert severity == "none"
        assert exceeded is False

    def test_check_threshold_warn(self) -> None:
        """Test checking value at warning threshold."""
        service = ThresholdService()
        severity, exceeded = service.check_threshold("api_response_time_ms", 3000)

        assert severity == "warn"
        assert exceeded is True

    def test_check_threshold_critical(self) -> None:
        """Test checking value at critical threshold."""
        service = ThresholdService()
        severity, exceeded = service.check_threshold("api_response_time_ms", 6000)

        assert severity == "critical"
        assert exceeded is True

    def test_get_all_thresholds(self) -> None:
        """Test getting all thresholds."""
        service = ThresholdService()
        thresholds = service.get_all_thresholds()

        assert len(thresholds) >= 5  # At least the 5 defaults
        names = {t.metric_name for t in thresholds}
        assert "api_response_time_ms" in names
        assert "error_rate_percent" in names


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_performance_monitor_singleton(self) -> None:
        """Test that get_performance_monitor returns singleton."""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()

        assert monitor1 is monitor2

    def test_get_threshold_service_singleton(self) -> None:
        """Test that get_threshold_service returns singleton."""
        service1 = get_threshold_service()
        service2 = get_threshold_service()

        assert service1 is service2

    def test_record_metric_convenience(self) -> None:
        """Test record_metric convenience function."""
        mock = MagicMock()
        mock.record_metric.return_value = True
        with patch(
            "backend.services.performance_monitor.get_performance_monitor", return_value=mock
        ):
            record_metric("test", 100.0)
            mock.record_metric.assert_called_once_with("test", 100.0, None, None)


class TestPercentileCalculation:
    """Tests for percentile calculation accuracy."""

    def test_p95_calculation(self) -> None:
        """Test p95 calculation is accurate."""
        import json

        mock_redis = MagicMock()
        now = time.time()
        # 100 values from 1 to 100
        mock_redis.zrangebyscore.return_value = [
            json.dumps({"value": float(i), "ts": now - i}) for i in range(1, 101)
        ]

        monitor = PerformanceMonitor(redis_client=mock_redis)
        stats = monitor.get_metric_stats("test", 30)

        assert stats is not None
        # p95 of 1-100 should be around 95
        assert 94 <= stats.p95 <= 96

    def test_p99_calculation(self) -> None:
        """Test p99 calculation is accurate."""
        import json

        mock_redis = MagicMock()
        now = time.time()
        # 100 values from 1 to 100
        mock_redis.zrangebyscore.return_value = [
            json.dumps({"value": float(i), "ts": now - i}) for i in range(1, 101)
        ]

        monitor = PerformanceMonitor(redis_client=mock_redis)
        stats = monitor.get_metric_stats("test", 30)

        assert stats is not None
        # p99 of 1-100 should be around 99
        assert 98 <= stats.p99 <= 100
