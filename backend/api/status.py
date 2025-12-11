"""Service status endpoints.

Provides:
- GET /api/v1/status - Public status (no auth) for frontend banner
- GET /api/admin/services/status - Detailed admin status
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.api.middleware.auth import require_admin
from backend.services.service_monitor import (
    get_detailed_status,
    get_system_status,
)
from backend.services.vendor_health import (
    get_all_provider_status,
)
from bo1.llm.circuit_breaker import get_all_circuit_breaker_status

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Response Models ---


class ServiceStatusItem(BaseModel):
    """Status of a single service."""

    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Status: operational, degraded, outage")
    error_rate: float | None = Field(None, description="Error rate (0-1)")
    latency_p50_ms: float | None = Field(None, description="Median latency")
    latency_p95_ms: float | None = Field(None, description="95th percentile latency")


class PublicStatusResponse(BaseModel):
    """Public service status for frontend banner.

    Attributes:
        status: Overall status (operational, degraded, outage)
        message: User-friendly message if not operational
        services: List of affected services (only non-operational)
    """

    status: str = Field(..., description="Overall status: operational, degraded, outage")
    message: str | None = Field(None, description="User-friendly status message")
    services: list[ServiceStatusItem] | None = Field(
        None, description="Affected services (only if degraded/outage)"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "operational",
                    "message": None,
                    "services": None,
                    "timestamp": "2025-01-15T12:00:00.000000",
                },
                {
                    "status": "degraded",
                    "message": "Some features may be slow or unavailable. We're working on it.",
                    "services": [{"name": "anthropic", "status": "degraded", "error_rate": 0.25}],
                    "timestamp": "2025-01-15T12:00:00.000000",
                },
            ]
        }
    }


class CircuitBreakerStatusItem(BaseModel):
    """Circuit breaker status for a service."""

    state: str = Field(..., description="Circuit state: closed, open, half_open")
    failure_count: int = Field(..., description="Current failure count")
    is_open: bool = Field(..., description="True if circuit is open (rejecting)")
    uptime_seconds: float = Field(..., description="Seconds since last state change")


class IncidentItem(BaseModel):
    """Historical incident record."""

    service: str = Field(..., description="Service name")
    old_status: str = Field(..., description="Previous status")
    new_status: str = Field(..., description="New status")
    timestamp: float = Field(..., description="Unix timestamp")
    error_rate: float | None = Field(None, description="Error rate at transition")


class DetailedServiceStatus(BaseModel):
    """Detailed status for admin view."""

    name: str
    status: str
    error_rate: float
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    last_check: float | None
    last_error: str | None
    is_critical: bool


class AdminStatusResponse(BaseModel):
    """Detailed service status for admin dashboard.

    Includes circuit breaker states, recent incidents, and detailed metrics.
    """

    status: str = Field(..., description="Overall status")
    message: str | None = Field(None, description="Status message")
    services: dict[str, DetailedServiceStatus] = Field(
        ..., description="Per-service detailed status"
    )
    circuit_breakers: dict[str, CircuitBreakerStatusItem] = Field(
        ..., description="Circuit breaker states"
    )
    vendor_health: dict[str, Any] = Field(..., description="LLM provider health")
    incidents_24h: list[IncidentItem] = Field(..., description="Recent incidents")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


# --- Endpoints ---


@router.get(
    "/v1/status",
    response_model=PublicStatusResponse,
    summary="Public service status",
    description="""
    Public service status for frontend status banner. No authentication required.

    Returns overall system status:
    - **operational**: All services healthy
    - **degraded**: Some services experiencing issues
    - **outage**: Critical services unavailable

    Use this endpoint for:
    - Frontend status banner polling (recommended: every 60s)
    - Pre-request health checks
    - Monitoring integration
    """,
    tags=["status"],
)
async def get_public_status() -> PublicStatusResponse:
    """Get public service status for frontend banner.

    No authentication required. Returns minimal info for public consumption.
    """
    system_status = get_system_status()

    # Only include affected services if not operational
    services = None
    if system_status["status"] != "operational":
        services = [
            ServiceStatusItem(
                name=s["name"],
                status=s["status"],
                error_rate=s.get("error_rate"),
                latency_p50_ms=s.get("latency_p50_ms"),
                latency_p95_ms=s.get("latency_p95_ms"),
            )
            for s in system_status.get("services", [])
            if s["status"] != "operational"
        ]

    return PublicStatusResponse(
        status=system_status["status"],
        message=system_status.get("message"),
        services=services if services else None,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/admin/services/status",
    response_model=AdminStatusResponse,
    summary="Admin service status",
    description="""
    Detailed service status for admin dashboard. Requires admin authentication.

    Includes:
    - Per-service metrics (error rate, latency percentiles)
    - Circuit breaker states
    - LLM provider health
    - Recent incidents (last 24h)
    """,
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)
async def get_admin_status() -> AdminStatusResponse:
    """Get detailed service status for admin dashboard.

    Requires admin authentication.
    """
    # Get detailed status from service monitor
    detailed = get_detailed_status()

    # Get circuit breaker states
    cb_statuses = get_all_circuit_breaker_status()
    circuit_breakers = {
        name: CircuitBreakerStatusItem(
            state=status["state"],
            failure_count=status["failure_count"],
            is_open=status["is_open"],
            uptime_seconds=status["uptime_seconds"],
        )
        for name, status in cb_statuses.items()
    }

    # Get vendor health
    vendor_health = get_all_provider_status()

    # Convert services to response model
    services = {}
    for name, svc in detailed.get("services", {}).items():
        services[name] = DetailedServiceStatus(
            name=svc["name"],
            status=svc["status"],
            error_rate=svc["error_rate"],
            latency_p50_ms=svc.get("latency_p50_ms"),
            latency_p95_ms=svc.get("latency_p95_ms"),
            last_check=svc.get("last_check"),
            last_error=svc.get("last_error"),
            is_critical=svc.get("is_critical", True),
        )

    # Convert incidents
    incidents = [
        IncidentItem(
            service=i["service"],
            old_status=i["old_status"],
            new_status=i["new_status"],
            timestamp=i["timestamp"],
            error_rate=i.get("error_rate"),
        )
        for i in detailed.get("incidents_24h", [])
    ]

    return AdminStatusResponse(
        status=detailed["status"],
        message=detailed.get("message"),
        services=services,
        circuit_breakers=circuit_breakers,
        vendor_health=vendor_health,
        incidents_24h=incidents,
        timestamp=datetime.now(UTC).isoformat(),
    )
