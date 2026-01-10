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
        storage_path: str | None = None,
        row_count: int | None = None,
        column_count: int | None = None,
        file_size_bytes: int | None = None,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new dataset.

        Args:
            user_id: User who owns the dataset
            name: Dataset name
            source_type: Source type (csv, sheets, api)
            description: Optional description
            source_uri: Original source location
            file_key: Spaces object key
            storage_path: Storage prefix path (e.g., datasets/user_id)
            row_count: Number of rows
            column_count: Number of columns
            file_size_bytes: File size in bytes
            workspace_id: Optional workspace UUID to scope dataset to a team

        Returns:
            Created dataset record
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO datasets (
                        user_id, name, description, source_type,
                        source_uri, file_key, storage_path, row_count, column_count, file_size_bytes, workspace_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, name, description, source_type,
                              source_uri, file_key, storage_path, row_count, column_count,
                              file_size_bytes, workspace_id, created_at, updated_at
                    """,
                    (
                        user_id,
                        name,
                        description,
                        source_type,
                        source_uri,
                        file_key,
                        storage_path,
                        row_count,
                        column_count,
                        file_size_bytes,
                        workspace_id,
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
                "storage_path": row["storage_path"],
                "row_count": row["row_count"],
                "column_count": row["column_count"],
                "file_size_bytes": row["file_size_bytes"],
                "workspace_id": str(row["workspace_id"]) if row["workspace_id"] else None,
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
                           source_uri, file_key, storage_path, row_count, column_count,
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
                "storage_path": row["storage_path"],
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
        workspace_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List datasets for a user.

        Args:
            user_id: User ID
            limit: Max results
            offset: Pagination offset
            workspace_id: Filter by workspace UUID (optional)

        Returns:
            Tuple of (datasets list, total count)
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Build WHERE clause
                where_parts = ["user_id = %s", "deleted_at IS NULL"]
                params: list[Any] = [user_id]

                if workspace_id:
                    where_parts.append("workspace_id = %s")
                    params.append(workspace_id)

                where_clause = " AND ".join(where_parts)

                # Get total count
                cur.execute(
                    f"""
                    SELECT COUNT(*) FROM datasets
                    WHERE {where_clause}
                    """,
                    params,
                )
                total = cur.fetchone()["count"]

                # Get datasets
                cur.execute(
                    f"""
                    SELECT id, user_id, name, description, source_type,
                           source_uri, file_key, storage_path, row_count, column_count,
                           file_size_bytes, workspace_id, created_at, updated_at
                    FROM datasets
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
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
                "storage_path": row["storage_path"],
                "row_count": row["row_count"],
                "column_count": row["column_count"],
                "file_size_bytes": row["file_size_bytes"],
                "workspace_id": str(row["workspace_id"]) if row["workspace_id"] else None,
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

    def update_dataset(
        self,
        dataset_id: str | UUID,
        user_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any] | None:
        """Update dataset name and/or description.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)
            name: New name (optional)
            description: New description (optional)

        Returns:
            Updated dataset or None if not found
        """
        updates: list[str] = []
        values: list[str] = []
        if name is not None:
            updates.append("name = %s")
            values.append(name)
        if description is not None:
            updates.append("description = %s")
            values.append(description)

        if not updates:
            return self.get_by_id(dataset_id, user_id)

        updates.append("updated_at = NOW()")
        values.extend([str(dataset_id), str(user_id)])

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE datasets
                    SET {", ".join(updates)}
                    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                    RETURNING id, user_id, name, description, source_type, source_uri,
                              file_key, row_count, column_count, file_size_bytes,
                              created_at, updated_at
                    """,
                    values,
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return {
                "id": str(row["id"]),
                "user_id": str(row["user_id"]),
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

    def update_row_count(
        self,
        dataset_id: str | UUID,
        user_id: str,
        row_count: int,
    ) -> bool:
        """Update dataset row count after data cleaning operations.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)
            row_count: New row count

        Returns:
            True if updated, False if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE datasets
                    SET row_count = %s, updated_at = NOW()
                    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                    """,
                    (row_count, str(dataset_id), str(user_id)),
                )
                affected: int = cur.rowcount or 0
                conn.commit()
        return affected > 0

    def acknowledge_pii(
        self,
        dataset_id: str | UUID,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Acknowledge PII warning for a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)

        Returns:
            Updated dataset or None if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE datasets
                    SET pii_acknowledged_at = NOW(), updated_at = NOW()
                    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                    RETURNING id, user_id, name, description, source_type, source_uri,
                              file_key, storage_path, row_count, column_count, file_size_bytes,
                              pii_acknowledged_at, created_at, updated_at
                    """,
                    (str(dataset_id), str(user_id)),
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return {
                "id": str(row["id"]),
                "user_id": str(row["user_id"]),
                "name": row["name"],
                "description": row["description"],
                "source_type": row["source_type"],
                "source_uri": row["source_uri"],
                "file_key": row["file_key"],
                "storage_path": row["storage_path"],
                "row_count": row["row_count"],
                "column_count": row["column_count"],
                "file_size_bytes": row["file_size_bytes"],
                "pii_acknowledged_at": (
                    row["pii_acknowledged_at"].isoformat() if row["pii_acknowledged_at"] else None
                ),
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

    def update_column_description(
        self,
        dataset_id: str | UUID,
        user_id: str,
        column_name: str,
        description: str,
    ) -> bool:
        """Update user-editable description for a specific column.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)
            column_name: Column to update
            description: User's description text

        Returns:
            True if updated, False if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Use jsonb_set to merge into existing descriptions
                cur.execute(
                    """
                    UPDATE datasets
                    SET column_descriptions = COALESCE(column_descriptions, '{}'::jsonb)
                        || jsonb_build_object(%s, %s)
                    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                    RETURNING id
                    """,
                    (column_name, description, str(dataset_id), user_id),
                )
                result = cur.fetchone()
                conn.commit()

        return result is not None

    def get_column_descriptions(
        self,
        dataset_id: str | UUID,
        user_id: str,
    ) -> dict[str, str]:
        """Get all user-defined column descriptions for a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)

        Returns:
            Dict mapping column_name to description
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_descriptions
                    FROM datasets
                    WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                    """,
                    (str(dataset_id), user_id),
                )
                row = cur.fetchone()

        if row and row["column_descriptions"]:
            return dict(row["column_descriptions"])
        return {}

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

    # =========================================================================
    # Dataset Favourites
    # =========================================================================

    def create_favourite(
        self,
        user_id: str,
        dataset_id: str,
        favourite_type: str,
        analysis_id: str | None = None,
        message_id: str | None = None,
        insight_data: dict[str, Any] | None = None,
        title: str | None = None,
        content: str | None = None,
        chart_spec: dict[str, Any] | None = None,
        figure_json: dict[str, Any] | None = None,
        user_note: str | None = None,
    ) -> dict[str, Any]:
        """Create a favourite for a dataset item."""
        import json

        with db_session() as conn:
            with conn.cursor() as cur:
                # Get next sort order
                cur.execute(
                    """
                    SELECT COALESCE(MAX(sort_order), -1) + 1 as next_order
                    FROM dataset_favourites
                    WHERE user_id = %s AND dataset_id = %s
                    """,
                    (user_id, dataset_id),
                )
                next_order = cur.fetchone()["next_order"]

                cur.execute(
                    """
                    INSERT INTO dataset_favourites (
                        user_id, dataset_id, favourite_type,
                        analysis_id, message_id, insight_data,
                        title, content, chart_spec, figure_json,
                        user_note, sort_order
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING id, user_id, dataset_id, favourite_type,
                              analysis_id, message_id, insight_data,
                              title, content, chart_spec, figure_json,
                              user_note, sort_order, created_at
                    """,
                    (
                        user_id,
                        dataset_id,
                        favourite_type,
                        analysis_id,
                        message_id,
                        json.dumps(insight_data) if insight_data else None,
                        title,
                        content,
                        json.dumps(chart_spec) if chart_spec else None,
                        json.dumps(figure_json) if figure_json else None,
                        user_note,
                        next_order,
                    ),
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return self._row_to_favourite(row)
        return {}

    def _row_to_favourite(self, row: Any) -> dict[str, Any]:
        """Convert database row to favourite dict."""
        return {
            "id": str(row["id"]),
            "dataset_id": str(row["dataset_id"]),
            "favourite_type": row["favourite_type"],
            "analysis_id": str(row["analysis_id"]) if row["analysis_id"] else None,
            "message_id": str(row["message_id"]) if row["message_id"] else None,
            "insight_data": row["insight_data"],
            "title": row["title"],
            "content": row["content"],
            "chart_spec": row["chart_spec"],
            "figure_json": row["figure_json"],
            "user_note": row["user_note"],
            "sort_order": row["sort_order"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }

    def get_favourite(self, favourite_id: str, user_id: str) -> dict[str, Any] | None:
        """Get a favourite by ID."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, dataset_id, favourite_type,
                           analysis_id, message_id, insight_data,
                           title, content, chart_spec, figure_json,
                           user_note, sort_order, created_at
                    FROM dataset_favourites
                    WHERE id = %s AND user_id = %s
                    """,
                    (favourite_id, user_id),
                )
                row = cur.fetchone()

        if row:
            return self._row_to_favourite(row)
        return None

    def list_favourites(self, dataset_id: str, user_id: str) -> list[dict[str, Any]]:
        """List favourites for a dataset, ordered by sort_order."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, dataset_id, favourite_type,
                           analysis_id, message_id, insight_data,
                           title, content, chart_spec, figure_json,
                           user_note, sort_order, created_at
                    FROM dataset_favourites
                    WHERE dataset_id = %s AND user_id = %s
                    ORDER BY sort_order ASC
                    """,
                    (dataset_id, user_id),
                )
                rows = cur.fetchall()

        return [self._row_to_favourite(row) for row in rows]

    def update_favourite(
        self,
        favourite_id: str,
        user_id: str,
        user_note: str | None = None,
        sort_order: int | None = None,
    ) -> dict[str, Any] | None:
        """Update a favourite."""
        updates: list[str] = []
        values: list[Any] = []

        if user_note is not None:
            updates.append("user_note = %s")
            values.append(user_note)
        if sort_order is not None:
            updates.append("sort_order = %s")
            values.append(sort_order)

        if not updates:
            return self.get_favourite(favourite_id, user_id)

        values.extend([favourite_id, user_id])

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE dataset_favourites
                    SET {", ".join(updates)}
                    WHERE id = %s AND user_id = %s
                    RETURNING id, user_id, dataset_id, favourite_type,
                              analysis_id, message_id, insight_data,
                              title, content, chart_spec, figure_json,
                              user_note, sort_order, created_at
                    """,
                    values,
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return self._row_to_favourite(row)
        return None

    def delete_favourite(self, favourite_id: str, user_id: str) -> bool:
        """Delete a favourite."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM dataset_favourites
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                    """,
                    (favourite_id, user_id),
                )
                result = cur.fetchone()
                conn.commit()

        return result is not None

    def get_favourites_by_ids(self, favourite_ids: list[str], user_id: str) -> list[dict[str, Any]]:
        """Get multiple favourites by IDs."""
        if not favourite_ids:
            return []

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, dataset_id, favourite_type,
                           analysis_id, message_id, insight_data,
                           title, content, chart_spec, figure_json,
                           user_note, sort_order, created_at
                    FROM dataset_favourites
                    WHERE id = ANY(%s) AND user_id = %s
                    ORDER BY sort_order ASC
                    """,
                    (favourite_ids, user_id),
                )
                rows = cur.fetchall()

        return [self._row_to_favourite(row) for row in rows]

    # =========================================================================
    # Dataset Reports
    # =========================================================================

    def create_report(
        self,
        user_id: str,
        dataset_id: str,
        title: str,
        report_content: dict[str, Any],
        favourite_ids: list[str],
        executive_summary: str | None = None,
        model_used: str | None = None,
        tokens_used: int | None = None,
    ) -> dict[str, Any]:
        """Create a dataset report."""
        import json

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO dataset_reports (
                        user_id, dataset_id, title, executive_summary,
                        report_content, favourite_ids, model_used, tokens_used
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, dataset_id, title, executive_summary,
                              report_content, favourite_ids, model_used, tokens_used,
                              created_at, updated_at
                    """,
                    (
                        user_id,
                        dataset_id,
                        title,
                        executive_summary,
                        json.dumps(report_content),
                        favourite_ids,
                        model_used,
                        tokens_used,
                    ),
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return self._row_to_report(row)
        return {}

    def _row_to_report(self, row: Any) -> dict[str, Any]:
        """Convert database row to report dict."""
        return {
            "id": str(row["id"]),
            "dataset_id": str(row["dataset_id"]) if row["dataset_id"] else None,
            "title": row["title"],
            "executive_summary": row["executive_summary"],
            "report_content": row["report_content"],
            "favourite_ids": [str(fid) for fid in row["favourite_ids"]]
            if row["favourite_ids"]
            else [],
            "model_used": row["model_used"],
            "tokens_used": row["tokens_used"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }

    def get_report(self, report_id: str, user_id: str) -> dict[str, Any] | None:
        """Get a report by ID."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, dataset_id, title, executive_summary,
                           report_content, favourite_ids, model_used, tokens_used,
                           created_at, updated_at
                    FROM dataset_reports
                    WHERE id = %s AND user_id = %s
                    """,
                    (report_id, user_id),
                )
                row = cur.fetchone()

        if row:
            return self._row_to_report(row)
        return None

    def list_reports(self, dataset_id: str, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """List reports for a dataset."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, dataset_id, title, executive_summary,
                           report_content, favourite_ids, model_used, tokens_used,
                           created_at, updated_at
                    FROM dataset_reports
                    WHERE dataset_id = %s AND user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (dataset_id, user_id, limit),
                )
                rows = cur.fetchall()

        return [self._row_to_report(row) for row in rows]

    def delete_report(self, report_id: str, user_id: str) -> bool:
        """Delete a report."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM dataset_reports
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                    """,
                    (report_id, user_id),
                )
                result = cur.fetchone()
                conn.commit()

        return result is not None

    def update_report_summary(self, report_id: str, user_id: str, summary: str) -> bool:
        """Update the executive summary for a report.

        Args:
            report_id: Report UUID
            user_id: User ID
            summary: New executive summary text

        Returns:
            True if updated, False if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE dataset_reports
                    SET executive_summary = %s, updated_at = NOW()
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                    """,
                    (summary, report_id, user_id),
                )
                result = cur.fetchone()
                conn.commit()

        return result is not None

    def list_all_reports(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """List all reports for a user across all datasets.

        Includes orphaned reports (where dataset was deleted).

        Args:
            user_id: User ID
            limit: Max results

        Returns:
            List of reports with dataset name attached (or None if deleted), newest first
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT r.id, r.user_id, r.dataset_id, r.title, r.executive_summary,
                           r.report_content, r.favourite_ids, r.model_used, r.tokens_used,
                           r.created_at, r.updated_at,
                           d.name as dataset_name
                    FROM dataset_reports r
                    LEFT JOIN datasets d ON d.id = r.dataset_id AND d.deleted_at IS NULL
                    WHERE r.user_id = %s
                    ORDER BY r.created_at DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
                rows = cur.fetchall()

        return [self._row_to_report_with_dataset(row) for row in rows]

    def _row_to_report_with_dataset(self, row: Any) -> dict[str, Any]:
        """Convert database row to report dict with dataset name."""
        result = self._row_to_report(row)
        if "dataset_name" in row.keys():
            result["dataset_name"] = row["dataset_name"]
        return result

    # =========================================================================
    # Dataset Investigations (8 Deterministic Analyses)
    # =========================================================================

    def save_investigation(
        self,
        dataset_id: str,
        user_id: str,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """Save or update investigation results for a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID
            investigation: Dict with 8 analysis results

        Returns:
            Saved investigation record
        """
        import json

        with db_session() as conn:
            with conn.cursor() as cur:
                # Upsert - one investigation per dataset
                cur.execute(
                    """
                    INSERT INTO dataset_investigations (
                        dataset_id, user_id,
                        column_roles, missingness, descriptive_stats, outliers,
                        correlations, time_series_readiness, segmentation_suggestions, data_quality
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (dataset_id) DO UPDATE SET
                        column_roles = EXCLUDED.column_roles,
                        missingness = EXCLUDED.missingness,
                        descriptive_stats = EXCLUDED.descriptive_stats,
                        outliers = EXCLUDED.outliers,
                        correlations = EXCLUDED.correlations,
                        time_series_readiness = EXCLUDED.time_series_readiness,
                        segmentation_suggestions = EXCLUDED.segmentation_suggestions,
                        data_quality = EXCLUDED.data_quality,
                        computed_at = NOW()
                    RETURNING id, dataset_id, user_id,
                              column_roles, missingness, descriptive_stats, outliers,
                              correlations, time_series_readiness, segmentation_suggestions, data_quality,
                              computed_at
                    """,
                    (
                        dataset_id,
                        user_id,
                        json.dumps(investigation.get("column_roles")),
                        json.dumps(investigation.get("missingness")),
                        json.dumps(investigation.get("descriptive_stats")),
                        json.dumps(investigation.get("outliers")),
                        json.dumps(investigation.get("correlations")),
                        json.dumps(investigation.get("time_series_readiness")),
                        json.dumps(investigation.get("segmentation_suggestions")),
                        json.dumps(investigation.get("data_quality")),
                    ),
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return self._row_to_investigation(row)
        return {}

    def _row_to_investigation(self, row: Any) -> dict[str, Any]:
        """Convert database row to investigation dict."""
        return {
            "id": str(row["id"]),
            "dataset_id": str(row["dataset_id"]),
            "column_roles": row["column_roles"],
            "missingness": row["missingness"],
            "descriptive_stats": row["descriptive_stats"],
            "outliers": row["outliers"],
            "correlations": row["correlations"],
            "time_series_readiness": row["time_series_readiness"],
            "segmentation_suggestions": row["segmentation_suggestions"],
            "data_quality": row["data_quality"],
            "computed_at": row["computed_at"].isoformat() if row["computed_at"] else None,
        }

    def get_investigation(self, dataset_id: str, user_id: str) -> dict[str, Any] | None:
        """Get investigation for a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)

        Returns:
            Investigation record or None
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT i.id, i.dataset_id, i.user_id,
                           i.column_roles, i.missingness, i.descriptive_stats, i.outliers,
                           i.correlations, i.time_series_readiness, i.segmentation_suggestions, i.data_quality,
                           i.computed_at
                    FROM dataset_investigations i
                    JOIN datasets d ON d.id = i.dataset_id
                    WHERE i.dataset_id = %s AND d.user_id = %s AND d.deleted_at IS NULL
                    """,
                    (dataset_id, user_id),
                )
                row = cur.fetchone()

        if row:
            return self._row_to_investigation(row)
        return None

    def update_column_role(
        self,
        dataset_id: str,
        user_id: str,
        column_name: str,
        new_role: str,
    ) -> dict[str, Any] | None:
        """Update a single column's role in the investigation.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)
            column_name: Column to update
            new_role: New role (metric, dimension, id, timestamp, unknown)

        Returns:
            Updated investigation or None if not found
        """
        import json

        investigation = self.get_investigation(dataset_id, user_id)
        if not investigation:
            return None

        column_roles = investigation.get("column_roles", {})
        roles_list = column_roles.get("roles", [])

        # Update the role for the specified column
        updated = False
        for role_entry in roles_list:
            if role_entry.get("column") == column_name:
                role_entry["role"] = new_role
                role_entry["confidence"] = 1.0  # User override = 100% confidence
                role_entry["reasoning"] = "User override"
                updated = True
                break

        if not updated:
            return None

        # Rebuild metric_columns and dimension_columns lists
        metric_columns = [r["column"] for r in roles_list if r["role"] == "metric"]
        dimension_columns = [r["column"] for r in roles_list if r["role"] == "dimension"]

        column_roles["roles"] = roles_list
        column_roles["metric_columns"] = metric_columns
        column_roles["dimension_columns"] = dimension_columns

        # Update just the column_roles field
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE dataset_investigations
                    SET column_roles = %s
                    WHERE dataset_id = %s
                    RETURNING id, dataset_id, user_id,
                              column_roles, missingness, descriptive_stats, outliers,
                              correlations, time_series_readiness, segmentation_suggestions, data_quality,
                              computed_at
                    """,
                    (json.dumps(column_roles), dataset_id),
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return self._row_to_investigation(row)
        return None

    def delete_investigation(self, dataset_id: str, user_id: str) -> bool:
        """Delete investigation for a dataset."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM dataset_investigations i
                    USING datasets d
                    WHERE i.dataset_id = d.id
                      AND i.dataset_id = %s
                      AND d.user_id = %s
                    RETURNING i.id
                    """,
                    (dataset_id, user_id),
                )
                result = cur.fetchone()
                conn.commit()

        return result is not None

    # =========================================================================
    # Dataset Business Context
    # =========================================================================

    def save_business_context(
        self,
        dataset_id: str,
        user_id: str,
        business_goal: str | None = None,
        key_metrics: list[str] | None = None,
        kpis: list[str] | None = None,
        objectives: str | None = None,
        industry: str | None = None,
        additional_context: str | None = None,
    ) -> dict[str, Any]:
        """Save or update business context for a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID
            business_goal: User's business goal
            key_metrics: List of key metrics
            kpis: List of KPIs
            objectives: Objectives text
            industry: Industry name
            additional_context: Any additional context

        Returns:
            Saved business context record
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Upsert - one context per dataset
                cur.execute(
                    """
                    INSERT INTO dataset_business_context (
                        dataset_id, user_id,
                        business_goal, key_metrics, kpis, objectives, industry, additional_context
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (dataset_id) DO UPDATE SET
                        business_goal = EXCLUDED.business_goal,
                        key_metrics = EXCLUDED.key_metrics,
                        kpis = EXCLUDED.kpis,
                        objectives = EXCLUDED.objectives,
                        industry = EXCLUDED.industry,
                        additional_context = EXCLUDED.additional_context,
                        updated_at = NOW()
                    RETURNING id, dataset_id, user_id,
                              business_goal, key_metrics, kpis, objectives, industry, additional_context,
                              created_at, updated_at
                    """,
                    (
                        dataset_id,
                        user_id,
                        business_goal,
                        key_metrics,
                        kpis,
                        objectives,
                        industry,
                        additional_context,
                    ),
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return self._row_to_business_context(row)
        return {}

    def _row_to_business_context(self, row: Any) -> dict[str, Any]:
        """Convert database row to business context dict."""
        return {
            "id": str(row["id"]),
            "dataset_id": str(row["dataset_id"]),
            "business_goal": row["business_goal"],
            "key_metrics": row["key_metrics"] or [],
            "kpis": row["kpis"] or [],
            "objectives": row["objectives"],
            "industry": row["industry"],
            "additional_context": row["additional_context"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }

    def get_business_context(self, dataset_id: str, user_id: str) -> dict[str, Any] | None:
        """Get business context for a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (for ownership check)

        Returns:
            Business context record or None
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT bc.id, bc.dataset_id, bc.user_id,
                           bc.business_goal, bc.key_metrics, bc.kpis, bc.objectives,
                           bc.industry, bc.additional_context,
                           bc.created_at, bc.updated_at
                    FROM dataset_business_context bc
                    JOIN datasets d ON d.id = bc.dataset_id
                    WHERE bc.dataset_id = %s AND d.user_id = %s AND d.deleted_at IS NULL
                    """,
                    (dataset_id, user_id),
                )
                row = cur.fetchone()

        if row:
            return self._row_to_business_context(row)
        return None

    def delete_business_context(self, dataset_id: str, user_id: str) -> bool:
        """Delete business context for a dataset."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM dataset_business_context bc
                    USING datasets d
                    WHERE bc.dataset_id = d.id
                      AND bc.dataset_id = %s
                      AND d.user_id = %s
                    RETURNING bc.id
                    """,
                    (dataset_id, user_id),
                )
                result = cur.fetchone()
                conn.commit()

        return result is not None

    # =========================================================================
    # Dataset Comparisons
    # =========================================================================

    def save_comparison(
        self,
        user_id: str,
        dataset_a_id: str,
        dataset_b_id: str,
        schema_comparison: dict[str, Any],
        statistics_comparison: dict[str, Any],
        key_metrics_comparison: dict[str, Any],
        insights: list[str],
        name: str | None = None,
    ) -> dict[str, Any]:
        """Save a dataset comparison result.

        Args:
            user_id: User performing comparison
            dataset_a_id: First dataset (baseline)
            dataset_b_id: Second dataset (comparison)
            schema_comparison: Schema comparison result
            statistics_comparison: Statistics comparison result
            key_metrics_comparison: Key metrics comparison result
            insights: List of generated insights
            name: Optional name for the comparison

        Returns:
            Created comparison record
        """
        from psycopg2.extras import Json

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO dataset_comparisons (
                        user_id, dataset_a_id, dataset_b_id, name,
                        schema_comparison, statistics_comparison,
                        key_metrics_comparison, insights
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, dataset_a_id, dataset_b_id, name,
                              schema_comparison, statistics_comparison,
                              key_metrics_comparison, insights, created_at, updated_at
                    """,
                    (
                        user_id,
                        dataset_a_id,
                        dataset_b_id,
                        name,
                        Json(schema_comparison),
                        Json(statistics_comparison),
                        Json(key_metrics_comparison),
                        Json(insights),
                    ),
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return self._row_to_comparison(row)
        return {}

    def get_comparison(self, comparison_id: str, user_id: str) -> dict[str, Any] | None:
        """Get a comparison by ID."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, dataset_a_id, dataset_b_id, name,
                           schema_comparison, statistics_comparison,
                           key_metrics_comparison, insights, created_at, updated_at
                    FROM dataset_comparisons
                    WHERE id = %s AND user_id = %s
                    """,
                    (comparison_id, user_id),
                )
                row = cur.fetchone()

        if row:
            return self._row_to_comparison(row)
        return None

    def get_comparison_by_datasets(
        self, dataset_a_id: str, dataset_b_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Get existing comparison between two datasets (either direction)."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, dataset_a_id, dataset_b_id, name,
                           schema_comparison, statistics_comparison,
                           key_metrics_comparison, insights, created_at, updated_at
                    FROM dataset_comparisons
                    WHERE user_id = %s
                      AND ((dataset_a_id = %s AND dataset_b_id = %s)
                           OR (dataset_a_id = %s AND dataset_b_id = %s))
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (user_id, dataset_a_id, dataset_b_id, dataset_b_id, dataset_a_id),
                )
                row = cur.fetchone()

        if row:
            return self._row_to_comparison(row)
        return None

    def list_comparisons_for_dataset(
        self, dataset_id: str, user_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """List all comparisons involving a specific dataset."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.id, c.user_id, c.dataset_a_id, c.dataset_b_id, c.name,
                           c.schema_comparison, c.statistics_comparison,
                           c.key_metrics_comparison, c.insights, c.created_at, c.updated_at,
                           da.name as dataset_a_name, db.name as dataset_b_name
                    FROM dataset_comparisons c
                    JOIN datasets da ON da.id = c.dataset_a_id
                    JOIN datasets db ON db.id = c.dataset_b_id
                    WHERE c.user_id = %s
                      AND (c.dataset_a_id = %s OR c.dataset_b_id = %s)
                    ORDER BY c.created_at DESC
                    LIMIT %s
                    """,
                    (user_id, dataset_id, dataset_id, limit),
                )
                rows = cur.fetchall()

        return [self._row_to_comparison(row) for row in rows]

    def delete_comparison(self, comparison_id: str, user_id: str) -> bool:
        """Delete a comparison."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM dataset_comparisons
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                    """,
                    (comparison_id, user_id),
                )
                result = cur.fetchone()
                conn.commit()

        return result is not None

    def _row_to_comparison(self, row: Any) -> dict[str, Any]:
        """Convert a database row to comparison dict."""
        result = {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "dataset_a_id": str(row["dataset_a_id"]),
            "dataset_b_id": str(row["dataset_b_id"]),
            "name": row["name"],
            "schema_comparison": row["schema_comparison"],
            "statistics_comparison": row["statistics_comparison"],
            "key_metrics_comparison": row["key_metrics_comparison"],
            "insights": row["insights"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        # Add dataset names if available
        if "dataset_a_name" in row.keys():
            result["dataset_a_name"] = row["dataset_a_name"]
        if "dataset_b_name" in row.keys():
            result["dataset_b_name"] = row["dataset_b_name"]
        return result

    # =========================================================================
    # Multi-Dataset Analyses
    # =========================================================================

    def save_multi_analysis(
        self,
        user_id: str,
        dataset_ids: list[str],
        common_schema: dict[str, Any],
        anomalies: list[dict[str, Any]],
        dataset_summaries: list[dict[str, Any]],
        pairwise_comparisons: list[dict[str, Any]],
        name: str | None = None,
    ) -> dict[str, Any]:
        """Save a multi-dataset analysis result.

        Args:
            user_id: User performing analysis
            dataset_ids: List of 2-5 dataset UUIDs
            common_schema: Schema comparison across all datasets
            anomalies: List of detected anomalies
            dataset_summaries: Per-dataset summary stats
            pairwise_comparisons: Results from pairwise DatasetComparator
            name: Optional name for the analysis

        Returns:
            Created analysis record
        """
        from psycopg2.extras import Json

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO multi_dataset_analyses (
                        user_id, dataset_ids, name,
                        common_schema, anomalies, dataset_summaries, pairwise_comparisons
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, dataset_ids, name,
                              common_schema, anomalies, dataset_summaries, pairwise_comparisons,
                              created_at, updated_at
                    """,
                    (
                        user_id,
                        dataset_ids,
                        name,
                        Json(common_schema),
                        Json(anomalies),
                        Json(dataset_summaries),
                        Json(pairwise_comparisons),
                    ),
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return self._row_to_multi_analysis(row)
        return {}

    def get_multi_analysis(self, analysis_id: str, user_id: str) -> dict[str, Any] | None:
        """Get a multi-dataset analysis by ID."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, dataset_ids, name,
                           common_schema, anomalies, dataset_summaries, pairwise_comparisons,
                           created_at, updated_at
                    FROM multi_dataset_analyses
                    WHERE id = %s AND user_id = %s
                    """,
                    (analysis_id, user_id),
                )
                row = cur.fetchone()

        if row:
            return self._row_to_multi_analysis(row)
        return None

    def list_multi_analyses(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """List multi-dataset analyses for a user, newest first."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, dataset_ids, name,
                           common_schema, anomalies, dataset_summaries, pairwise_comparisons,
                           created_at, updated_at
                    FROM multi_dataset_analyses
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
                rows = cur.fetchall()

        return [self._row_to_multi_analysis(row) for row in rows]

    def delete_multi_analysis(self, analysis_id: str, user_id: str) -> bool:
        """Delete a multi-dataset analysis."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM multi_dataset_analyses
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                    """,
                    (analysis_id, user_id),
                )
                result = cur.fetchone()
                conn.commit()

        return result is not None

    def _row_to_multi_analysis(self, row: Any) -> dict[str, Any]:
        """Convert a database row to multi-analysis dict."""
        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "dataset_ids": [str(did) for did in row["dataset_ids"]] if row["dataset_ids"] else [],
            "name": row["name"],
            "common_schema": row["common_schema"],
            "anomalies": row["anomalies"],
            "dataset_summaries": row["dataset_summaries"],
            "pairwise_comparisons": row["pairwise_comparisons"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }

    # =========================================================================
    # Dataset Objective Analysis
    # =========================================================================

    def save_objective_analysis(self, analysis_data: dict[str, Any]) -> dict[str, Any]:
        """Save or update objective analysis for a dataset.

        Uses UPSERT to update existing analysis or create new one.

        Args:
            analysis_data: Analysis data including:
                - id: Analysis UUID
                - dataset_id: Dataset UUID
                - user_id: User UUID
                - analysis_mode: 'objective_focused' or 'open_exploration'
                - relevance_score: 0-100 or None
                - relevance_assessment: JSONB
                - data_story: JSONB
                - insights: JSONB array
                - context_snapshot: JSONB
                - selected_objective_id: Optional objective index

        Returns:
            Saved analysis record
        """
        import json

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO dataset_objective_analyses (
                        id, dataset_id, user_id, analysis_mode, relevance_score,
                        relevance_assessment, data_story, insights,
                        context_snapshot, selected_objective_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (dataset_id)
                    DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        analysis_mode = EXCLUDED.analysis_mode,
                        relevance_score = EXCLUDED.relevance_score,
                        relevance_assessment = EXCLUDED.relevance_assessment,
                        data_story = EXCLUDED.data_story,
                        insights = EXCLUDED.insights,
                        context_snapshot = EXCLUDED.context_snapshot,
                        selected_objective_id = EXCLUDED.selected_objective_id,
                        updated_at = NOW()
                    RETURNING id, dataset_id, user_id, analysis_mode, relevance_score,
                              relevance_assessment, data_story, insights,
                              context_snapshot, selected_objective_id,
                              created_at, updated_at
                    """,
                    (
                        analysis_data["id"],
                        analysis_data["dataset_id"],
                        analysis_data["user_id"],
                        analysis_data["analysis_mode"],
                        analysis_data.get("relevance_score"),
                        json.dumps(analysis_data.get("relevance_assessment"))
                        if analysis_data.get("relevance_assessment")
                        else None,
                        json.dumps(analysis_data.get("data_story"))
                        if analysis_data.get("data_story")
                        else None,
                        json.dumps(analysis_data.get("insights"))
                        if analysis_data.get("insights")
                        else None,
                        json.dumps(analysis_data.get("context_snapshot"))
                        if analysis_data.get("context_snapshot")
                        else None,
                        analysis_data.get("selected_objective_id"),
                    ),
                )
                row = cur.fetchone()
                conn.commit()

        if row:
            return self._row_to_objective_analysis(row)
        return {}

    def get_objective_analysis(self, dataset_id: str, user_id: str) -> dict[str, Any] | None:
        """Get objective analysis for a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User UUID

        Returns:
            Analysis record or None if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, dataset_id, user_id, analysis_mode, relevance_score,
                           relevance_assessment, data_story, insights,
                           context_snapshot, selected_objective_id,
                           created_at, updated_at
                    FROM dataset_objective_analyses
                    WHERE dataset_id = %s AND user_id = %s
                    """,
                    (dataset_id, user_id),
                )
                row = cur.fetchone()

        if row:
            return self._row_to_objective_analysis(row)
        return None

    def delete_objective_analysis(self, dataset_id: str, user_id: str) -> bool:
        """Delete objective analysis for a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User UUID

        Returns:
            True if deleted, False if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM dataset_objective_analyses
                    WHERE dataset_id = %s AND user_id = %s
                    RETURNING id
                    """,
                    (dataset_id, user_id),
                )
                result = cur.fetchone()
                conn.commit()

        return result is not None

    def _row_to_objective_analysis(self, row: Any) -> dict[str, Any]:
        """Convert database row to objective analysis dict."""
        return {
            "id": str(row["id"]),
            "dataset_id": str(row["dataset_id"]),
            "user_id": str(row["user_id"]),
            "analysis_mode": row["analysis_mode"],
            "relevance_score": row["relevance_score"],
            "relevance_assessment": row["relevance_assessment"],
            "data_story": row["data_story"],
            "insights": row["insights"],
            "context_snapshot": row["context_snapshot"],
            "selected_objective_id": row["selected_objective_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
