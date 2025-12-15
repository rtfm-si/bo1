"""API utilities for graceful degradation under pool exhaustion.

Provides:
- raise_pool_exhausted(): Raise 503 with Retry-After header
- handle_pool_exhaustion(): Decorator/dependency for endpoint protection
"""

import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from bo1.state.pool_degradation import (
    PoolExhaustionError,
    get_degradation_manager,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def raise_pool_exhausted(
    queue_depth: int = 0,
    wait_estimate: float = 0.0,
) -> None:
    """Raise HTTP 503 with Retry-After header for pool exhaustion.

    Args:
        queue_depth: Current queue depth for response body
        wait_estimate: Suggested retry time in seconds

    Raises:
        HTTPException: Always raises 503 Service Unavailable
    """
    manager = get_degradation_manager()
    retry_after = manager.get_retry_after()

    raise HTTPException(
        status_code=503,
        detail={
            "error": "service_unavailable",
            "message": "Database pool exhausted, please retry",
            "queue_depth": queue_depth,
            "retry_after": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )


def pool_exhaustion_response(exc: PoolExhaustionError) -> JSONResponse:
    """Create JSON response for pool exhaustion error.

    Args:
        exc: The PoolExhaustionError exception

    Returns:
        JSONResponse with 503 status and Retry-After header
    """
    manager = get_degradation_manager()
    retry_after = manager.get_retry_after()

    return JSONResponse(
        status_code=503,
        content={
            "error": "service_unavailable",
            "message": str(exc),
            "queue_depth": exc.queue_depth,
            "retry_after": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )


async def check_pool_health(request: Request) -> None:
    """FastAPI dependency to check pool health before request.

    Use as a dependency for write endpoints that should shed load:

        @router.post("/sessions", dependencies=[Depends(check_pool_health)])
        async def create_session(...):
            ...

    Raises:
        HTTPException: 503 if pool is severely exhausted
    """
    from backend.api.metrics import prom_metrics

    manager = get_degradation_manager()

    if manager.should_shed_load():
        manager.record_shed_load()
        prom_metrics.record_request_shed()
        stats = manager.get_stats()
        raise_pool_exhausted(
            queue_depth=stats.queue_depth,
            wait_estimate=manager.get_retry_after(),
        )


def handle_pool_exhaustion(func: F) -> F:  # noqa: UP047
    """Decorator to handle PoolExhaustionError in endpoints.

    Catches PoolExhaustionError and converts to proper 503 response
    with Retry-After header.

    Usage:
        @router.get("/sessions/{id}")
        @handle_pool_exhaustion
        async def get_session(...):
            ...
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except PoolExhaustionError as e:
            from backend.api.metrics import prom_metrics

            prom_metrics.record_request_shed()
            manager = get_degradation_manager()
            retry_after = manager.get_retry_after()
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "service_unavailable",
                    "message": str(e),
                    "queue_depth": e.queue_depth,
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            ) from e

    return wrapper  # type: ignore[return-value]


def get_degradation_status() -> dict[str, Any]:
    """Get current degradation status for health endpoints.

    Returns:
        Dict with degradation status information
    """
    manager = get_degradation_manager()
    stats = manager.get_stats()

    return {
        "is_degraded": stats.is_degraded,
        "should_shed_load": stats.should_shed_load,
        "pool_utilization_pct": stats.pool_utilization_pct,
        "queue_depth": stats.queue_depth,
        "requests_queued_total": stats.requests_queued_total,
        "requests_shed_total": stats.requests_shed_total,
        "queue_timeouts_total": stats.queue_timeouts_total,
    }
