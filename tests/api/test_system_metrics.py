"""Tests for system metrics collection.

Tests:
- ProcessMetrics dataclass
- get_process_metrics() function
- Caching behavior
- Prometheus gauge updates
"""

import time
from unittest.mock import MagicMock, patch


class TestProcessMetrics:
    """Tests for get_process_metrics() function."""

    def test_returns_process_metrics_dataclass(self):
        """get_process_metrics should return ProcessMetrics dataclass."""
        from backend.api.system_metrics import ProcessMetrics, get_process_metrics

        metrics = get_process_metrics()
        assert isinstance(metrics, ProcessMetrics)

    def test_returns_cpu_percent(self):
        """get_process_metrics should return CPU percentage."""
        # Reset cache to get fresh metrics
        import backend.api.system_metrics as sm
        from backend.api.system_metrics import get_process_metrics

        sm._last_metrics = None
        sm._last_fetch_time = 0.0

        metrics = get_process_metrics()
        # CPU percent can be 0.0 on first call (no interval), but should be a number
        assert metrics.cpu_percent is None or isinstance(metrics.cpu_percent, float)

    def test_returns_memory_metrics(self):
        """get_process_metrics should return memory metrics."""
        # Reset cache
        import backend.api.system_metrics as sm
        from backend.api.system_metrics import get_process_metrics

        sm._last_metrics = None
        sm._last_fetch_time = 0.0

        metrics = get_process_metrics()
        assert metrics.memory_percent is not None
        assert metrics.memory_rss_mb is not None
        assert metrics.memory_percent >= 0
        assert metrics.memory_rss_mb > 0

    def test_returns_open_fds(self):
        """get_process_metrics should return file descriptor count."""
        # Reset cache
        import backend.api.system_metrics as sm
        from backend.api.system_metrics import get_process_metrics

        sm._last_metrics = None
        sm._last_fetch_time = 0.0

        metrics = get_process_metrics()
        # May be None on Windows
        assert metrics.open_fds is None or metrics.open_fds >= 0

    def test_returns_thread_count(self):
        """get_process_metrics should return thread count."""
        # Reset cache
        import backend.api.system_metrics as sm
        from backend.api.system_metrics import get_process_metrics

        sm._last_metrics = None
        sm._last_fetch_time = 0.0

        metrics = get_process_metrics()
        assert metrics.threads is not None
        assert metrics.threads >= 1


class TestMetricsCaching:
    """Tests for metrics caching behavior."""

    def test_caches_results(self):
        """get_process_metrics should cache results within TTL."""
        # Reset cache
        import backend.api.system_metrics as sm
        from backend.api.system_metrics import get_process_metrics

        sm._last_metrics = None
        sm._last_fetch_time = 0.0

        with patch("psutil.Process") as mock_process_class:
            mock_process = MagicMock()
            mock_process.cpu_percent.return_value = 10.5
            mock_process.memory_percent.return_value = 20.3
            mock_process.memory_info.return_value.rss = 100 * 1024 * 1024  # 100 MB
            mock_process.num_fds.return_value = 50
            mock_process.num_threads.return_value = 4
            mock_process_class.return_value = mock_process

            # First call should fetch
            metrics1 = get_process_metrics()
            assert mock_process.cpu_percent.call_count == 1

            # Second call within TTL should use cache
            metrics2 = get_process_metrics()
            assert mock_process.cpu_percent.call_count == 1  # Not called again

            # Values should be same
            assert metrics1.cpu_percent == metrics2.cpu_percent
            assert metrics1.memory_rss_mb == metrics2.memory_rss_mb

    def test_refreshes_after_ttl(self):
        """get_process_metrics should refresh after TTL expires."""
        # Reset cache and set fetch time in the past
        import backend.api.system_metrics as sm
        from backend.api.system_metrics import get_process_metrics

        sm._last_metrics = {
            "cpu_percent": 5.0,
            "memory_percent": 10.0,
            "memory_rss_mb": 50.0,
            "open_fds": 20,
            "threads": 2,
        }
        sm._last_fetch_time = time.monotonic() - 10.0  # 10 seconds ago (beyond 5s TTL)

        with patch("psutil.Process") as mock_process_class:
            mock_process = MagicMock()
            mock_process.cpu_percent.return_value = 25.0
            mock_process.memory_percent.return_value = 30.0
            mock_process.memory_info.return_value.rss = 200 * 1024 * 1024
            mock_process.num_fds.return_value = 100
            mock_process.num_threads.return_value = 8
            mock_process_class.return_value = mock_process

            metrics = get_process_metrics()
            # Should have fetched new values
            assert metrics.cpu_percent == 25.0
            assert metrics.threads == 8


class TestMetricsErrorHandling:
    """Tests for error handling in metrics collection."""

    def test_handles_psutil_import_error(self):
        """get_process_metrics should handle missing psutil gracefully."""
        import backend.api.system_metrics as sm

        sm._last_metrics = None
        sm._last_fetch_time = 0.0

        with patch.dict("sys.modules", {"psutil": None}):
            with patch("backend.api.system_metrics.logger"):
                # Force reimport check by patching import
                import builtins

                original_import = builtins.__import__

                def mock_import(name, *args, **kwargs):
                    if name == "psutil":
                        raise ImportError("psutil not installed")
                    return original_import(name, *args, **kwargs)

                with patch.object(builtins, "__import__", mock_import):
                    from backend.api.system_metrics import get_process_metrics

                    # Reset again after import
                    sm._last_metrics = None
                    sm._last_fetch_time = 0.0

                    metrics = get_process_metrics()
                    # Should return ProcessMetrics with all None values
                    assert metrics.cpu_percent is None
                    assert metrics.memory_percent is None

    def test_handles_cpu_percent_failure(self):
        """get_process_metrics should handle cpu_percent failure gracefully."""
        import backend.api.system_metrics as sm
        from backend.api.system_metrics import get_process_metrics

        sm._last_metrics = None
        sm._last_fetch_time = 0.0

        with patch("psutil.Process") as mock_process_class:
            mock_process = MagicMock()
            mock_process.cpu_percent.side_effect = Exception("CPU access denied")
            mock_process.memory_percent.return_value = 15.0
            mock_process.memory_info.return_value.rss = 100 * 1024 * 1024
            mock_process.num_fds.return_value = 30
            mock_process.num_threads.return_value = 3
            mock_process_class.return_value = mock_process

            metrics = get_process_metrics()
            assert metrics.cpu_percent is None  # Failed
            assert metrics.memory_percent == 15.0  # Still works

    def test_handles_memory_info_failure(self):
        """get_process_metrics should handle memory_info failure gracefully."""
        import backend.api.system_metrics as sm
        from backend.api.system_metrics import get_process_metrics

        sm._last_metrics = None
        sm._last_fetch_time = 0.0

        with patch("psutil.Process") as mock_process_class:
            mock_process = MagicMock()
            mock_process.cpu_percent.return_value = 5.0
            mock_process.memory_info.side_effect = Exception("Memory access denied")
            mock_process.memory_percent.side_effect = Exception("Memory access denied")
            mock_process.num_fds.return_value = 30
            mock_process.num_threads.return_value = 3
            mock_process_class.return_value = mock_process

            metrics = get_process_metrics()
            assert metrics.cpu_percent == 5.0  # Still works
            assert metrics.memory_percent is None  # Failed
            assert metrics.memory_rss_mb is None  # Failed


class TestSystemMetricsDict:
    """Tests for get_system_metrics_dict() function."""

    def test_returns_dictionary(self):
        """get_system_metrics_dict should return a dictionary."""
        from backend.api.system_metrics import get_system_metrics_dict

        result = get_system_metrics_dict()
        assert isinstance(result, dict)
        assert "cpu_percent" in result
        assert "memory_percent" in result
        assert "memory_rss_mb" in result
        assert "open_fds" in result
        assert "threads" in result


class TestPrometheusMetricsUpdate:
    """Tests for Prometheus gauge updates."""

    def test_update_process_metrics_sets_gauges(self):
        """update_process_metrics should set Prometheus gauge values."""
        from backend.api.middleware.metrics import (
            bo1_process_cpu_percent,
            bo1_process_memory_percent,
            bo1_process_memory_rss_bytes,
            bo1_process_open_fds,
            bo1_process_threads,
            update_process_metrics,
        )

        update_process_metrics(
            cpu_percent=15.5,
            memory_percent=25.3,
            memory_rss_mb=512.0,
            open_fds=100,
            threads=16,
        )

        # Get current gauge values (prometheus_client uses _value.get())
        assert bo1_process_cpu_percent._value.get() == 15.5
        assert bo1_process_memory_percent._value.get() == 25.3
        # Memory is converted to bytes: 512 MB * 1024 * 1024
        assert bo1_process_memory_rss_bytes._value.get() == 512.0 * 1024 * 1024
        assert bo1_process_open_fds._value.get() == 100
        assert bo1_process_threads._value.get() == 16

    def test_update_process_metrics_handles_none_values(self):
        """update_process_metrics should skip None values."""
        from backend.api.middleware.metrics import (
            bo1_process_cpu_percent,
            update_process_metrics,
        )

        # Set initial value
        bo1_process_cpu_percent.set(10.0)
        initial_value = bo1_process_cpu_percent._value.get()

        # Call with None - should not change the value
        update_process_metrics(
            cpu_percent=None,
            memory_percent=None,
            memory_rss_mb=None,
            open_fds=None,
            threads=None,
        )

        # Value should remain unchanged
        assert bo1_process_cpu_percent._value.get() == initial_value
