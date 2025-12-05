"""Database helper utilities for common query patterns.

This module provides reusable functions to eliminate the repetitive
db_session() / cursor pattern found throughout the API codebase.

Usage:
    from backend.api.utils.db_helpers import get_single_value, execute_query

    # Instead of 5 lines of db_session boilerplate:
    tier = get_single_value(
        "SELECT subscription_tier FROM users WHERE id = %s",
        (user_id,),
        column="subscription_tier",
        default="free"
    )

    # For fetching all rows:
    rows = execute_query(
        "SELECT * FROM competitor_profiles WHERE user_id = %s",
        (user_id,)
    )
"""

import logging
from typing import Any, Literal, overload

from psycopg2.extras import RealDictRow

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@overload
def execute_query(
    sql: str,
    params: tuple = (),
    *,
    fetch: Literal["one"],
) -> RealDictRow | None: ...


@overload
def execute_query(
    sql: str,
    params: tuple = (),
    *,
    fetch: Literal["all"] = "all",
) -> list[RealDictRow]: ...


@overload
def execute_query(
    sql: str,
    params: tuple = (),
    *,
    fetch: Literal["none"],
) -> None: ...


def execute_query(
    sql: str,
    params: tuple = (),
    *,
    fetch: Literal["one", "all", "none"] = "all",
) -> RealDictRow | list[RealDictRow] | None:
    """Execute a SQL query with standard connection handling.

    This is the base helper that handles the db_session() context manager
    pattern, eliminating boilerplate across the codebase.

    Args:
        sql: SQL query string with %s placeholders
        params: Tuple of parameters for the query
        fetch: What to return - "one" for single row, "all" for all rows,
               "none" for write operations

    Returns:
        - fetch="one": Single row dict or None
        - fetch="all": List of row dicts
        - fetch="none": None (for INSERT/UPDATE/DELETE)

    Examples:
        >>> # Fetch single row
        >>> row = execute_query(
        ...     "SELECT * FROM users WHERE id = %s",
        ...     (user_id,),
        ...     fetch="one"
        ... )

        >>> # Fetch all rows
        >>> rows = execute_query(
        ...     "SELECT * FROM sessions WHERE user_id = %s",
        ...     (user_id,)
        ... )

        >>> # Write operation
        >>> execute_query(
        ...     "UPDATE users SET name = %s WHERE id = %s",
        ...     (name, user_id),
        ...     fetch="none"
        ... )
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch == "one":
                return cur.fetchone()
            elif fetch == "all":
                return cur.fetchall()
            else:
                return None


def get_single_value[T](
    sql: str,
    params: tuple,
    *,
    column: str,
    default: T = None,  # type: ignore[assignment]
) -> T:
    """Get a single column value from a query.

    Convenience wrapper for the common pattern of fetching one value
    from a single row, with a default if not found.

    Args:
        sql: SQL query string
        params: Query parameters
        column: Column name to extract from result
        default: Default value if row not found or column is null

    Returns:
        The value from the specified column, or default if not found

    Examples:
        >>> tier = get_single_value(
        ...     "SELECT subscription_tier FROM users WHERE id = %s",
        ...     (user_id,),
        ...     column="subscription_tier",
        ...     default="free"
        ... )

        >>> count = get_single_value(
        ...     "SELECT COUNT(*) as count FROM sessions WHERE user_id = %s",
        ...     (user_id,),
        ...     column="count",
        ...     default=0
        ... )
    """
    row = execute_query(sql, params, fetch="one")
    if row is None:
        return default
    value = row.get(column)
    return value if value is not None else default


def get_row_by_id(
    table: str,
    id_value: Any,
    *,
    id_column: str = "id",
) -> RealDictRow | None:
    """Fetch a single row by its ID.

    Args:
        table: Table name
        id_value: ID value to match
        id_column: Name of ID column (default: "id")

    Returns:
        Row dict or None if not found

    Examples:
        >>> user = get_row_by_id("users", user_id)
        >>> session = get_row_by_id("sessions", "bo1_abc123", id_column="session_id")
    """
    # Note: Table name is not parameterizable, must be safe string
    if not table.isidentifier():
        raise ValueError(f"Invalid table name: {table}")
    if not id_column.isidentifier():
        raise ValueError(f"Invalid column name: {id_column}")

    return execute_query(
        f"SELECT * FROM {table} WHERE {id_column} = %s",  # noqa: S608
        (id_value,),
        fetch="one",
    )


def exists(
    table: str,
    *,
    where: str,
    params: tuple,
) -> bool:
    """Check if a row exists matching the condition.

    Args:
        table: Table name
        where: WHERE clause (without "WHERE" keyword)
        params: Parameters for the WHERE clause

    Returns:
        True if at least one matching row exists

    Examples:
        >>> if exists("users", where="email = %s", params=(email,)):
        ...     raise ValueError("Email already registered")
    """
    if not table.isidentifier():
        raise ValueError(f"Invalid table name: {table}")

    row = execute_query(
        f"SELECT 1 FROM {table} WHERE {where} LIMIT 1",  # noqa: S608
        params,
        fetch="one",
    )
    return row is not None


def count_rows(
    table: str,
    *,
    where: str | None = None,
    params: tuple = (),
) -> int:
    """Count rows in a table, optionally filtered.

    Args:
        table: Table name
        where: Optional WHERE clause (without "WHERE" keyword)
        params: Parameters for the WHERE clause

    Returns:
        Number of matching rows

    Examples:
        >>> total_users = count_rows("users")
        >>> user_sessions = count_rows(
        ...     "sessions",
        ...     where="user_id = %s",
        ...     params=(user_id,)
        ... )
    """
    if not table.isidentifier():
        raise ValueError(f"Invalid table name: {table}")

    if where:
        sql = f"SELECT COUNT(*) as count FROM {table} WHERE {where}"  # noqa: S608
    else:
        sql = f"SELECT COUNT(*) as count FROM {table}"  # noqa: S608

    return get_single_value(sql, params, column="count", default=0)
