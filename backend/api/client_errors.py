"""Client error reporting endpoint.

Receives JavaScript errors from the frontend and stores them in audit_log.
This enables tracking of client-side issues for debugging and monitoring.

Rate limited to prevent abuse (10 errors/minute per IP).
"""

import json
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from slowapi.util import get_remote_address

from backend.api.middleware.rate_limit import limiter
from backend.api.utils import RATE_LIMIT_RESPONSE
from backend.api.utils.db_helpers import execute_query
from bo1.logging.errors import ErrorCode, log_error
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/errors", tags=["client-errors"])


class ClientErrorReport(BaseModel):
    """Client-side error report from frontend."""

    error: str = Field(..., max_length=1000, description="Error message")
    stack: str | None = Field(None, max_length=10000, description="Stack trace")
    url: str = Field(..., max_length=2000, description="Page URL where error occurred")
    component: str | None = Field(None, max_length=200, description="Component name if available")
    correlation_id: str | None = Field(None, max_length=100, description="Request correlation ID")
    context: dict[str, Any] | None = Field(None, description="Additional context")


class ClientErrorResponse(BaseModel):
    """Response for client error report."""

    success: bool
    message: str


@router.post(
    "",
    summary="Report client-side error",
    description="""
    Report a JavaScript error from the frontend for logging and monitoring.

    No authentication required (errors may occur before/without auth).
    Rate limited to 10 errors per minute per IP to prevent abuse.

    Errors are stored in the audit_log table with:
    - action: "client_error"
    - resource_type: "frontend"
    """,
    response_model=ClientErrorResponse,
    responses={429: RATE_LIMIT_RESPONSE},
)
@limiter.limit("10/minute")
async def report_client_error(
    request: Request,
    error_report: ClientErrorReport,
) -> ClientErrorResponse:
    """Store client error in audit_log."""
    # Get client IP and user agent
    client_ip = get_remote_address(request)
    user_agent = request.headers.get("user-agent", "")[:500]

    # Get correlation ID from header if not in payload
    correlation_id = error_report.correlation_id or request.headers.get("x-request-id")

    # Build details JSON
    details = {
        "error": error_report.error,
        "stack": error_report.stack,
        "url": error_report.url,
        "component": error_report.component,
        "correlation_id": correlation_id,
        **(error_report.context or {}),
    }

    try:
        # Insert into audit_log (user_id is NULL for client errors)
        execute_query(
            """
            INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, ip_address, user_agent)
            VALUES (NULL, 'client_error', 'frontend', %s, %s, %s, %s)
            """,
            (
                error_report.url,  # Use URL as resource_id for grouping
                json.dumps(details),
                client_ip,
                user_agent,
            ),
            fetch="none",
        )

        logger.info(
            "Client error reported",
            extra={
                "client_ip": client_ip,
                "url": error_report.url,
                "error": error_report.error[:100],
                "correlation_id": correlation_id,
            },
        )

        return ClientErrorResponse(success=True, message="Error reported")

    except Exception as e:
        # Don't fail the request if logging fails
        log_error(logger, ErrorCode.SERVICE_EXECUTION_ERROR, f"Failed to store client error: {e}")
        return ClientErrorResponse(success=False, message="Failed to store error")
