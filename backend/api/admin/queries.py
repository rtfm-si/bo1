"""Admin API endpoints for database query performance analysis.

Provides:
- GET /api/admin/queries/slow - Get slowest queries from pg_stat_statements

Requires pg_stat_statements extension to be enabled in PostgreSQL.
See migration z16_enable_pg_stat_statements.py for setup.
"""

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import ErrorResponse
from backend.api.utils.db_helpers import execute_query
from backend.api.utils.errors import handle_api_errors
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/queries", tags=["Admin - Query Performance"])


class SlowQueryResponse(BaseModel):
    """Single slow query entry from pg_stat_statements."""

    query: str = Field(description="SQL query text (may be truncated)")
    calls: int = Field(description="Number of times the query was executed")
    mean_time_ms: float = Field(description="Mean execution time in milliseconds")
    total_time_ms: float = Field(description="Total execution time in milliseconds")
    rows: int = Field(description="Total number of rows retrieved or affected")
    shared_blks_hit: int = Field(description="Shared blocks hit in buffer cache")
    shared_blks_read: int = Field(description="Shared blocks read from disk")


class SlowQueryListResponse(BaseModel):
    """Response containing list of slow queries."""

    queries: list[SlowQueryResponse] = Field(description="List of slow queries")
    extension_available: bool = Field(
        description="Whether pg_stat_statements extension is available"
    )
    message: str | None = Field(
        default=None,
        description="Status message (e.g., extension not configured)",
    )


def _check_extension_available() -> bool:
    """Check if pg_stat_statements extension is available."""
    try:
        result = execute_query(
            """
            SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
            """,
            fetch="one",
        )
        return result is not None
    except Exception:
        return False


@router.get(
    "/slow",
    summary="Get slowest queries",
    description="""
    Get the top N slowest queries from pg_stat_statements ordered by mean execution time.

    Returns:
    - Query text (may be truncated for long queries)
    - Call count
    - Mean and total execution time
    - Row count
    - Buffer cache hit/read statistics

    Note: Requires pg_stat_statements extension to be enabled.
    If not available, returns empty list with extension_available=false.
    """,
    responses={
        200: {"description": "Slow queries retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get slow queries")
async def get_slow_queries(
    request: Request,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of queries to return",
    ),
    min_calls: int = Query(
        default=1,
        ge=1,
        description="Minimum number of calls to include query",
    ),
    _admin: str = Depends(require_admin_any),
) -> SlowQueryListResponse:
    """Get slowest queries from pg_stat_statements (admin only)."""
    # Check if extension is available
    if not _check_extension_available():
        logger.warning("pg_stat_statements extension not available")
        return SlowQueryListResponse(
            queries=[],
            extension_available=False,
            message=(
                "pg_stat_statements extension not installed. "
                "Run migration z16_enable_pg_stat_statements and restart PostgreSQL "
                "with shared_preload_libraries=pg_stat_statements."
            ),
        )

    # Query pg_stat_statements for slowest queries
    try:
        rows = execute_query(
            """
            SELECT
                query,
                calls,
                mean_exec_time as mean_time_ms,
                total_exec_time as total_time_ms,
                rows,
                shared_blks_hit,
                shared_blks_read
            FROM pg_stat_statements
            WHERE calls >= %s
            ORDER BY mean_exec_time DESC
            LIMIT %s
            """,
            (min_calls, limit),
            fetch="all",
        )

        queries = [
            SlowQueryResponse(
                query=row["query"],
                calls=row["calls"],
                mean_time_ms=round(row["mean_time_ms"], 3),
                total_time_ms=round(row["total_time_ms"], 3),
                rows=row["rows"],
                shared_blks_hit=row["shared_blks_hit"],
                shared_blks_read=row["shared_blks_read"],
            )
            for row in rows
        ]

        logger.info(f"Admin: Retrieved {len(queries)} slow queries")
        return SlowQueryListResponse(
            queries=queries,
            extension_available=True,
        )

    except Exception as e:
        # Handle case where extension exists but stats not yet populated
        error_msg = str(e)
        if "pg_stat_statements" in error_msg:
            logger.warning(f"pg_stat_statements query failed: {error_msg}")
            return SlowQueryListResponse(
                queries=[],
                extension_available=True,
                message=(
                    "pg_stat_statements is installed but may not be fully configured. "
                    "Ensure shared_preload_libraries includes pg_stat_statements and restart PostgreSQL."
                ),
            )
        raise


@router.post(
    "/slow/reset",
    summary="Reset query statistics",
    description="""
    Reset all query statistics in pg_stat_statements.

    Use this after deploying optimizations to start fresh measurements.
    Requires superuser or pg_stat_statements_reset privilege.
    """,
    responses={
        200: {"description": "Statistics reset successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("reset query stats")
async def reset_query_stats(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> dict[str, str]:
    """Reset pg_stat_statements statistics (admin only)."""
    if not _check_extension_available():
        return {
            "status": "skipped",
            "message": "pg_stat_statements extension not available",
        }

    try:
        execute_query("SELECT pg_stat_statements_reset()", fetch="none")
        logger.info("Admin: Reset pg_stat_statements")
        return {
            "status": "success",
            "message": "Query statistics reset successfully",
        }
    except Exception as e:
        error_msg = str(e)
        if "permission denied" in error_msg.lower():
            return {
                "status": "error",
                "message": "Permission denied. Requires superuser or pg_stat_statements_reset privilege.",
            }
        raise
