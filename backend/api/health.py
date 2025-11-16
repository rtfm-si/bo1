"""Health check endpoints for Board of One API.

Provides endpoints to check:
- Basic API health
- PostgreSQL database connection
- Redis connection
- Anthropic API key validity
"""

import os
from datetime import datetime

import psycopg2
import redis
from anthropic import Anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


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
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        details={
            "version": "1.0.0",
            "api": "Board of One",
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
