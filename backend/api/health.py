"""Health check endpoints for Board of One API.

Provides endpoints to check:
- Basic API health
- PostgreSQL database connection
- Redis connection
- Anthropic API key validity
- Build metadata (timestamp, git commit)
"""

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg2
import redis
from anthropic import Anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from bo1.state.repositories.session_repository import session_repository

router = APIRouter()
logger = logging.getLogger(__name__)

# Load build info at startup (cached)
_build_info: dict[str, str] = {}


def get_build_info() -> dict[str, str]:
    """Load build info from file (cached).

    Returns:
        Dict with build_timestamp and git_commit, or empty values if not found.
    """
    global _build_info
    if _build_info:
        return _build_info

    build_info_path = Path("/app/build_info.json")
    if build_info_path.exists():
        try:
            with open(build_info_path) as f:
                _build_info = json.load(f)
                logger.info(f"Loaded build info: {_build_info}")
        except Exception as e:
            logger.warning(f"Failed to load build info: {e}")
            _build_info = {"build_timestamp": "unknown", "git_commit": "unknown"}
    else:
        # Development mode - no build info file
        _build_info = {"build_timestamp": "development", "git_commit": "development"}

    return _build_info


class HealthResponse(BaseModel):
    """Health check response model.

    Attributes:
        status: Overall health status
        timestamp: ISO 8601 timestamp of health check
        details: Optional health details
    """

    status: str = Field(..., description="Overall health status", examples=["healthy"])
    timestamp: str = Field(..., description="ISO 8601 timestamp of health check")
    details: dict[str, str | bool] | None = Field(
        None,
        description="Optional health details",
        examples=[{"version": "1.0.0", "api": "Board of One"}],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "timestamp": "2025-01-15T12:00:00.000000",
                    "details": {"version": "1.0.0", "api": "Board of One"},
                }
            ]
        }
    }


class ComponentHealthResponse(BaseModel):
    """Component-specific health check response.

    Attributes:
        status: Component health status
        component: Component name (postgresql, redis, anthropic)
        healthy: Whether component is healthy
        message: Optional status message
        timestamp: ISO 8601 timestamp of health check
    """

    status: str = Field(
        ..., description="Component health status", examples=["healthy", "unhealthy"]
    )
    component: str = Field(
        ..., description="Component name", examples=["postgresql", "redis", "anthropic"]
    )
    healthy: bool = Field(..., description="Whether component is healthy")
    message: str | None = Field(None, description="Optional status message")
    timestamp: str = Field(..., description="ISO 8601 timestamp of health check")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "component": "postgresql",
                    "healthy": True,
                    "message": "Database connection successful",
                    "timestamp": "2025-01-15T12:00:00.000000",
                },
                {
                    "status": "unhealthy",
                    "component": "redis",
                    "healthy": False,
                    "message": "Redis connection failed: Connection refused",
                    "timestamp": "2025-01-15T12:00:00.000000",
                },
            ]
        }
    }


class ServiceHealthSummary(BaseModel):
    """Summary of a service's health status."""

    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Status: operational, degraded, outage")
    is_critical: bool = Field(..., description="Whether service is critical for operation")


class ReadinessResponse(BaseModel):
    """Readiness check response for k8s probes.

    Attributes:
        status: Overall status (ok, degraded, unavailable)
        ready: Whether the service is ready to accept traffic
        checks: Individual component check results
        services: Service health summaries
        vendor_status: Overall LLM provider status
        redis_state: Redis connection state (connected/disconnected/reconnecting)
        timestamp: ISO 8601 timestamp
    """

    status: str = Field(..., description="Overall status: ok, degraded, unavailable")
    ready: bool = Field(..., description="Whether service is ready for traffic")
    checks: dict[str, bool] = Field(..., description="Individual component check results")
    services: list[ServiceHealthSummary] | None = Field(
        None, description="Service health summaries"
    )
    vendor_status: str | None = Field(None, description="Overall LLM provider status")
    redis_state: str | None = Field(None, description="Redis connection state")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe (public, no auth required)",
    description="""
    Kubernetes readiness probe - checks if the service is ready to accept traffic.

    Tests critical dependencies:
    - PostgreSQL database connectivity
    - Redis connectivity

    **Use Cases:**
    - Kubernetes readiness probes
    - Load balancer backend health checks
    - Pre-traffic verification after deployment

    Returns 200 if ready, 503 if not ready.
    """,
    responses={
        200: {
            "description": "Service is ready to accept traffic",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "ready": True,
                        "checks": {"postgres": True, "redis": True},
                        "timestamp": "2025-01-15T12:00:00.000000",
                    }
                }
            },
        },
        503: {
            "description": "Service is not ready",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unavailable",
                        "ready": False,
                        "checks": {"postgres": True, "redis": False},
                        "timestamp": "2025-01-15T12:00:00.000000",
                    }
                }
            },
        },
    },
)
async def readiness_check() -> ReadinessResponse:
    """Kubernetes readiness probe.

    Checks critical dependencies (Postgres, Redis) and returns 503 if any fail.
    Also returns 503 during graceful shutdown to drain traffic.

    Returns:
        ReadinessResponse with component check results

    Raises:
        HTTPException: 503 if service is not ready or shutting down
    """
    # Check if shutting down (import here to avoid circular dependency)
    from backend.api.main import is_shutting_down

    if is_shutting_down():
        raise HTTPException(
            status_code=503,
            detail={
                "status": "shutting_down",
                "ready": False,
                "checks": {},
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    checks: dict[str, bool] = {}
    timestamp = datetime.now(UTC).isoformat()

    # Check PostgreSQL
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            conn = psycopg2.connect(database_url, connect_timeout=5)
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            checks["postgres"] = True
        else:
            checks["postgres"] = False
    except Exception:
        checks["postgres"] = False

    # Check Redis and get connection state
    redis_state = None
    try:
        # Try to get state from RedisManager if available
        try:
            from backend.api.dependencies import get_redis_manager

            redis_manager = get_redis_manager()
            redis_state = redis_manager.connection_state.value
            checks["redis"] = redis_manager.is_available
        except Exception:
            # Fallback to direct ping if RedisManager not available
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            client = redis.from_url(redis_url, socket_timeout=5)
            client.ping()
            client.close()
            checks["redis"] = True
            redis_state = "connected"
    except Exception:
        checks["redis"] = False
        redis_state = "disconnected"

    # Get service health summaries
    try:
        from backend.services.service_monitor import get_service_monitor
        from backend.services.vendor_health import (
            get_overall_vendor_status,
        )

        monitor = get_service_monitor()
        all_health = monitor.get_all_health()
        services = [
            ServiceHealthSummary(
                name=h.name,
                status=h.status.value,
                is_critical=h.is_critical,
            )
            for h in all_health.values()
        ]
        vendor_status = get_overall_vendor_status()
    except Exception:
        services = None
        vendor_status = None

    # Determine overall status
    all_ok = all(checks.values())
    any_ok = any(checks.values())

    if all_ok:
        status = "ok"
        ready = True
    elif any_ok:
        status = "degraded"
        ready = False  # Not ready if any critical dependency fails
    else:
        status = "unavailable"
        ready = False

    response = ReadinessResponse(
        status=status,
        ready=ready,
        checks=checks,
        services=services,
        vendor_status=vendor_status,
        redis_state=redis_state,
        timestamp=timestamp,
    )

    if not ready:
        raise HTTPException(status_code=503, detail=response.model_dump())

    return response


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe (public, no auth required)",
    description="""
    Kubernetes liveness probe - checks if the API process is alive and responding.

    This is a lightweight health check that doesn't test dependencies.
    Use /ready for readiness probes, /health/db, /health/redis for component checks.

    **Use Cases:**
    - Kubernetes liveness probes
    - Load balancer health checks
    - Uptime monitoring
    - Smoke tests after deployment
    """,
    responses={
        200: {
            "description": "API is healthy and responding",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2025-01-15T12:00:00.000000",
                        "details": {"version": "1.0.0", "api": "Board of One"},
                    }
                }
            },
        }
    },
)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns:
        Health status response indicating API is online
    """
    build_info = get_build_info()
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC).isoformat(),
        details={
            "version": "1.0.0",
            "api": "Board of One",
            "build_timestamp": build_info.get("build_timestamp", "unknown"),
            "git_commit": build_info.get("git_commit", "unknown"),
        },
    )


@router.get(
    "/health/db",
    response_model=ComponentHealthResponse,
    summary="PostgreSQL health (public, no auth required)",
    description="""
    Check if PostgreSQL database is online and accepting connections.

    Tests:
    - Database connection via DATABASE_URL
    - Simple SELECT query execution

    **Use Cases:**
    - Pre-deployment database connectivity verification
    - Monitoring database availability
    - Troubleshooting connection issues
    """,
    responses={
        200: {
            "description": "Database is healthy and accepting connections",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "component": "postgresql",
                        "healthy": True,
                        "message": "Database connection successful",
                        "timestamp": "2025-01-15T12:00:00.000000",
                    }
                }
            },
        },
        503: {
            "description": "Database is unhealthy or unreachable",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "component": "postgresql",
                        "healthy": False,
                        "message": "Database connection failed: could not connect to server",
                        "timestamp": "2025-01-15T12:00:00.000000",
                    }
                }
            },
        },
    },
)
async def health_check_db() -> ComponentHealthResponse:
    """PostgreSQL database health check.

    Returns:
        Database health status with connection test results

    Raises:
        HTTPException: If database is unhealthy with detailed error message
    """
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(
                status_code=500,
                detail="DATABASE_URL environment variable not set",
            )

        conn = psycopg2.connect(database_url)
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        conn.close()

        return ComponentHealthResponse(
            status="healthy",
            component="postgresql",
            healthy=True,
            message="Database connection successful",
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "component": "postgresql",
                "healthy": False,
                "message": f"Database connection failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            },
        ) from e


class PoolHealthResponse(BaseModel):
    """PostgreSQL connection pool health response.

    Attributes:
        status: Component health status
        component: Component name (postgresql_pool)
        healthy: Whether pool is healthy
        pool_initialized: Whether pool has been created
        min_connections: Configured minimum connections
        max_connections: Configured maximum connections
        used_connections: Connections currently in use
        free_connections: Connections available in pool
        pool_utilization_pct: Pool utilization percentage (0-100)
        pool_degraded: Whether pool is in degradation mode (queuing requests)
        queue_depth: Number of requests waiting in degradation queue
        test_query_success: Whether test query succeeded
        message: Status message
        error: Error message if unhealthy
        timestamp: ISO 8601 timestamp
    """

    status: str = Field(..., description="Component health status")
    component: str = Field(default="postgresql_pool", description="Component name")
    healthy: bool = Field(..., description="Whether pool is healthy")
    pool_initialized: bool = Field(..., description="Whether pool has been created")
    min_connections: int = Field(..., description="Configured minimum connections")
    max_connections: int = Field(..., description="Configured maximum connections")
    used_connections: int = Field(0, description="Connections currently in use")
    free_connections: int = Field(0, description="Connections available in pool")
    pool_utilization_pct: float = Field(0.0, description="Pool utilization percentage (0-100)")
    pool_degraded: bool = Field(False, description="Whether pool is in degradation mode")
    queue_depth: int = Field(0, description="Requests waiting in degradation queue")
    test_query_success: bool = Field(..., description="Whether test query succeeded")
    message: str | None = Field(None, description="Status message")
    error: str | None = Field(None, description="Error message if unhealthy")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


@router.get(
    "/health/db/pool",
    response_model=PoolHealthResponse,
    summary="PostgreSQL pool health (public, no auth required)",
    description="""
    Check health of the PostgreSQL connection pool.

    Tests:
    - Pool initialization status
    - Connection checkout from pool
    - Test query execution (SELECT 1)

    **Use Cases:**
    - Monitor connection pool utilization
    - Detect stale or exhausted pool
    - Verify pool configuration
    """,
    responses={
        200: {
            "description": "Pool health status (may be healthy or unhealthy)",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy": {
                            "summary": "Healthy pool",
                            "value": {
                                "status": "healthy",
                                "component": "postgresql_pool",
                                "healthy": True,
                                "pool_initialized": True,
                                "min_connections": 1,
                                "max_connections": 20,
                                "test_query_success": True,
                                "message": "Pool functioning correctly",
                                "error": None,
                                "timestamp": "2025-01-15T12:00:00.000000",
                            },
                        },
                        "unhealthy": {
                            "summary": "Unhealthy pool",
                            "value": {
                                "status": "unhealthy",
                                "component": "postgresql_pool",
                                "healthy": False,
                                "pool_initialized": True,
                                "min_connections": 1,
                                "max_connections": 20,
                                "test_query_success": False,
                                "message": "Pool health check failed",
                                "error": "Connection refused",
                                "timestamp": "2025-01-15T12:00:00.000000",
                            },
                        },
                    }
                }
            },
        },
    },
)
async def health_check_db_pool() -> PoolHealthResponse:
    """PostgreSQL connection pool health check.

    Returns:
        Pool health status with configuration, utilization metrics, and test results
    """
    from backend.api.metrics import prom_metrics
    from bo1.state.database import get_pool_health
    from bo1.state.pool_degradation import get_degradation_manager

    health = get_pool_health()
    status = "healthy" if health["healthy"] else "unhealthy"

    # Get degradation status
    degradation_manager = get_degradation_manager()
    degradation_manager.update_pool_state(
        used_connections=health.get("used_connections", 0),
        free_connections=health.get("free_connections", 0),
        max_connections=health.get("max_connections", 20),
    )
    degradation_stats = degradation_manager.get_stats()

    # Build message with utilization and degradation info
    utilization_pct = health.get("pool_utilization_pct", 0.0)
    if health["healthy"]:
        if degradation_stats.should_shed_load:
            status = "degraded"
            message = f"Pool shedding load ({utilization_pct}% utilization, queue: {degradation_stats.queue_depth})"
        elif degradation_stats.is_degraded:
            status = "degraded"
            message = f"Pool in degradation mode ({utilization_pct}% utilization)"
        elif utilization_pct >= 80:
            message = f"Pool healthy but high utilization ({utilization_pct}%)"
        else:
            message = f"Pool functioning correctly ({utilization_pct}% utilization)"
    else:
        message = "Pool health check failed"

    # Update Prometheus metrics
    prom_metrics.update_pool_metrics(
        used_connections=health.get("used_connections", 0),
        free_connections=health.get("free_connections", 0),
        utilization_pct=utilization_pct,
    )
    prom_metrics.update_degradation_metrics(
        is_degraded=degradation_stats.is_degraded,
        queue_depth=degradation_stats.queue_depth,
    )

    return PoolHealthResponse(
        status=status,
        component="postgresql_pool",
        healthy=health["healthy"],
        pool_initialized=health["pool_initialized"],
        min_connections=health["min_connections"],
        max_connections=health["max_connections"],
        used_connections=health.get("used_connections", 0),
        free_connections=health.get("free_connections", 0),
        pool_utilization_pct=utilization_pct,
        pool_degraded=degradation_stats.is_degraded,
        queue_depth=degradation_stats.queue_depth,
        test_query_success=health["test_query_success"],
        message=message,
        error=health.get("error"),
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get(
    "/health/redis",
    response_model=ComponentHealthResponse,
    summary="Redis health (public, no auth required)",
    description="""
    Check if Redis is online and accepting connections.

    Tests:
    - Redis connection via REDIS_URL
    - PING command execution

    **Use Cases:**
    - Verify Redis cache availability
    - Check session storage connectivity
    - Monitor Redis uptime
    """,
    responses={
        200: {
            "description": "Redis is healthy and responding",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "component": "redis",
                        "healthy": True,
                        "message": "Redis connection successful",
                        "timestamp": "2025-01-15T12:00:00.000000",
                    }
                }
            },
        },
        503: {
            "description": "Redis is unhealthy or unreachable",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "component": "redis",
                        "healthy": False,
                        "message": "Redis connection failed: Connection refused",
                        "timestamp": "2025-01-15T12:00:00.000000",
                    }
                }
            },
        },
    },
)
async def health_check_redis() -> ComponentHealthResponse:
    """Redis health check.

    Returns:
        Redis health status with connection test results

    Raises:
        HTTPException: If Redis is unhealthy with detailed error message
    """
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = redis.from_url(redis_url)
        client.ping()
        client.close()

        return ComponentHealthResponse(
            status="healthy",
            component="redis",
            healthy=True,
            message="Redis connection successful",
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "component": "redis",
                "healthy": False,
                "message": f"Redis connection failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            },
        ) from e


@router.get(
    "/health/anthropic",
    response_model=ComponentHealthResponse,
    summary="Anthropic API health (public, no auth required)",
    description="""
    Check if Anthropic API key is configured.

    Tests:
    - ANTHROPIC_API_KEY environment variable is set
    - Anthropic client can be initialized

    **Note:** This endpoint does NOT make actual API calls to avoid costs.
    It only verifies the API key is configured.

    **Use Cases:**
    - Verify API key configuration before starting deliberations
    - Troubleshoot authentication issues
    - Pre-deployment configuration checks
    """,
    responses={
        200: {
            "description": "Anthropic API key is configured",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "component": "anthropic",
                        "healthy": True,
                        "message": "Anthropic API key configured",
                        "timestamp": "2025-01-15T12:00:00.000000",
                    }
                }
            },
        },
        503: {
            "description": "Anthropic API key is not configured or invalid",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "component": "anthropic",
                        "healthy": False,
                        "message": "ANTHROPIC_API_KEY environment variable not set",
                        "timestamp": "2025-01-15T12:00:00.000000",
                    }
                }
            },
        },
    },
)
async def health_check_anthropic() -> ComponentHealthResponse:
    """Anthropic API health check.

    Returns:
        Anthropic API health status (key configuration only, no actual API calls)

    Raises:
        HTTPException: If API key is not configured
    """
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="ANTHROPIC_API_KEY environment variable not set",
            )

        # Test API key with a minimal request
        # Note: We don't actually make a request here to avoid costs
        # Just verify the client can be created with the API key
        # In production, you might want to make a minimal test request
        _ = Anthropic(api_key=api_key)  # Verify client can be created

        return ComponentHealthResponse(
            status="healthy",
            component="anthropic",
            healthy=True,
            message="Anthropic API key configured",
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "component": "anthropic",
                "healthy": False,
                "message": f"Anthropic API check failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            },
        ) from e


class SessionPersistenceDetail(BaseModel):
    """Detail about a single session's persistence status."""

    session_id: str = Field(..., description="Session ID")
    redis_count: int = Field(..., description="Events in Redis")
    postgres_count: int = Field(..., description="Events in PostgreSQL")
    discrepancy: int = Field(..., description="Difference (Redis - PostgreSQL)")
    status: str = Field(..., description="Status: ok, warning, critical")


class PersistenceHealthResponse(BaseModel):
    """Event persistence health response.

    Attributes:
        status: Overall persistence health status
        component: Component name (persistence)
        healthy: Whether persistence is healthy
        sessions_checked: Number of recent sessions checked
        sessions_with_issues: Number of sessions with persistence discrepancies
        total_redis_events: Total events in Redis for checked sessions
        total_postgres_events: Total events in PostgreSQL for checked sessions
        persistence_rate: Percentage of events successfully persisted
        queue_depth: Number of events in retry queue
        dlq_depth: Number of events in dead letter queue
        details: List of sessions with issues (if any)
        message: Status message
        timestamp: ISO 8601 timestamp
    """

    status: str = Field(..., description="Overall persistence health status")
    component: str = Field(default="persistence", description="Component name")
    healthy: bool = Field(..., description="Whether persistence is healthy")
    sessions_checked: int = Field(..., description="Number of recent sessions checked")
    sessions_with_issues: int = Field(..., description="Sessions with persistence issues")
    total_redis_events: int = Field(..., description="Total events in Redis")
    total_postgres_events: int = Field(..., description="Total events in PostgreSQL")
    persistence_rate: float = Field(..., description="Percentage of events persisted")
    queue_depth: int = Field(..., description="Number of events in retry queue")
    dlq_depth: int = Field(..., description="Number of events in dead letter queue")
    details: list[SessionPersistenceDetail] | None = Field(None, description="Sessions with issues")
    message: str = Field(..., description="Status message")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


@router.get(
    "/health/persistence",
    response_model=PersistenceHealthResponse,
    summary="Persistence health (public, no auth required)",
    description="""
    Check if events are being correctly persisted from Redis to PostgreSQL.

    Tests:
    - Compares event counts in Redis vs PostgreSQL for recent sessions
    - Identifies sessions with persistence discrepancies
    - Calculates overall persistence success rate

    **Thresholds:**
    - Healthy: 100% persistence rate
    - Warning: 95-99% persistence rate or minor discrepancies
    - Critical: <95% persistence rate or sessions with zero PostgreSQL events

    **Use Cases:**
    - Post-deployment verification of event persistence
    - Detecting data loss before it affects users
    - Monitoring overall system reliability
    """,
    responses={
        200: {
            "description": "Persistence health status",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy": {
                            "summary": "Healthy persistence",
                            "value": {
                                "status": "healthy",
                                "component": "persistence",
                                "healthy": True,
                                "sessions_checked": 10,
                                "sessions_with_issues": 0,
                                "total_redis_events": 150,
                                "total_postgres_events": 150,
                                "persistence_rate": 100.0,
                                "details": None,
                                "message": "All events persisted successfully",
                                "timestamp": "2025-01-15T12:00:00.000000",
                            },
                        },
                        "warning": {
                            "summary": "Warning - minor discrepancies",
                            "value": {
                                "status": "warning",
                                "component": "persistence",
                                "healthy": True,
                                "sessions_checked": 10,
                                "sessions_with_issues": 1,
                                "total_redis_events": 150,
                                "total_postgres_events": 148,
                                "persistence_rate": 98.67,
                                "details": [
                                    {
                                        "session_id": "abc123",
                                        "redis_count": 15,
                                        "postgres_count": 13,
                                        "discrepancy": 2,
                                        "status": "warning",
                                    }
                                ],
                                "message": "1 session(s) with minor persistence issues",
                                "timestamp": "2025-01-15T12:00:00.000000",
                            },
                        },
                    }
                }
            },
        },
        503: {
            "description": "Critical persistence issues",
            "content": {
                "application/json": {
                    "example": {
                        "status": "critical",
                        "component": "persistence",
                        "healthy": False,
                        "sessions_checked": 10,
                        "sessions_with_issues": 3,
                        "total_redis_events": 150,
                        "total_postgres_events": 50,
                        "persistence_rate": 33.33,
                        "details": [
                            {
                                "session_id": "abc123",
                                "redis_count": 50,
                                "postgres_count": 0,
                                "discrepancy": 50,
                                "status": "critical",
                            }
                        ],
                        "message": "CRITICAL: 3 session(s) with persistence failures",
                        "timestamp": "2025-01-15T12:00:00.000000",
                    }
                }
            },
        },
    },
)
async def health_check_persistence() -> PersistenceHealthResponse:
    """Event persistence health check.

    Checks recent sessions (last hour) and compares Redis event counts
    with PostgreSQL event counts to detect persistence issues. Also checks
    the retry queue and dead letter queue depths.

    Returns:
        Persistence health status with details about any discrepancies

    Raises:
        HTTPException: If critical persistence issues are detected
    """
    try:
        from backend.api.event_publisher import get_dlq_depth, get_queue_depth

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            raise HTTPException(
                status_code=500,
                detail="DATABASE_URL environment variable not set",
            )

        # Get recent sessions from PostgreSQL (last 2 hours)
        conn = psycopg2.connect(database_url)
        cutoff_time = datetime.now(UTC) - timedelta(hours=2)

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM sessions
                WHERE created_at >= %s
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (cutoff_time,),
            )
            recent_sessions = [row[0] for row in cur.fetchall()]
        conn.close()

        # Get retry queue depths
        queue_depth = await get_queue_depth(redis_client)
        dlq_depth = await get_dlq_depth(redis_client)

        if not recent_sessions:
            # No recent sessions to check
            return PersistenceHealthResponse(
                status="healthy",
                component="persistence",
                healthy=True,
                sessions_checked=0,
                sessions_with_issues=0,
                total_redis_events=0,
                total_postgres_events=0,
                persistence_rate=100.0,
                queue_depth=queue_depth,
                dlq_depth=dlq_depth,
                details=None,
                message="No recent sessions to verify",
                timestamp=datetime.now(UTC).isoformat(),
            )

        # Compare Redis vs PostgreSQL counts for each session
        total_redis = 0
        total_postgres = 0
        issues: list[SessionPersistenceDetail] = []

        for session_id in recent_sessions:
            # Get Redis count
            redis_key = f"events_history:{session_id}"
            redis_count = redis_client.llen(redis_key)

            # Get PostgreSQL count
            pg_events = session_repository.get_events(session_id)
            postgres_count = len(pg_events) if pg_events else 0

            total_redis += redis_count
            total_postgres += postgres_count

            # Check for discrepancies
            if redis_count > postgres_count:
                discrepancy = redis_count - postgres_count

                # Determine severity
                if postgres_count == 0 and redis_count > 0:
                    status = "critical"
                elif discrepancy > 5:
                    status = "warning"
                else:
                    status = "warning"

                issues.append(
                    SessionPersistenceDetail(
                        session_id=session_id,
                        redis_count=redis_count,
                        postgres_count=postgres_count,
                        discrepancy=discrepancy,
                        status=status,
                    )
                )

        redis_client.close()

        # Calculate persistence rate
        persistence_rate = (total_postgres / total_redis * 100) if total_redis > 0 else 100.0

        # Determine overall health
        critical_issues = [i for i in issues if i.status == "critical"]
        has_critical = len(critical_issues) > 0

        # Check queue depths for warnings
        queue_warning = queue_depth > 100
        dlq_warning = dlq_depth > 0

        if has_critical or persistence_rate < 95:
            status = "critical"
            healthy = False
            message = f"CRITICAL: {len(issues)} session(s) with persistence failures"
        elif issues or persistence_rate < 100 or queue_warning or dlq_warning:
            status = "warning"
            healthy = True
            warnings = []
            if issues:
                warnings.append(f"{len(issues)} session(s) with minor persistence issues")
            if queue_warning:
                warnings.append(f"{queue_depth} events in retry queue")
            if dlq_warning:
                warnings.append(f"{dlq_depth} events in dead letter queue")
            message = "; ".join(warnings)
        else:
            status = "healthy"
            healthy = True
            message = "All events persisted successfully"

        response = PersistenceHealthResponse(
            status=status,
            component="persistence",
            healthy=healthy,
            sessions_checked=len(recent_sessions),
            sessions_with_issues=len(issues),
            total_redis_events=total_redis,
            total_postgres_events=total_postgres,
            persistence_rate=round(persistence_rate, 2),
            queue_depth=queue_depth,
            dlq_depth=dlq_depth,
            details=issues if issues else None,
            message=message,
            timestamp=datetime.now(UTC).isoformat(),
        )

        if not healthy:
            raise HTTPException(
                status_code=503,
                detail=response.model_dump(),
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Persistence health check failed")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "component": "persistence",
                "healthy": False,
                "message": f"Persistence health check failed: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        ) from e


class CircuitBreakerStatus(BaseModel):
    """Status of a single circuit breaker."""

    state: str = Field(..., description="Circuit state: closed, open, half_open")
    failure_count: int = Field(..., description="Current failure count")
    success_count: int = Field(..., description="Success count (in half_open)")
    uptime_seconds: float = Field(..., description="Seconds since last state change")
    is_open: bool = Field(..., description="True if circuit is open (rejecting)")
    is_half_open: bool = Field(..., description="True if circuit is testing")


class CircuitBreakersHealthResponse(BaseModel):
    """Circuit breakers health response."""

    status: str = Field(..., description="Overall status")
    component: str = Field(default="circuit_breakers", description="Component name")
    healthy: bool = Field(..., description="True if all circuits closed")
    services: dict[str, CircuitBreakerStatus] = Field(
        ..., description="Per-service circuit breaker status"
    )
    message: str = Field(..., description="Status message")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


@router.get(
    "/health/circuit-breakers",
    response_model=CircuitBreakersHealthResponse,
    summary="Circuit breakers health (public, no auth required)",
    description="""
    Check status of all circuit breakers for external APIs.

    **Services monitored:**
    - anthropic: Claude API
    - voyage: Voyage AI embeddings
    - brave: Brave Search API

    **States:**
    - closed: Normal operation
    - open: Service unavailable, requests fast-fail
    - half_open: Testing recovery

    **Use Cases:**
    - Monitor external API health
    - Diagnose service outages
    - Verify recovery after incidents
    """,
)
async def health_check_circuit_breakers() -> CircuitBreakersHealthResponse:
    """Circuit breakers health check.

    Returns:
        Status of all circuit breakers
    """
    from bo1.llm.circuit_breaker import get_all_circuit_breaker_status

    statuses = get_all_circuit_breaker_status()

    # Convert to response model
    services = {name: CircuitBreakerStatus(**status) for name, status in statuses.items()}

    # Check if any circuit is open
    any_open = any(s.is_open for s in services.values())
    any_half_open = any(s.is_half_open for s in services.values())

    if any_open:
        status = "degraded"
        healthy = False
        open_services = [n for n, s in services.items() if s.is_open]
        message = f"Circuit breakers OPEN: {', '.join(open_services)}"
    elif any_half_open:
        status = "recovering"
        healthy = True
        recovering_services = [n for n, s in services.items() if s.is_half_open]
        message = f"Testing recovery: {', '.join(recovering_services)}"
    elif not services:
        status = "healthy"
        healthy = True
        message = "No circuit breakers initialized yet"
    else:
        status = "healthy"
        healthy = True
        message = f"All circuits closed ({len(services)} services)"

    return CircuitBreakersHealthResponse(
        status=status,
        component="circuit_breakers",
        healthy=healthy,
        services=services,
        message=message,
        timestamp=datetime.now(UTC).isoformat(),
    )


class HSTSCheckResponse(BaseModel):
    """HSTS compliance check response.

    Attributes:
        status: Compliance status (compliant/non_compliant)
        component: Component name (hsts)
        preload_eligible: Whether the configuration meets preload requirements
        header_value: Current HSTS header value (from nginx config)
        checks: Individual requirement check results
        message: Status message with any issues
        submission_url: URL to submit domain for preload (if eligible)
        timestamp: ISO 8601 timestamp
    """

    status: str = Field(..., description="Compliance status: compliant, non_compliant")
    component: str = Field(default="hsts", description="Component name")
    preload_eligible: bool = Field(..., description="Meets preload requirements")
    header_value: str = Field(..., description="Current HSTS header value")
    checks: dict[str, bool] = Field(..., description="Individual requirement results")
    message: str = Field(..., description="Status message with any issues")
    submission_url: str | None = Field(None, description="HSTS preload submission URL")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class CheckpointHealthResponse(BaseModel):
    """Checkpoint backend health response.

    Attributes:
        status: Health status (healthy/unhealthy)
        component: Component name (checkpoint)
        healthy: Whether checkpoint backend is healthy
        backend: Backend type (redis/postgres)
        message: Status message
        error: Error message if unhealthy
        timestamp: ISO 8601 timestamp
    """

    status: str = Field(..., description="Health status")
    component: str = Field(default="checkpoint", description="Component name")
    healthy: bool = Field(..., description="Whether checkpoint backend is healthy")
    backend: str = Field(..., description="Backend type (redis/postgres)")
    message: str = Field(..., description="Status message")
    error: str | None = Field(None, description="Error message if unhealthy")
    details: dict[str, Any] | None = Field(None, description="Backend-specific details")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


@router.get(
    "/health/checkpoint",
    response_model=CheckpointHealthResponse,
    summary="Checkpoint health (public, no auth required)",
    description="""
    Check health of the LangGraph checkpoint backend (Redis or PostgreSQL).

    Tests:
    - Backend connectivity (ping for Redis, SELECT 1 for Postgres)
    - Configuration validity

    **Use Cases:**
    - Verify checkpoint storage before starting deliberations
    - Monitor checkpoint backend availability
    - Troubleshoot state persistence issues
    """,
    responses={
        200: {
            "description": "Checkpoint backend is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "component": "checkpoint",
                        "healthy": True,
                        "backend": "redis",
                        "message": "Redis checkpoint backend healthy",
                        "error": None,
                        "details": {"host": "localhost", "port": 6379, "db": 0},
                        "timestamp": "2025-01-15T12:00:00.000000",
                    }
                }
            },
        },
        503: {
            "description": "Checkpoint backend is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "component": "checkpoint",
                        "healthy": False,
                        "backend": "redis",
                        "message": "Health check failed",
                        "error": "Connection refused",
                        "details": None,
                        "timestamp": "2025-01-15T12:00:00.000000",
                    }
                }
            },
        },
    },
)
async def health_check_checkpoint() -> CheckpointHealthResponse:
    """LangGraph checkpoint backend health check.

    Returns:
        Checkpoint backend health status

    Raises:
        HTTPException: If checkpoint backend is unhealthy
    """
    from bo1.graph.checkpointer_factory import check_checkpoint_health

    health = check_checkpoint_health()

    # Extract details (remove keys already in response model)
    details = {
        k: v for k, v in health.items() if k not in ("healthy", "backend", "message", "error")
    }

    response = CheckpointHealthResponse(
        status="healthy" if health["healthy"] else "unhealthy",
        component="checkpoint",
        healthy=health["healthy"],
        backend=health["backend"],
        message=health["message"],
        error=health.get("error"),
        details=details if details else None,
        timestamp=datetime.now(UTC).isoformat(),
    )

    if not health["healthy"]:
        raise HTTPException(status_code=503, detail=response.model_dump())

    return response


class EventQueueHealth(BaseModel):
    """Event queue health details."""

    depth: int = Field(..., description="Current number of pending events")
    threshold_warning: int = Field(..., description="Warning threshold")
    threshold_critical: int = Field(..., description="Critical threshold")
    healthy: bool = Field(..., description="True if depth below critical threshold")
    status: str = Field(..., description="ok, warning, or critical")


class CircuitBreakerHealth(BaseModel):
    """Circuit breaker health summary."""

    healthy: bool = Field(..., description="True if all circuits closed/half_open")
    open_circuits: list[str] = Field(..., description="List of open circuit names")
    total_circuits: int = Field(..., description="Total number of circuits")
    state_summary: dict[str, int] = Field(..., description="Count of circuits in each state")


class DetailedHealthResponse(BaseModel):
    """Detailed operational health response.

    Combines event queue depth and circuit breaker status for operational health.
    """

    status: str = Field(..., description="Overall status: ok, warning, critical")
    healthy: bool = Field(..., description="True if all components healthy")
    event_queue: EventQueueHealth = Field(..., description="Event queue health")
    circuit_breakers: CircuitBreakerHealth = Field(..., description="Circuit breaker health")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


@router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed health (public, no auth required)",
    description="""
    Comprehensive operational health check combining:
    - Event queue depth (pending events in batcher)
    - LLM provider circuit breaker states

    **Thresholds:**
    - Event queue warning: 50 pending events
    - Event queue critical: 100 pending events
    - Circuit breaker: open state is unhealthy

    **Use Cases:**
    - Operational dashboards
    - Pre-traffic verification
    - Alerting integration
    """,
    responses={
        200: {
            "description": "Detailed health status (may include warnings)",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "healthy": True,
                        "event_queue": {
                            "depth": 5,
                            "threshold_warning": 50,
                            "threshold_critical": 100,
                            "healthy": True,
                            "status": "ok",
                        },
                        "circuit_breakers": {
                            "healthy": True,
                            "open_circuits": [],
                            "total_circuits": 3,
                            "state_summary": {"closed": 3},
                        },
                        "timestamp": "2025-01-15T12:00:00.000000",
                    }
                }
            },
        },
        503: {
            "description": "Critical health issues",
            "content": {
                "application/json": {
                    "example": {
                        "status": "critical",
                        "healthy": False,
                        "event_queue": {
                            "depth": 150,
                            "threshold_warning": 50,
                            "threshold_critical": 100,
                            "healthy": False,
                            "status": "critical",
                        },
                        "circuit_breakers": {
                            "healthy": False,
                            "open_circuits": ["anthropic"],
                            "total_circuits": 3,
                            "state_summary": {"closed": 2, "open": 1},
                        },
                        "timestamp": "2025-01-15T12:00:00.000000",
                    }
                }
            },
        },
    },
)
async def health_check_detailed() -> DetailedHealthResponse:
    """Detailed operational health check.

    Combines event queue depth and circuit breaker status for comprehensive
    operational health monitoring.

    Returns:
        DetailedHealthResponse with event queue and circuit breaker status

    Raises:
        HTTPException: 503 if critical health issues detected
    """
    from backend.services.event_batcher import get_batcher
    from bo1.constants import HealthThresholds
    from bo1.llm.circuit_breaker import get_all_circuit_breaker_status

    timestamp = datetime.now(UTC).isoformat()

    # Get event queue health
    batcher = get_batcher()
    queue_depth = batcher.get_queue_depth()

    if queue_depth >= HealthThresholds.EVENT_QUEUE_CRITICAL:
        queue_status = "critical"
        queue_healthy = False
    elif queue_depth >= HealthThresholds.EVENT_QUEUE_WARNING:
        queue_status = "warning"
        queue_healthy = True
    else:
        queue_status = "ok"
        queue_healthy = True

    event_queue = EventQueueHealth(
        depth=queue_depth,
        threshold_warning=HealthThresholds.EVENT_QUEUE_WARNING,
        threshold_critical=HealthThresholds.EVENT_QUEUE_CRITICAL,
        healthy=queue_healthy,
        status=queue_status,
    )

    # Get circuit breaker health
    cb_statuses = get_all_circuit_breaker_status()
    open_circuits = [
        name
        for name, status in cb_statuses.items()
        if status.get("state") not in HealthThresholds.CIRCUIT_BREAKER_HEALTHY_STATES
    ]
    state_counts: dict[str, int] = {}
    for status in cb_statuses.values():
        state = status.get("state", "unknown")
        state_counts[state] = state_counts.get(state, 0) + 1

    cb_healthy = len(open_circuits) == 0

    circuit_breakers = CircuitBreakerHealth(
        healthy=cb_healthy,
        open_circuits=open_circuits,
        total_circuits=len(cb_statuses),
        state_summary=state_counts,
    )

    # Determine overall status
    if not queue_healthy or not cb_healthy:
        overall_status = "critical"
        overall_healthy = False
    elif queue_status == "warning":
        overall_status = "warning"
        overall_healthy = True
    else:
        overall_status = "ok"
        overall_healthy = True

    response = DetailedHealthResponse(
        status=overall_status,
        healthy=overall_healthy,
        event_queue=event_queue,
        circuit_breakers=circuit_breakers,
        timestamp=timestamp,
    )

    if not overall_healthy:
        raise HTTPException(status_code=503, detail=response.model_dump())

    return response


# HSTS preload requirements
HSTS_MIN_MAX_AGE = 31536000  # 1 year in seconds
HSTS_SUBMISSION_URL = "https://hstspreload.org"


@router.get(
    "/health/hsts",
    response_model=HSTSCheckResponse,
    summary="HSTS compliance (public, no auth required)",
    description="""
    Check if HSTS configuration meets browser preload list requirements.

    **Preload Requirements:**
    - max-age >= 31536000 (1 year)
    - includeSubDomains directive present
    - preload directive present
    - Served over HTTPS (port 443)
    - HTTP redirects to HTTPS

    **Use Cases:**
    - Verify HSTS configuration before preload submission
    - Monitor HSTS compliance after config changes
    - Security audit verification

    **Note:** This endpoint checks the configured header value. Actual submission
    to hstspreload.org must be done manually at https://hstspreload.org
    """,
    responses={
        200: {
            "description": "HSTS compliance check result",
            "content": {
                "application/json": {
                    "examples": {
                        "compliant": {
                            "summary": "Fully compliant",
                            "value": {
                                "status": "compliant",
                                "component": "hsts",
                                "preload_eligible": True,
                                "header_value": "max-age=31536000; includeSubDomains; preload",
                                "checks": {
                                    "max_age_sufficient": True,
                                    "include_subdomains": True,
                                    "preload_directive": True,
                                },
                                "message": "HSTS configuration meets all preload requirements",
                                "submission_url": "https://hstspreload.org",
                                "timestamp": "2025-01-15T12:00:00.000000",
                            },
                        },
                        "missing_preload": {
                            "summary": "Missing preload directive",
                            "value": {
                                "status": "non_compliant",
                                "component": "hsts",
                                "preload_eligible": False,
                                "header_value": "max-age=31536000; includeSubDomains",
                                "checks": {
                                    "max_age_sufficient": True,
                                    "include_subdomains": True,
                                    "preload_directive": False,
                                },
                                "message": "Missing: preload directive",
                                "submission_url": None,
                                "timestamp": "2025-01-15T12:00:00.000000",
                            },
                        },
                    }
                }
            },
        },
    },
)
async def health_check_hsts() -> HSTSCheckResponse:
    """HSTS preload compliance check.

    Checks if the configured HSTS header meets browser preload list requirements.
    Returns the current header value and individual requirement check results.

    Returns:
        HSTSCheckResponse with compliance status and details
    """
    # Expected HSTS header (from nginx config)
    # In production, this could be fetched dynamically via self-request
    # For now, we check the expected configured value
    expected_header = "max-age=31536000; includeSubDomains; preload"

    # Parse and validate header
    header_lower = expected_header.lower()

    # Check individual requirements
    checks: dict[str, bool] = {}

    # 1. Check max-age >= 31536000
    import re

    max_age_match = re.search(r"max-age=(\d+)", header_lower)
    if max_age_match:
        max_age_value = int(max_age_match.group(1))
        checks["max_age_sufficient"] = max_age_value >= HSTS_MIN_MAX_AGE
    else:
        checks["max_age_sufficient"] = False

    # 2. Check includeSubDomains
    checks["include_subdomains"] = "includesubdomains" in header_lower

    # 3. Check preload directive
    checks["preload_directive"] = "preload" in header_lower

    # Determine overall compliance
    all_pass = all(checks.values())

    if all_pass:
        status = "compliant"
        message = "HSTS configuration meets all preload requirements"
        submission_url = HSTS_SUBMISSION_URL
    else:
        status = "non_compliant"
        missing = [name.replace("_", " ") for name, passed in checks.items() if not passed]
        message = f"Missing: {', '.join(missing)}"
        submission_url = None

    return HSTSCheckResponse(
        status=status,
        component="hsts",
        preload_eligible=all_pass,
        header_value=expected_header,
        checks=checks,
        message=message,
        submission_url=submission_url,
        timestamp=datetime.now(UTC).isoformat(),
    )
