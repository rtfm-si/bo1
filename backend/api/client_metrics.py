"""Client-side metrics collection endpoint.

Receives operation timing and error data from the frontend for UX observability.
Stores metrics in Redis with TTL for analysis.
"""

import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from redis import Redis

from backend.api.middleware.rate_limit import limiter
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

# Redis key prefix and TTL
METRICS_KEY_PREFIX = "client_metrics:"
METRICS_TTL_SECONDS = 86400  # 24 hours
MAX_OPERATIONS_PER_BATCH = 50  # Limit batch size


class TrackedOperation(BaseModel):
    """A single tracked operation from the client."""

    id: str
    name: str
    startTime: float  # noqa: N815
    endTime: float | None = None  # noqa: N815
    duration: float | None = None
    success: bool | None = None
    error: str | None = None
    retryCount: int = 0  # noqa: N815
    metadata: dict[str, Any] | None = None


class ClientMetricsBatch(BaseModel):
    """Batch of client-side operation metrics."""

    operations: list[TrackedOperation] = Field(
        default_factory=list,
        max_length=MAX_OPERATIONS_PER_BATCH,
    )


def _get_redis() -> Redis:
    """Get Redis client instance."""
    manager = RedisManager()
    return manager.client


def _store_operation(redis: Redis, user_id: str | None, op: TrackedOperation) -> None:
    """Store a single operation metric in Redis.

    Uses sorted sets keyed by operation name for efficient percentile queries.
    """
    timestamp = int(time.time() * 1000)
    user_key = user_id or "anonymous"

    # Store in sorted set by operation name (score = duration for percentile calc)
    if op.duration is not None:
        duration_key = f"{METRICS_KEY_PREFIX}duration:{op.name}"
        redis.zadd(duration_key, {f"{timestamp}:{user_key}": op.duration})
        redis.expire(duration_key, METRICS_TTL_SECONDS)

    # Track success/failure counts
    status = "success" if op.success else "failure" if op.success is False else "unknown"
    count_key = f"{METRICS_KEY_PREFIX}count:{op.name}:{status}"
    redis.incr(count_key)
    redis.expire(count_key, METRICS_TTL_SECONDS)

    # Track retry patterns
    if op.retryCount > 0:
        retry_key = f"{METRICS_KEY_PREFIX}retries:{op.name}"
        redis.hincrby(retry_key, str(op.retryCount), 1)
        redis.expire(retry_key, METRICS_TTL_SECONDS)

    # Store full operation for recent history (limited to last 1000)
    history_key = f"{METRICS_KEY_PREFIX}history:{op.name}"
    op_data = json.dumps(
        {
            "id": op.id,
            "user": user_key,
            "duration": op.duration,
            "success": op.success,
            "error": op.error,
            "retryCount": op.retryCount,
            "timestamp": timestamp,
        }
    )
    redis.lpush(history_key, op_data)
    redis.ltrim(history_key, 0, 999)
    redis.expire(history_key, METRICS_TTL_SECONDS)


def _extract_user_id(request: Request) -> str | None:
    """Extract user ID from request state if authenticated.

    This is a best-effort extraction - metrics are collected regardless of auth status.
    """
    try:
        # User data is set by auth middleware if authenticated
        user = getattr(request.state, "user", None)
        if user and isinstance(user, dict):
            return user.get("user_id")
    except Exception:  # noqa: S110
        pass
    return None


@router.post("/client")
@limiter.limit("30/minute")
async def receive_client_metrics(
    request: Request,
    batch: ClientMetricsBatch,
) -> dict[str, str]:
    """Receive client-side operation metrics.

    Accepts batched operation timing and error data from the frontend.
    Stores in Redis for analysis via admin endpoints.

    Rate limited to 30 requests/minute to prevent abuse.
    No authentication required - metrics are collected for all users.

    Args:
        request: FastAPI request
        batch: Batch of operation metrics

    Returns:
        Acknowledgment response
    """
    if not batch.operations:
        return {"status": "empty"}

    try:
        redis = _get_redis()
        user_id = _extract_user_id(request)

        for op in batch.operations:
            _store_operation(redis, user_id, op)

        logger.debug(
            "Received client metrics",
            extra={
                "operation_count": len(batch.operations),
                "user_id": user_id or "anonymous",
            },
        )

        return {"status": "received", "count": str(len(batch.operations))}

    except Exception:
        logger.warning("Failed to store client metrics", exc_info=True)
        # Don't fail the request - metrics are best-effort
        return {"status": "error"}


def get_operation_stats(operation_name: str) -> dict[str, Any]:
    """Get statistics for a specific operation.

    Used by admin dashboard to display operation performance.

    Args:
        operation_name: Name of the operation to get stats for

    Returns:
        Dictionary with count, duration percentiles, and failure rate
    """
    redis = _get_redis()

    # Get counts
    success_count = int(redis.get(f"{METRICS_KEY_PREFIX}count:{operation_name}:success") or 0)
    failure_count = int(redis.get(f"{METRICS_KEY_PREFIX}count:{operation_name}:failure") or 0)
    total_count = success_count + failure_count

    # Get duration percentiles from sorted set
    duration_key = f"{METRICS_KEY_PREFIX}duration:{operation_name}"
    durations = redis.zrange(duration_key, 0, -1, withscores=True)

    if durations:
        sorted_durations = sorted([d[1] for d in durations])
        count = len(sorted_durations)
        p50 = sorted_durations[int(count * 0.5)] if count > 0 else 0
        p95 = sorted_durations[min(int(count * 0.95), count - 1)] if count > 0 else 0
        p99 = sorted_durations[min(int(count * 0.99), count - 1)] if count > 0 else 0
        avg = sum(sorted_durations) / count if count > 0 else 0
    else:
        p50 = p95 = p99 = avg = 0

    # Get retry distribution
    retry_key = f"{METRICS_KEY_PREFIX}retries:{operation_name}"
    retries = redis.hgetall(retry_key)
    retry_dist = {k.decode(): int(v) for k, v in retries.items()} if retries else {}

    return {
        "operation": operation_name,
        "total_count": total_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "failure_rate": failure_count / total_count if total_count > 0 else 0,
        "duration_ms": {
            "avg": round(avg, 2),
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
        },
        "retry_distribution": retry_dist,
    }


def list_tracked_operations() -> list[str]:
    """List all operation names that have metrics.

    Returns:
        List of operation names
    """
    redis = _get_redis()
    keys = redis.keys(f"{METRICS_KEY_PREFIX}count:*:success")
    operations = set()
    for key in keys:
        # Extract operation name from key: client_metrics:count:{name}:success
        parts = key.decode().split(":")
        if len(parts) >= 3:
            operations.add(parts[2])
    return sorted(operations)
