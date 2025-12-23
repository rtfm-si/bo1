"""System metrics collection using psutil.

Provides process-level resource utilization metrics (CPU, memory, file descriptors)
for the /health endpoint and Prometheus gauges.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Cache configuration
_CACHE_TTL_SECONDS = 5.0
_last_metrics: dict[str, Any] | None = None
_last_fetch_time: float = 0.0


@dataclass
class ProcessMetrics:
    """Process-level resource metrics."""

    cpu_percent: float | None
    memory_percent: float | None
    memory_rss_mb: float | None
    open_fds: int | None
    threads: int | None


def get_process_metrics() -> ProcessMetrics:
    """Get current process resource metrics.

    Returns cached values if called within CACHE_TTL_SECONDS to avoid
    overhead on rapid health checks.

    Returns:
        ProcessMetrics with CPU%, memory%, RSS in MB, and open file descriptors.
        Values are None if psutil fails to collect them.
    """
    global _last_metrics, _last_fetch_time

    current_time = time.monotonic()

    # Return cached metrics if within TTL
    if _last_metrics is not None and (current_time - _last_fetch_time) < _CACHE_TTL_SECONDS:
        return ProcessMetrics(**_last_metrics)

    # Collect fresh metrics
    metrics: dict[str, Any] = {
        "cpu_percent": None,
        "memory_percent": None,
        "memory_rss_mb": None,
        "open_fds": None,
        "threads": None,
    }

    try:
        import psutil

        process = psutil.Process()

        # CPU percent (non-blocking, returns since last call or process start)
        # Use interval=None for non-blocking call
        try:
            metrics["cpu_percent"] = process.cpu_percent(interval=None)
        except Exception as e:
            logger.debug(f"Failed to get CPU percent: {e}")

        # Memory info
        try:
            mem_info = process.memory_info()
            metrics["memory_rss_mb"] = round(mem_info.rss / (1024 * 1024), 2)
            metrics["memory_percent"] = round(process.memory_percent(), 2)
        except Exception as e:
            logger.debug(f"Failed to get memory info: {e}")

        # File descriptors (Unix only)
        try:
            metrics["open_fds"] = process.num_fds()
        except (AttributeError, psutil.Error):
            # num_fds() not available on Windows
            try:
                metrics["open_fds"] = len(process.open_files())
            except Exception:  # noqa: S110 - optional metric, silently skip
                pass

        # Thread count
        try:
            metrics["threads"] = process.num_threads()
        except Exception as e:
            logger.debug(f"Failed to get thread count: {e}")

    except ImportError:
        logger.warning("psutil not installed, system metrics unavailable")
    except Exception as e:
        logger.warning(f"Failed to collect process metrics: {e}")

    # Update cache
    _last_metrics = metrics
    _last_fetch_time = current_time

    return ProcessMetrics(**metrics)


def get_system_metrics_dict() -> dict[str, Any]:
    """Get system metrics as a dictionary for API response.

    Returns:
        Dictionary with cpu_percent, memory_percent, memory_rss_mb, open_fds, threads.
        Values are None if collection fails.
    """
    metrics = get_process_metrics()
    return {
        "cpu_percent": metrics.cpu_percent,
        "memory_percent": metrics.memory_percent,
        "memory_rss_mb": metrics.memory_rss_mb,
        "open_fds": metrics.open_fds,
        "threads": metrics.threads,
    }
