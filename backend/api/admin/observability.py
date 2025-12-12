"""Admin API endpoints for observability links.

Provides:
- GET /api/admin/observability-links - Get observability tool URLs
"""

from fastapi import APIRouter, Depends

from backend.api.middleware.admin import require_admin_any
from backend.api.models import ErrorResponse
from backend.api.utils.errors import handle_api_errors
from backend.services.observability import ObservabilityLinks, get_observability_links
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["Admin - Observability"])


@router.get(
    "/observability-links",
    summary="Get observability tool links",
    description="""
    Get URLs for external observability tools (Grafana, Prometheus, Sentry).

    Returns configured links for monitoring dashboards. Missing URLs are omitted.
    Useful for admin dashboard quick-access links.
    """,
    responses={
        200: {"description": "Observability links retrieved", "model": ObservabilityLinks},
        403: {"description": "Unauthorized - admin only", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("get observability links")
async def get_observability_links_endpoint(
    _admin: str = Depends(require_admin_any),
) -> ObservabilityLinks:
    """Get observability tool URLs (admin only).

    Returns only configured links; omits missing URLs.
    """
    return get_observability_links()
