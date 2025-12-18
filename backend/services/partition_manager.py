"""Partition management service for time-based table partitions.

Provides:
- create_partition: Create new monthly partition for a table
- drop_old_partitions: Drop partitions older than retention period
- ensure_future_partitions: Pre-create upcoming partitions
- get_partition_stats: Return partition sizes and row counts
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from bo1.constants import PartitionRetention
from bo1.logging import ErrorCode, log_error
from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@dataclass
class PartitionInfo:
    """Information about a table partition."""

    partition_name: str
    table_name: str
    start_date: datetime
    end_date: datetime
    row_count: int
    total_size: str
    table_size: str
    indexes_size: str


@dataclass
class PartitionResult:
    """Result of a partition operation."""

    table: str
    partition_name: str
    status: str  # 'created', 'already_exists', 'dropped', 'error'
    message: str | None = None


PARTITIONED_TABLES = ["api_costs", "session_events", "contributions"]


def create_partition(table: str, start_date: datetime, end_date: datetime) -> PartitionResult:
    """Create a new monthly partition for the specified table.

    Args:
        table: Name of the partitioned table (api_costs, session_events, contributions)
        start_date: Start of partition range (inclusive)
        end_date: End of partition range (exclusive)

    Returns:
        PartitionResult with status and any error message
    """
    if table not in PARTITIONED_TABLES:
        return PartitionResult(
            table=table,
            partition_name="",
            status="error",
            message=f"Table {table} is not a partitioned table",
        )

    partition_name = f"{table}_{start_date.strftime('%Y_%m')}"

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Check if partition already exists
                cur.execute(
                    """
                    SELECT 1 FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = %s AND n.nspname = 'public'
                    """,
                    (partition_name,),
                )
                if cur.fetchone():
                    return PartitionResult(
                        table=table,
                        partition_name=partition_name,
                        status="already_exists",
                    )

                # Create the partition
                cur.execute(
                    f"""
                    CREATE TABLE {partition_name} PARTITION OF {table}
                    FOR VALUES FROM (%s) TO (%s)
                    """,  # noqa: S608
                    (start_date.date(), end_date.date()),
                )

        logger.info(f"Created partition {partition_name} for {table}")
        return PartitionResult(
            table=table,
            partition_name=partition_name,
            status="created",
        )

    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_PARTITION_ERROR,
            f"Failed to create partition {partition_name}: {e}",
        )
        return PartitionResult(
            table=table,
            partition_name=partition_name,
            status="error",
            message=str(e),
        )


def drop_old_partitions(table: str, retention_days: int | None = None) -> list[PartitionResult]:
    """Drop partitions older than the retention period.

    Args:
        table: Name of the partitioned table
        retention_days: Override retention period. If None, uses PartitionRetention defaults.

    Returns:
        List of PartitionResults for each dropped partition
    """
    if table not in PARTITIONED_TABLES:
        return [
            PartitionResult(
                table=table,
                partition_name="",
                status="error",
                message=f"Table {table} is not a partitioned table",
            )
        ]

    if retention_days is None:
        retention_days = PartitionRetention.get_retention_days(table)

    cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
    results: list[PartitionResult] = []

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Get partitions for this table
                cur.execute(
                    """
                    SELECT c.relname AS partition_name
                    FROM pg_class c
                    JOIN pg_inherits i ON i.inhrelid = c.oid
                    JOIN pg_class p ON p.oid = i.inhparent
                    WHERE p.relname = %s
                    ORDER BY c.relname
                    """,
                    (table,),
                )
                partitions = cur.fetchall()

                for row in partitions:
                    partition_name = row["partition_name"]
                    # Extract date from partition name (e.g., api_costs_2024_06)
                    try:
                        parts = partition_name.rsplit("_", 2)
                        if len(parts) >= 3:
                            year = int(parts[-2])
                            month = int(parts[-1])
                            partition_start = datetime(year, month, 1, tzinfo=UTC)

                            # Drop if partition is older than retention period
                            if partition_start < cutoff_date:
                                cur.execute(f"DROP TABLE {partition_name}")  # noqa: S608
                                results.append(
                                    PartitionResult(
                                        table=table,
                                        partition_name=partition_name,
                                        status="dropped",
                                    )
                                )
                                logger.info(
                                    f"Dropped partition {partition_name} (older than {retention_days} days)"
                                )
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Could not parse partition name {partition_name}: {e}")

        return results

    except Exception as e:
        log_error(
            logger, ErrorCode.DB_PARTITION_ERROR, f"Failed to drop old partitions for {table}: {e}"
        )
        return [
            PartitionResult(
                table=table,
                partition_name="",
                status="error",
                message=str(e),
            )
        ]


def ensure_future_partitions(table: str, months_ahead: int = 3) -> list[PartitionResult]:
    """Pre-create partitions for upcoming months.

    Args:
        table: Name of the partitioned table
        months_ahead: Number of months ahead to create partitions for

    Returns:
        List of PartitionResults for each partition operation
    """
    if table not in PARTITIONED_TABLES:
        return [
            PartitionResult(
                table=table,
                partition_name="",
                status="error",
                message=f"Table {table} is not a partitioned table",
            )
        ]

    results: list[PartitionResult] = []
    now = datetime.now(UTC)

    for i in range(months_ahead + 1):
        # Calculate the target month
        year = now.year + (now.month + i - 1) // 12
        month = (now.month + i - 1) % 12 + 1

        start_date = datetime(year, month, 1, tzinfo=UTC)
        # Calculate next month
        next_year = year + (month) // 12
        next_month = (month) % 12 + 1
        end_date = datetime(next_year, next_month, 1, tzinfo=UTC)

        result = create_partition(table, start_date, end_date)
        results.append(result)

    return results


def get_partition_stats(table: str) -> list[PartitionInfo]:
    """Get size and row count statistics for all partitions of a table.

    Args:
        table: Name of the partitioned table

    Returns:
        List of PartitionInfo objects with size/count stats
    """
    if table not in PARTITIONED_TABLES:
        return []

    partitions: list[PartitionInfo] = []

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        c.relname AS partition_name,
                        c.reltuples::BIGINT AS row_count,
                        pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
                        pg_size_pretty(pg_relation_size(c.oid)) AS table_size,
                        pg_size_pretty(
                            pg_total_relation_size(c.oid) - pg_relation_size(c.oid)
                        ) AS indexes_size
                    FROM pg_class c
                    JOIN pg_inherits i ON i.inhrelid = c.oid
                    JOIN pg_class p ON p.oid = i.inhparent
                    WHERE p.relname = %s
                    ORDER BY c.relname
                    """,
                    (table,),
                )

                for row in cur.fetchall():
                    partition_name = row["partition_name"]
                    # Extract date range from partition name
                    try:
                        parts = partition_name.rsplit("_", 2)
                        if len(parts) >= 3:
                            year = int(parts[-2])
                            month = int(parts[-1])
                            start_date = datetime(year, month, 1, tzinfo=UTC)
                            next_year = year + (month) // 12
                            next_month = (month) % 12 + 1
                            end_date = datetime(next_year, next_month, 1, tzinfo=UTC)
                        else:
                            start_date = datetime.now(UTC)
                            end_date = datetime.now(UTC)
                    except (ValueError, IndexError):
                        start_date = datetime.now(UTC)
                        end_date = datetime.now(UTC)

                    partitions.append(
                        PartitionInfo(
                            partition_name=partition_name,
                            table_name=table,
                            start_date=start_date,
                            end_date=end_date,
                            row_count=row["row_count"],
                            total_size=row["total_size"],
                            table_size=row["table_size"],
                            indexes_size=row["indexes_size"],
                        )
                    )

        return partitions

    except Exception as e:
        log_error(
            logger, ErrorCode.DB_QUERY_ERROR, f"Failed to get partition stats for {table}: {e}"
        )
        return []


def get_all_partition_stats() -> dict[str, list[PartitionInfo]]:
    """Get partition stats for all partitioned tables.

    Returns:
        Dict mapping table name to list of PartitionInfo
    """
    return {table: get_partition_stats(table) for table in PARTITIONED_TABLES}


def run_maintenance(
    create_future: bool = True,
    drop_expired: bool = True,
    months_ahead: int = 3,
) -> dict[str, list[PartitionResult]]:
    """Run partition maintenance for all partitioned tables.

    Args:
        create_future: Whether to create future partitions
        drop_expired: Whether to drop expired partitions
        months_ahead: Months ahead to create partitions for

    Returns:
        Dict mapping table name to list of PartitionResults
    """
    results: dict[str, list[PartitionResult]] = {}

    for table in PARTITIONED_TABLES:
        table_results: list[PartitionResult] = []

        if create_future:
            table_results.extend(ensure_future_partitions(table, months_ahead))

        if drop_expired:
            table_results.extend(drop_old_partitions(table))

        results[table] = table_results

    return results
