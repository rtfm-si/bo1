"""Admin API endpoints for partition management.

Provides:
- GET /api/admin/partitions - List all partitions with sizes
- POST /api/admin/partitions/cleanup - Trigger manual partition cleanup
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.middleware.admin import require_admin_any
from backend.jobs.partition_retention_job import run_retention_job
from backend.services.partition_manager import (
    PARTITIONED_TABLES,
    get_all_partition_stats,
)
from bo1.constants import PartitionRetention

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/partitions", tags=["admin-partitions"])


# =============================================================================
# Models
# =============================================================================


class PartitionInfoResponse(BaseModel):
    """Partition information."""

    partition_name: str
    table_name: str
    start_date: datetime
    end_date: datetime
    row_count: int
    total_size: str
    table_size: str
    indexes_size: str


class TablePartitionsResponse(BaseModel):
    """Partitions for a single table."""

    table_name: str
    retention_days: int
    partitions: list[PartitionInfoResponse]
    total_partitions: int
    total_rows: int


class AllPartitionsResponse(BaseModel):
    """All partitions across all partitioned tables."""

    tables: list[TablePartitionsResponse]
    total_tables: int


class CleanupRequest(BaseModel):
    """Request to trigger manual partition cleanup."""

    months_ahead: int = Field(default=3, ge=1, le=12)
    dry_run: bool = Field(default=False)


class CleanupResultResponse(BaseModel):
    """Result of partition cleanup operation."""

    started_at: str
    completed_at: str
    duration_ms: int
    dry_run: bool
    summary: dict[str, int]
    tables: dict[str, Any]


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "",
    response_model=AllPartitionsResponse,
    dependencies=[Depends(require_admin_any)],
)
async def list_partitions() -> AllPartitionsResponse:
    """List all partitions with sizes and row counts.

    Returns partition information for all partitioned tables:
    - api_costs (90 day retention)
    - session_events (180 day retention)
    - contributions (365 day retention)
    """
    try:
        all_stats = get_all_partition_stats()

        tables = []
        for table_name in PARTITIONED_TABLES:
            partitions = all_stats.get(table_name, [])
            total_rows = sum(p.row_count for p in partitions)

            tables.append(
                TablePartitionsResponse(
                    table_name=table_name,
                    retention_days=PartitionRetention.get_retention_days(table_name),
                    partitions=[
                        PartitionInfoResponse(
                            partition_name=p.partition_name,
                            table_name=p.table_name,
                            start_date=p.start_date,
                            end_date=p.end_date,
                            row_count=p.row_count,
                            total_size=p.total_size,
                            table_size=p.table_size,
                            indexes_size=p.indexes_size,
                        )
                        for p in partitions
                    ],
                    total_partitions=len(partitions),
                    total_rows=total_rows,
                )
            )

        return AllPartitionsResponse(
            tables=tables,
            total_tables=len(tables),
        )

    except Exception as e:
        logger.error(f"Failed to list partitions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve partition information"
        ) from None


@router.post(
    "/cleanup",
    response_model=CleanupResultResponse,
    dependencies=[Depends(require_admin_any)],
)
async def trigger_cleanup(request: CleanupRequest) -> CleanupResultResponse:
    """Trigger manual partition cleanup.

    Creates future partitions and drops expired ones based on
    per-table retention periods:
    - api_costs: 90 days
    - session_events: 180 days
    - contributions: 365 days

    Use dry_run=true to preview changes without making them.
    """
    try:
        result = run_retention_job(
            months_ahead=request.months_ahead,
            dry_run=request.dry_run,
        )

        return CleanupResultResponse(
            started_at=result["started_at"],
            completed_at=result["completed_at"],
            duration_ms=result["duration_ms"],
            dry_run=result["dry_run"],
            summary=result["summary"],
            tables=result["tables"],
        )

    except Exception as e:
        logger.error(f"Failed to run partition cleanup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to run partition cleanup") from None
