"""Graph node execution metrics.

Provides timing instrumentation for LangGraph node functions.
Integrates with the Prometheus metrics in backend/api/metrics.py.
"""

import functools
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


def timed_node[T](
    node_name: str,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator to record execution time for async graph nodes.

    Records:
    - Duration in seconds (histogram with percentile buckets)
    - Success/error counts (counter with status label)

    Args:
        node_name: Name of the node (e.g., "decompose", "select_personas")

    Returns:
        Decorator function

    Example:
        @timed_node("decompose")
        async def decompose_node(state: DeliberationGraphState) -> dict:
            ...
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.perf_counter()
            success = True
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.perf_counter() - start_time
                try:
                    # Import here to avoid circular imports
                    from backend.api.metrics import prom_metrics

                    prom_metrics.record_graph_node_execution(node_name, duration, success)
                except Exception as e:
                    # Don't let metrics failures break node execution
                    logger.warning(f"Failed to record metrics for node {node_name}: {e}")

        return wrapper

    return decorator


def wrap_node_with_timing[T](
    node_name: str, func: Callable[..., Awaitable[T]]
) -> Callable[..., Awaitable[T]]:
    """Wrap an existing node function with timing instrumentation.

    Use this when you can't apply the @timed_node decorator directly
    (e.g., when wrapping nodes in config.py).

    Args:
        node_name: Name of the node for metrics labels
        func: The async node function to wrap

    Returns:
        Wrapped function with timing instrumentation

    Example:
        workflow.add_node("decompose", wrap_node_with_timing("decompose", decompose_node))
    """
    return timed_node(node_name)(func)


def timed_sync_node[T](
    node_name: str,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to record execution time for sync graph nodes.

    Similar to timed_node but for synchronous functions.

    Args:
        node_name: Name of the node (e.g., "cost_guard")

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.perf_counter()
            success = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.perf_counter() - start_time
                try:
                    from backend.api.metrics import prom_metrics

                    prom_metrics.record_graph_node_execution(node_name, duration, success)
                except Exception as e:
                    logger.warning(f"Failed to record metrics for node {node_name}: {e}")

        return wrapper

    return decorator


def wrap_sync_node_with_timing[T](node_name: str, func: Callable[..., T]) -> Callable[..., T]:
    """Wrap a synchronous node function with timing instrumentation.

    Use for sync nodes like cost_guard_node.

    Args:
        node_name: Name of the node for metrics labels
        func: The sync node function to wrap

    Returns:
        Wrapped function with timing instrumentation
    """
    return timed_sync_node(node_name)(func)
