#!/usr/bin/env python3
"""Check Alembic migration history in the database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from psycopg2.extras import RealDictCursor

from bo1.state.postgres_manager import db_session


def check_migration_history() -> str | None:
    """Check which migrations have been applied."""
    # Check if alembic_version table exists
    check_table_query = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'alembic_version'
    ) as exists;
    """

    with db_session() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(check_table_query)
            result = cur.fetchone()
            table_exists = result["exists"] if result else False

            if not table_exists:
                print("❌ alembic_version table does not exist")
                print("   No migrations have been run yet.")
                return None

            # Get current migration version
            version_query = "SELECT version_num FROM alembic_version;"
            cur.execute(version_query)
            result = cur.fetchone()

            if result:
                version = result["version_num"]
                print(f"✅ Current migration version: {version}")
                return version
            else:
                print("⚠️  alembic_version table exists but is empty")
                return None


def check_table_exists(table_name: str) -> bool:
    """Check if a specific table exists."""
    query = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = %s
    ) as exists;
    """

    with db_session() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (table_name,))
            result = cur.fetchone()
            return result["exists"] if result else False


def list_all_tables() -> list[str]:
    """List all tables in the database.

    Returns:
        List of table names in the public schema.
    """
    query = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name;
    """

    with db_session() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            tables = [row["table_name"] for row in cur.fetchall()]
            return tables


if __name__ == "__main__":
    print("Checking Alembic migration history...\n")

    version = check_migration_history()

    print("\nChecking for expected tables:")
    expected_tables = [
        "users",
        "sessions",
        "personas",
        "contributions",
        "votes",
        "audit_log",
        "user_context",
        "session_clarifications",
        "research_cache",
        "actions",
    ]

    for table in expected_tables:
        exists = check_table_exists(table)
        status = "✅" if exists else "❌"
        print(f"  {status} {table}")

    print("\nAll tables in database:")
    all_tables = list_all_tables()
    for table in all_tables:
        print(f"  - {table}")
