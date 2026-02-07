"""Tests for admin analytics SQL safety validation.

Critical path: ensures no SQL injection or mutation is possible.
"""

import pytest

from backend.services.admin_analytics.sql_safety import (
    DEFAULT_LIMIT,
    SQLValidationError,
    validate_sql,
)

# =============================================================================
# Valid queries
# =============================================================================


class TestValidQueries:
    """Queries that should pass validation."""

    def test_simple_select(self):
        sql = validate_sql("SELECT COUNT(*) FROM users")
        assert "SELECT COUNT(*) FROM users" in sql
        assert f"LIMIT {DEFAULT_LIMIT}" in sql

    def test_select_with_where(self):
        sql = validate_sql(
            "SELECT email, created_at FROM users WHERE created_at > NOW() - INTERVAL '30 days'"
        )
        assert "SELECT email" in sql

    def test_cte_query(self):
        sql = validate_sql(
            """
            WITH daily AS (
                SELECT DATE_TRUNC('day', created_at) AS day, COUNT(*) AS cnt
                FROM users
                GROUP BY 1
            )
            SELECT day, cnt FROM daily ORDER BY day
            """
        )
        assert "WITH daily AS" in sql

    def test_join_query(self):
        sql = validate_sql(
            """
            SELECT u.email, COUNT(s.id) as session_count
            FROM users u
            LEFT JOIN sessions s ON s.user_id = u.id
            GROUP BY u.email
            ORDER BY session_count DESC
            """
        )
        assert "LEFT JOIN sessions" in sql

    def test_existing_limit_preserved(self):
        sql = validate_sql("SELECT * FROM users LIMIT 10")
        assert "LIMIT 10" in sql
        # Should NOT inject another LIMIT
        assert sql.count("LIMIT") == 1

    def test_aggregate_functions(self):
        sql = validate_sql(
            "SELECT provider, SUM(total_cost) FROM api_costs WHERE created_at > NOW() - INTERVAL '7 days' GROUP BY provider"
        )
        assert "SUM(total_cost)" in sql

    def test_subquery_in_where(self):
        sql = validate_sql(
            """
            SELECT * FROM sessions
            WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@test.com')
            """
        )
        assert "SELECT * FROM sessions" in sql

    def test_case_insensitive(self):
        sql = validate_sql("select count(*) from users")
        assert "LIMIT" in sql

    def test_multiple_joins(self):
        sql = validate_sql(
            """
            SELECT u.email, p.name, c.content
            FROM users u
            JOIN sessions s ON s.user_id = u.id
            JOIN personas p ON p.session_id = s.id
            LEFT JOIN contributions c ON c.persona_id = p.id
            """
        )
        assert "JOIN personas" in sql


# =============================================================================
# Invalid queries - mutations
# =============================================================================


class TestMutationBlocking:
    """Mutation statements must be blocked."""

    def test_insert(self):
        with pytest.raises(SQLValidationError, match="SELECT/WITH"):
            validate_sql("INSERT INTO users (email) VALUES ('test@test.com')")

    def test_update(self):
        with pytest.raises(SQLValidationError, match="SELECT/WITH"):
            validate_sql("UPDATE users SET email = 'hacked' WHERE id = '1'")

    def test_delete(self):
        with pytest.raises(SQLValidationError, match="SELECT/WITH"):
            validate_sql("DELETE FROM users WHERE id = '1'")

    def test_drop_table(self):
        with pytest.raises(SQLValidationError, match="SELECT/WITH"):
            validate_sql("DROP TABLE users")

    def test_alter_table(self):
        with pytest.raises(SQLValidationError, match="SELECT/WITH"):
            validate_sql("ALTER TABLE users ADD COLUMN hacked TEXT")

    def test_truncate(self):
        with pytest.raises(SQLValidationError, match="SELECT/WITH"):
            validate_sql("TRUNCATE users")

    def test_create_table(self):
        with pytest.raises(SQLValidationError, match="SELECT/WITH"):
            validate_sql("CREATE TABLE evil (id INT)")

    def test_grant(self):
        with pytest.raises(SQLValidationError, match="SELECT/WITH"):
            validate_sql("GRANT ALL ON users TO public")

    def test_copy(self):
        with pytest.raises(SQLValidationError, match="SELECT/WITH"):
            validate_sql("COPY users TO '/tmp/dump.csv'")


# =============================================================================
# Invalid queries - system access
# =============================================================================


class TestSystemAccessBlocking:
    """System catalog and metadata access must be blocked."""

    def test_pg_tables(self):
        with pytest.raises(SQLValidationError, match="not allowed"):
            validate_sql("SELECT * FROM pg_tables")

    def test_pg_stat_statements(self):
        with pytest.raises(SQLValidationError, match="not allowed"):
            validate_sql("SELECT * FROM pg_stat_statements")

    def test_information_schema(self):
        with pytest.raises(SQLValidationError, match="not allowed|information_schema"):
            validate_sql("SELECT * FROM information_schema.tables")

    def test_select_into(self):
        with pytest.raises(SQLValidationError, match="INTO"):
            validate_sql("SELECT * INTO new_table FROM users")


# =============================================================================
# Invalid queries - table allowlist
# =============================================================================


class TestTableAllowlist:
    """Queries referencing non-allowed tables must be blocked."""

    def test_disallowed_table(self):
        with pytest.raises(SQLValidationError, match="not allowed"):
            validate_sql("SELECT * FROM secret_table")

    def test_partial_allowed(self):
        """If one table is allowed and another isn't, should reject."""
        with pytest.raises(SQLValidationError, match="not allowed"):
            validate_sql("SELECT * FROM users u JOIN secret_table s ON s.id = u.id")


# =============================================================================
# Invalid queries - structure
# =============================================================================


class TestStructuralValidation:
    """Structural SQL validation."""

    def test_empty_sql(self):
        with pytest.raises(SQLValidationError, match="Empty"):
            validate_sql("")

    def test_whitespace_only(self):
        with pytest.raises(SQLValidationError, match="Empty"):
            validate_sql("   ")

    def test_multiple_statements(self):
        with pytest.raises(SQLValidationError, match="1 statement"):
            validate_sql("SELECT 1; SELECT 2")

    def test_dynamic_execution(self):
        with pytest.raises(SQLValidationError, match="SELECT/WITH"):
            validate_sql("DO $$ BEGIN EXECUTE 'DROP TABLE users'; END $$")


# =============================================================================
# LIMIT injection
# =============================================================================


class TestLimitInjection:
    """LIMIT should be auto-injected when missing."""

    def test_limit_injected(self):
        sql = validate_sql("SELECT * FROM users")
        assert f"LIMIT {DEFAULT_LIMIT}" in sql

    def test_limit_not_doubled(self):
        sql = validate_sql("SELECT * FROM users LIMIT 5")
        assert sql.upper().count("LIMIT") == 1

    def test_limit_in_subquery_still_adds_outer(self):
        sql = validate_sql("SELECT * FROM (SELECT id FROM users LIMIT 5) sub")
        # Should have LIMIT in subquery AND auto-injected outer LIMIT
        assert sql.upper().count("LIMIT") == 2
