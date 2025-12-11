"""Dataset repository for data management operations.

Handles:
- Dataset CRUD operations
- Dataset profile management
- File metadata tracking
"""

import logging
from typing import Any
from uuid import UUID

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class DatasetRepository(BaseRepository):
    """Repository for dataset management operations."""

    # =========================================================================
    # Dataset CRUD
    # =========================================================================

    def create(
        self,
        user_id: str,
        name: str,
        source_type: str = "csv",
        description: str | None = None,
        source_uri: str | None = None,
        file_key: str | None = None,
        row_count: int | None = None,
        column_count: int | None = None,
        file_size_bytes: int | None = None,
    ) -> dict[str, Any]:
        """Create a new dataset.

        Args:
            user_id: User who owns the dataset
            name: Dataset name
            source_type: Source type (csv, sheets, api)
            description: Optional description
            source_uri: Original source location
            file_key: Spaces object key
            row_count: Number of rows
            column_count: Number of columns
            file_size_bytes: File size in bytes

        Returns:
            Created dataset record
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO datasets (
                        user_id, name, description, source_type,
                        source_uri, file_key, row_count, column_count, file_size_bytes
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, name, description, source_type,
                              source_uri, file_key, row_count, column_count,
                              file_size_bytes, created_at, updated_at
                    """,
                    (
                        user_id,
                        name,
                        description,
                        source_type,
                        source_uri,
                        file_key,
                        row_count,
                        column_count,
                        file_size_bytes,
                    ),
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return {
                "id": str(row["id"]),
                "user_id": row["user_id"],
                "name": row["name"],
                "description": row["description"],
                "source_type": row["source_type"],
                "source_uri": row["source_uri"],
                "file_key": row["file_key"],
                "row_count": row["row_count"],
                "column_count": row["column_count"],
                "file_size_bytes": row["file_size_bytes"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
        return {}

    def get_by_id(self, dataset_id: str | UUID, user_id: str) -> dict[str, Any] | None:
        """Get dataset by ID.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)

        Returns:
            Dataset record or None if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, name, description, source_type,
                           source_uri, file_key, row_count, column_count,
                           file_size_bytes, created_at, updated_at, summary
                    FROM datasets
                    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                    """,
                    (str(dataset_id), user_id),
                )
                row = cur.fetchone()

        if row:
            return {
                "id": str(row["id"]),
                "user_id": row["user_id"],
                "name": row["name"],
                "description": row["description"],
                "source_type": row["source_type"],
                "source_uri": row["source_uri"],
                "file_key": row["file_key"],
                "row_count": row["row_count"],
                "column_count": row["column_count"],
                "file_size_bytes": row["file_size_bytes"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                "summary": row["summary"],
            }
        return None

    def list_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """List datasets for a user.

        Args:
            user_id: User ID
            limit: Max results
            offset: Pagination offset

        Returns:
            Tuple of (datasets list, total count)
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Get total count
                cur.execute(
                    """
                    SELECT COUNT(*) FROM datasets
                    WHERE user_id = %s AND deleted_at IS NULL
                    """,
                    (user_id,),
                )
                total = cur.fetchone()["count"]

                # Get datasets
                cur.execute(
                    """
                    SELECT id, user_id, name, description, source_type,
                           source_uri, file_key, row_count, column_count,
                           file_size_bytes, created_at, updated_at
                    FROM datasets
                    WHERE user_id = %s AND deleted_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, limit, offset),
                )
                rows = cur.fetchall()

        datasets = [
            {
                "id": str(row["id"]),
                "user_id": row["user_id"],
                "name": row["name"],
                "description": row["description"],
                "source_type": row["source_type"],
                "source_uri": row["source_uri"],
                "file_key": row["file_key"],
                "row_count": row["row_count"],
                "column_count": row["column_count"],
                "file_size_bytes": row["file_size_bytes"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
            for row in rows
        ]
        return datasets, total

    def delete(self, dataset_id: str | UUID, user_id: str) -> bool:
        """Soft delete a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)

        Returns:
            True if deleted, False if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE datasets
                    SET deleted_at = now()
                    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                    RETURNING id
                    """,
                    (str(dataset_id), user_id),
                )
                result = cur.fetchone()
                conn.commit()

        return result is not None

    def update_metadata(
        self,
        dataset_id: str | UUID,
        user_id: str,
        row_count: int | None = None,
        column_count: int | None = None,
        file_size_bytes: int | None = None,
    ) -> dict[str, Any] | None:
        """Update dataset metadata after processing.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)
            row_count: Number of rows
            column_count: Number of columns
            file_size_bytes: File size

        Returns:
            Updated dataset or None
        """
        updates: list[str] = []
        values: list[int | str] = []
        if row_count is not None:
            updates.append("row_count = %s")
            values.append(row_count)
        if column_count is not None:
            updates.append("column_count = %s")
            values.append(column_count)
        if file_size_bytes is not None:
            updates.append("file_size_bytes = %s")
            values.append(file_size_bytes)

        if not updates:
            return self.get_by_id(dataset_id, user_id)

        values.extend([str(dataset_id), str(user_id)])

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE datasets
                    SET {", ".join(updates)}
                    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                    RETURNING id, user_id, name, description, source_type,
                              source_uri, file_key, row_count, column_count,
                              file_size_bytes, created_at, updated_at
                    """,
                    values,
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return {
                "id": str(row["id"]),
                "user_id": row["user_id"],
                "name": row["name"],
                "description": row["description"],
                "source_type": row["source_type"],
                "source_uri": row["source_uri"],
                "file_key": row["file_key"],
                "row_count": row["row_count"],
                "column_count": row["column_count"],
                "file_size_bytes": row["file_size_bytes"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
        return None

    def update_summary(
        self,
        dataset_id: str | UUID,
        user_id: str,
        summary: str,
    ) -> bool:
        """Update dataset summary.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)
            summary: Generated summary text

        Returns:
            True if updated, False if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE datasets
                    SET summary = %s
                    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                    RETURNING id
                    """,
                    (summary, str(dataset_id), user_id),
                )
                result = cur.fetchone()
                conn.commit()

        return result is not None

    # =========================================================================
    # Dataset Profiles
    # =========================================================================

    def create_profile(
        self,
        dataset_id: str | UUID,
        column_name: str,
        data_type: str,
        null_count: int | None = None,
        unique_count: int | None = None,
        min_value: str | None = None,
        max_value: str | None = None,
        mean_value: float | None = None,
        sample_values: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Create a column profile for a dataset.

        Args:
            dataset_id: Dataset UUID
            column_name: Column name
            data_type: Inferred data type
            null_count: Count of null values
            unique_count: Count of unique values
            min_value: Minimum value (as string)
            max_value: Maximum value (as string)
            mean_value: Mean value (for numeric columns)
            sample_values: Sample values list

        Returns:
            Created profile record
        """
        import json

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO dataset_profiles (
                        dataset_id, column_name, data_type,
                        null_count, unique_count, min_value, max_value,
                        mean_value, sample_values
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, dataset_id, column_name, data_type,
                              null_count, unique_count, min_value, max_value,
                              mean_value, sample_values, created_at
                    """,
                    (
                        str(dataset_id),
                        column_name,
                        data_type,
                        null_count,
                        unique_count,
                        min_value,
                        max_value,
                        mean_value,
                        json.dumps(sample_values) if sample_values else None,
                    ),
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return {
                "id": str(row["id"]),
                "dataset_id": str(row["dataset_id"]),
                "column_name": row["column_name"],
                "data_type": row["data_type"],
                "null_count": row["null_count"],
                "unique_count": row["unique_count"],
                "min_value": row["min_value"],
                "max_value": row["max_value"],
                "mean_value": row["mean_value"],
                "sample_values": row["sample_values"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
        return {}

    def get_profiles(self, dataset_id: str | UUID) -> list[dict[str, Any]]:
        """Get all column profiles for a dataset.

        Args:
            dataset_id: Dataset UUID

        Returns:
            List of profile records
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, dataset_id, column_name, data_type,
                           null_count, unique_count, min_value, max_value,
                           mean_value, sample_values, created_at
                    FROM dataset_profiles
                    WHERE dataset_id = %s
                    ORDER BY created_at ASC
                    """,
                    (str(dataset_id),),
                )
                rows = cur.fetchall()

        return [
            {
                "id": str(row["id"]),
                "dataset_id": str(row["dataset_id"]),
                "column_name": row["column_name"],
                "data_type": row["data_type"],
                "null_count": row["null_count"],
                "unique_count": row["unique_count"],
                "min_value": row["min_value"],
                "max_value": row["max_value"],
                "mean_value": row["mean_value"],
                "sample_values": row["sample_values"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]

    def delete_profiles(self, dataset_id: str | UUID) -> int:
        """Delete all profiles for a dataset.

        Args:
            dataset_id: Dataset UUID

        Returns:
            Number of profiles deleted
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM dataset_profiles
                    WHERE dataset_id = %s
                    """,
                    (str(dataset_id),),
                )
                count = cur.rowcount
                conn.commit()

        return int(count) if count else 0

    # =========================================================================
    # Dataset Analyses
    # =========================================================================

    def create_analysis(
        self,
        dataset_id: str | UUID,
        user_id: str,
        query_spec: dict[str, Any] | None = None,
        chart_spec: dict[str, Any] | None = None,
        query_result_preview: dict[str, Any] | None = None,
        chart_key: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Create a dataset analysis record.

        Args:
            dataset_id: Dataset UUID
            user_id: User who created the analysis
            query_spec: Query specification (JSONB)
            chart_spec: Chart specification (JSONB)
            query_result_preview: Preview of query results (first 10 rows)
            chart_key: Spaces object key for chart PNG
            title: Display title for gallery

        Returns:
            Created analysis record
        """
        import json

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO dataset_analyses (
                        dataset_id, user_id, query_spec, chart_spec,
                        query_result_preview, chart_key, title
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, dataset_id, user_id, query_spec, chart_spec,
                              query_result_preview, chart_key, title, created_at
                    """,
                    (
                        str(dataset_id),
                        user_id,
                        json.dumps(query_spec) if query_spec else None,
                        json.dumps(chart_spec) if chart_spec else None,
                        json.dumps(query_result_preview) if query_result_preview else None,
                        chart_key,
                        title,
                    ),
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return {
                "id": str(row["id"]),
                "dataset_id": str(row["dataset_id"]),
                "user_id": row["user_id"],
                "query_spec": row["query_spec"],
                "chart_spec": row["chart_spec"],
                "query_result_preview": row["query_result_preview"],
                "chart_key": row["chart_key"],
                "title": row["title"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
        return {}

    def list_analyses(
        self,
        dataset_id: str | UUID,
        user_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List recent analyses for a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)
            limit: Max results

        Returns:
            List of analysis records (newest first)
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT a.id, a.dataset_id, a.user_id, a.query_spec, a.chart_spec,
                           a.query_result_preview, a.chart_key, a.title, a.created_at
                    FROM dataset_analyses a
                    JOIN datasets d ON d.id = a.dataset_id
                    WHERE a.dataset_id = %s AND d.user_id = %s AND d.deleted_at IS NULL
                    ORDER BY a.created_at DESC
                    LIMIT %s
                    """,
                    (str(dataset_id), user_id, limit),
                )
                rows = cur.fetchall()

        return [
            {
                "id": str(row["id"]),
                "dataset_id": str(row["dataset_id"]),
                "user_id": row["user_id"],
                "query_spec": row["query_spec"],
                "chart_spec": row["chart_spec"],
                "query_result_preview": row["query_result_preview"],
                "chart_key": row["chart_key"],
                "title": row["title"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]

    # =========================================================================
    # Dataset Clarifications
    # =========================================================================

    def get_clarifications(
        self,
        dataset_id: str | UUID,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """Get clarifications for a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)

        Returns:
            List of clarification dicts {question, answer, timestamp}
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT clarifications
                    FROM datasets
                    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                    """,
                    (str(dataset_id), user_id),
                )
                row = cur.fetchone()

        if row and row["clarifications"]:
            result: list[dict[str, Any]] = row["clarifications"]
            return result
        return []

    def add_clarification(
        self,
        dataset_id: str | UUID,
        user_id: str,
        question: str,
        answer: str,
    ) -> bool:
        """Add a clarification Q&A pair to a dataset.

        Appends to the existing clarifications array. Deduplicates by question.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)
            question: The clarification question
            answer: The user's answer

        Returns:
            True if added successfully
        """
        import json
        from datetime import UTC, datetime

        clarification = {
            "question": question,
            "answer": answer,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        with db_session() as conn:
            with conn.cursor() as cur:
                # Use jsonb_agg to append, with deduplication by question
                cur.execute(
                    """
                    UPDATE datasets
                    SET clarifications = (
                        SELECT COALESCE(
                            jsonb_agg(c),
                            '[]'::jsonb
                        ) || %s::jsonb
                        FROM (
                            SELECT c
                            FROM jsonb_array_elements(
                                COALESCE(clarifications, '[]'::jsonb)
                            ) AS c
                            WHERE c->>'question' != %s
                        ) subq
                    )
                    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                    RETURNING id
                    """,
                    (json.dumps(clarification), question, str(dataset_id), user_id),
                )
                result = cur.fetchone()
                conn.commit()

        return result is not None
