"""Base repository with common database operations.

Provides:
- Connection management via db_session
- Common query execution patterns
- Type-safe result conversion
- JSON handling for JSONB columns
"""

import logging
from typing import Any

from psycopg2.extras import Json

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common database operations.

    All repositories inherit from this class to get:
    - Connection management
    - Query execution helpers
    - Result conversion utilities
    """

    def _execute_query(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        user_id: str | None = None,
        statement_timeout_ms: int | None = None,
    ) -> list[dict[str, Any]]:
        """Execute query and return results as list of dicts.

        Args:
            query: SQL query string
            params: Query parameters
            user_id: Optional user ID for RLS context
            statement_timeout_ms: Optional statement timeout in ms

        Returns:
            List of row dictionaries
        """
        with db_session(user_id=user_id, statement_timeout_ms=statement_timeout_ms) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    def _execute_one(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        user_id: str | None = None,
        statement_timeout_ms: int | None = None,
    ) -> dict[str, Any] | None:
        """Execute query and return first result or None.

        Args:
            query: SQL query string
            params: Query parameters
            user_id: Optional user ID for RLS context
            statement_timeout_ms: Optional statement timeout in ms

        Returns:
            Row dictionary or None if no results
        """
        with db_session(user_id=user_id, statement_timeout_ms=statement_timeout_ms) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return dict(row) if row else None

    def _execute_returning(
        self,
        query: str,
        params: tuple[Any, ...],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute INSERT/UPDATE with RETURNING clause.

        Args:
            query: SQL query with RETURNING clause
            params: Query parameters
            user_id: Optional user ID for RLS context

        Returns:
            Returned row dictionary

        Raises:
            ValueError: If no row returned (query failed)
        """
        with db_session(user_id=user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                if not row:
                    raise ValueError("Query did not return a row")
                return dict(row)

    def _execute_count(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        user_id: str | None = None,
    ) -> int:
        """Execute query and return affected row count.

        Args:
            query: SQL query string
            params: Query parameters
            user_id: Optional user ID for RLS context

        Returns:
            Number of affected rows
        """
        with db_session(user_id=user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return int(cur.rowcount)

    @staticmethod
    def _to_json(value: dict[str, Any] | list[Any] | None) -> Json | None:
        """Convert dict/list to psycopg2 Json for JSONB columns.

        Args:
            value: Dictionary or list to convert

        Returns:
            Json wrapper or None
        """
        return Json(value) if value else None

    @staticmethod
    def _validate_id(id_value: str, name: str = "id") -> str:
        """Validate non-empty string ID.

        Args:
            id_value: ID value to validate
            name: Parameter name for error message

        Returns:
            Validated ID value

        Raises:
            ValueError: If ID is empty or not a string
        """
        if not id_value or not isinstance(id_value, str):
            raise ValueError(f"{name} must be a non-empty string")
        return id_value

    @staticmethod
    def _validate_positive_int(value: int, name: str) -> int:
        """Validate non-negative integer.

        Args:
            value: Integer to validate
            name: Parameter name for error message

        Returns:
            Validated integer

        Raises:
            ValueError: If value is not a non-negative integer
        """
        if not isinstance(value, int):
            raise ValueError(f"{name} must be an integer, got {type(value).__name__}")
        if value < 0:
            raise ValueError(f"{name} must be non-negative, got {value}")
        return value

    def _execute_paginated(
        self,
        count_query: str,
        data_query: str,
        params: list[Any],
        page: int,
        per_page: int,
        user_id: str | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        """Execute paginated query with count.

        Args:
            count_query: SQL query to get total count (SELECT COUNT(*) ...)
            data_query: SQL query to get data (should have LIMIT %s OFFSET %s at end)
            params: Query parameters for both queries (count params first)
            page: Page number (1-indexed)
            per_page: Items per page
            user_id: Optional user ID for RLS context

        Returns:
            Tuple of (total_count, page_results)
        """
        offset = (page - 1) * per_page
        with db_session(user_id=user_id) as conn:
            with conn.cursor() as cur:
                # Get total count
                cur.execute(count_query, params)
                count_row = cur.fetchone()
                total_count = count_row["count"] if count_row else 0

                # Get paginated data
                cur.execute(data_query, [*params, per_page, offset])
                rows = cur.fetchall()

                return total_count, [dict(row) for row in rows]

    @staticmethod
    def _to_iso_string(value: Any) -> str:
        """Convert datetime to ISO format string, empty string if None.

        Args:
            value: Datetime value or None

        Returns:
            ISO format string or empty string
        """
        return value.isoformat() if value else ""

    @staticmethod
    def _to_iso_string_or_none(value: Any) -> str | None:
        """Convert datetime to ISO format string, None if None.

        Args:
            value: Datetime value or None

        Returns:
            ISO format string or None
        """
        return value.isoformat() if value else None
