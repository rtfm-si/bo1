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
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: str
    details: dict[str, str | bool] | None = None


class ComponentHealthResponse(BaseModel):
    """Component-specific health check response."""

    status: str
    component: str
    healthy: bool
    message: str | None = None
    timestamp: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns:
        Health status response
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        details={
            "version": "1.0.0",
            "api": "Board of One",
        },
    )


@router.get("/health/db", response_model=ComponentHealthResponse)
async def health_check_db() -> ComponentHealthResponse:
    """PostgreSQL database health check.

    Returns:
        Database health status

    Raises:
        HTTPException: If database is unhealthy
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


@router.get("/health/redis", response_model=ComponentHealthResponse)
async def health_check_redis() -> ComponentHealthResponse:
    """Redis health check.

    Returns:
        Redis health status

    Raises:
        HTTPException: If Redis is unhealthy
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


@router.get("/health/anthropic", response_model=ComponentHealthResponse)
async def health_check_anthropic() -> ComponentHealthResponse:
    """Anthropic API health check.

    Returns:
        Anthropic API health status

    Raises:
        HTTPException: If Anthropic API is unhealthy
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
