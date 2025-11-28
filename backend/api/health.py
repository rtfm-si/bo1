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
from datetime import datetime
from pathlib import Path

import psycopg2
import redis
from anthropic import Anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic health check",
    description="""
    Check if the Board of One API is online and responding.

    This is a lightweight health check that doesn't test dependencies.
    Use /health/db, /health/redis, or /health/anthropic to test specific components.

    **Use Cases:**
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
        timestamp=datetime.utcnow().isoformat(),
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
    summary="PostgreSQL database health check",
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
    test_query_success: bool = Field(..., description="Whether test query succeeded")
    message: str | None = Field(None, description="Status message")
    error: str | None = Field(None, description="Error message if unhealthy")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


@router.get(
    "/health/db/pool",
    response_model=PoolHealthResponse,
    summary="PostgreSQL connection pool health check",
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
        Pool health status with configuration and test results
    """
    from bo1.state.postgres_manager import get_pool_health

    health = get_pool_health()
    status = "healthy" if health["healthy"] else "unhealthy"
    message = "Pool functioning correctly" if health["healthy"] else "Pool health check failed"

    return PoolHealthResponse(
        status=status,
        component="postgresql_pool",
        healthy=health["healthy"],
        pool_initialized=health["pool_initialized"],
        min_connections=health["min_connections"],
        max_connections=health["max_connections"],
        test_query_success=health["test_query_success"],
        message=message,
        error=health.get("error"),
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get(
    "/health/redis",
    response_model=ComponentHealthResponse,
    summary="Redis health check",
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
    summary="Anthropic API health check",
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
