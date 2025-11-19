"""SQL injection prevention utilities.

Provides safe query building utilities to prevent SQL injection attacks.
All SQL queries must use parameterized queries or this SafeQueryBuilder.
"""


class SafeQueryBuilder:
    """Prevents SQL injection by enforcing parameterized queries.

    This class ensures all SQL queries use proper parameter binding
    instead of f-string formatting, which is vulnerable to injection.

    Examples:
        >>> builder = SafeQueryBuilder("SELECT * FROM users WHERE id = %s")
        >>> builder.add_param("123")
        >>> query, params = builder.build()
        >>> cursor.execute(query, params)

        >>> # With interval filter
        >>> builder = SafeQueryBuilder("SELECT * FROM cache WHERE 1=1")
        >>> builder.add_interval_filter("created_at", 90)
        >>> query, params = builder.build()
        # Returns: ("SELECT * FROM cache WHERE 1=1 AND created_at >= ...", [90])
    """

    def __init__(self, base_query: str) -> None:
        """Initialize query builder with base SQL.

        Args:
            base_query: Base SQL query with %s placeholders for parameters

        Raises:
            ValueError: If f-string formatting detected in query
        """
        # Detect f-string patterns (security check)
        if "{" in base_query or "}" in base_query:
            raise ValueError(
                "f-string formatting detected in SQL query. "
                "Use %s placeholders instead for safe parameterization."
            )

        self.query = base_query
        self.params: list[str | int | float | bool | None] = []

    def add_param(self, value: str | int | float | bool | None) -> "SafeQueryBuilder":
        """Add a parameter value.

        Args:
            value: Parameter value to add

        Returns:
            Self for method chaining
        """
        self.params.append(value)
        return self

    def add_condition(self, column: str, operator: str = "=") -> "SafeQueryBuilder":
        """Add a WHERE condition with parameter placeholder.

        Args:
            column: Column name (must be a valid identifier)
            operator: SQL operator (=, >, <, >=, <=, !=, LIKE, etc.)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If column name contains suspicious characters
        """
        # Validate column name (prevent injection via column names)
        if not column.replace("_", "").replace(".", "").isalnum():
            raise ValueError(
                f"Invalid column name '{column}'. "
                f"Only alphanumeric characters, underscores, and dots allowed."
            )

        # Validate operator (whitelist approach)
        valid_operators = {"=", ">", "<", ">=", "<=", "!=", "<>", "LIKE", "ILIKE", "IN", "NOT IN"}
        if operator.upper() not in valid_operators:
            raise ValueError(
                f"Invalid operator '{operator}'. Allowed: {', '.join(valid_operators)}"
            )

        self.query += f" AND {column} {operator} %s"
        return self

    def add_interval_filter(
        self, column: str, days: int, operator: str = ">="
    ) -> "SafeQueryBuilder":
        """Safely add PostgreSQL interval filter for time-based queries.

        Args:
            column: Column name to filter on (must be timestamp/date column)
            days: Number of days for interval (must be positive integer)
            operator: Comparison operator (default: >=)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If days is not a positive integer or column name invalid
        """
        # Validate column name (prevent injection)
        if not column.replace("_", "").isalnum():
            raise ValueError(
                f"Invalid column name '{column}'. Only alphanumeric and underscores allowed."
            )

        # Validate days parameter (CRITICAL: prevents injection)
        if not isinstance(days, int):
            raise ValueError(f"days must be an integer, got {type(days).__name__}")

        if days < 0:
            raise ValueError(f"days must be non-negative, got {days}")

        # Validate operator
        valid_operators = {">=", ">", "<=", "<", "="}
        if operator not in valid_operators:
            raise ValueError(
                f"Invalid operator '{operator}'. Allowed: {', '.join(valid_operators)}"
            )

        # Safe: We've validated days is an int, so f-string is safe here
        # This uses PostgreSQL's INTERVAL syntax which requires string literal
        self.query += f" AND {column} {operator} NOW() - INTERVAL '{days} days'"
        return self

    def add_order_by(self, column: str, direction: str = "ASC") -> "SafeQueryBuilder":
        """Add ORDER BY clause.

        Args:
            column: Column name to order by
            direction: Sort direction (ASC or DESC)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If column name or direction is invalid
        """
        # Validate column name
        if not column.replace("_", "").replace(".", "").isalnum():
            raise ValueError(f"Invalid column name '{column}'")

        # Validate direction
        direction = direction.upper()
        if direction not in {"ASC", "DESC"}:
            raise ValueError(f"Invalid sort direction '{direction}'. Use ASC or DESC.")

        self.query += f" ORDER BY {column} {direction}"
        return self

    def add_limit(self, limit: int) -> "SafeQueryBuilder":
        """Add LIMIT clause.

        Args:
            limit: Maximum number of rows to return

        Returns:
            Self for method chaining

        Raises:
            ValueError: If limit is not a positive integer
        """
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"LIMIT must be a positive integer, got {limit}")

        self.query += f" LIMIT {limit}"
        return self

    def build(self) -> tuple[str, list[str | int | float | bool | None]]:
        """Build final query and parameters tuple.

        Returns:
            Tuple of (query_string, parameters_list)

        Examples:
            >>> query, params = builder.build()
            >>> cursor.execute(query, params)
        """
        return self.query, self.params


def validate_sql_identifier(identifier: str) -> str:
    """Validate SQL identifier (table name, column name, etc.).

    Args:
        identifier: SQL identifier to validate

    Returns:
        The validated identifier

    Raises:
        ValueError: If identifier contains suspicious characters
    """
    # Allow alphanumeric, underscores, and dots (for qualified names)
    if not identifier.replace("_", "").replace(".", "").isalnum():
        raise ValueError(
            f"Invalid SQL identifier '{identifier}'. "
            f"Only alphanumeric characters, underscores, and dots allowed."
        )

    return identifier
