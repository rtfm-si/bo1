"""CSP violation report endpoint.

Receives Content-Security-Policy violation reports from browsers when
CSP directives are violated. Used for monitoring and debugging CSP issues.
"""

import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["security"])


class CspViolationReport(BaseModel):
    """CSP violation report as sent by browsers."""

    model_config = ConfigDict(extra="allow")

    document_uri: str | None = None
    referrer: str | None = None
    violated_directive: str | None = None
    effective_directive: str | None = None
    original_policy: str | None = None
    disposition: str | None = None
    blocked_uri: str | None = None
    line_number: int | None = None
    column_number: int | None = None
    source_file: str | None = None
    status_code: int | None = None
    script_sample: str | None = None


class CspReportWrapper(BaseModel):
    """Wrapper for CSP report (browsers send as csp-report object)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    csp_report: CspViolationReport | None = None


@router.post("/csp-report")
async def receive_csp_report(request: Request) -> dict[str, str]:
    """Receive CSP violation reports from browsers.

    Browsers send POST requests to this endpoint when CSP violations occur.
    The report format follows the CSP specification.

    Args:
        request: The incoming request containing the CSP report

    Returns:
        Acknowledgment response
    """
    try:
        body: dict[str, Any] = await request.json()

        # Extract the nested csp-report object (browser format uses kebab-case)
        report_data = body.get("csp-report", body)

        # Log the violation for monitoring
        logger.warning(
            "CSP violation",
            extra={
                "csp_violated_directive": report_data.get("violated-directive"),
                "csp_blocked_uri": report_data.get("blocked-uri"),
                "csp_document_uri": report_data.get("document-uri"),
                "csp_source_file": report_data.get("source-file"),
                "csp_line_number": report_data.get("line-number"),
            },
        )

    except Exception:
        # Don't fail on malformed reports
        logger.debug("Failed to parse CSP report", exc_info=True)

    return {"status": "received"}
