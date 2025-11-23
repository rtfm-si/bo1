#!/usr/bin/env python3
"""Verify database indexes exist.

This script connects to the PostgreSQL database and lists all existing indexes
for the tables of interest: user_context, session_clarifications, research_cache.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bo1.state.postgres_manager import db_session


def check_indexes() -> None:
    """Check which indexes exist in the database."""
    # Query to list all indexes with detailed information
    query = """
    SELECT
        schemaname,
        tablename,
        indexname,
        indexdef
    FROM pg_indexes
    WHERE schemaname = 'public'
    ORDER BY tablename, indexname;
    """

    try:
        from psycopg2.extras import RealDictCursor

        with db_session() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query)
                indexes = cur.fetchall()

        print("Existing Indexes in PostgreSQL Database")
        print("=" * 100)

        current_table = None
        table_count = {}

        for row in indexes:
            # schema = row["schemaname"]  # Not currently used
            table = row["tablename"]
            index_name = row["indexname"]
            index_def = row["indexdef"]
            if table != current_table:
                print(f"\n{table.upper()}:")
                current_table = table
                table_count[table] = 0

            table_count[table] += 1
            print(f"  {table_count[table]}. {index_name}")
            print(f"     {index_def}")

        # Summary of indexes by table
        print("\n" + "=" * 100)
        print("SUMMARY:")
        for table, count in sorted(table_count.items()):
            print(f"  {table}: {count} indexes")

        print(f"\nTotal indexes: {len(indexes)}")

        return indexes

    except Exception as e:
        print(f"Error checking indexes: {e}")
        print("\nMake sure PostgreSQL is running and environment variables are set:")
        print("  - DATABASE_URL or individual DB_* variables")
        print("  - Try: make up")
        sys.exit(1)


def check_specific_indexes() -> None:
    """Check for specific indexes mentioned in the refactoring analysis."""
    # Expected indexes based on the task
    expected = {
        "user_context": ["idx_user_context_user_id"],
        "session_clarifications": [
            "idx_session_clarifications_session_id",
            "idx_session_clarifications_user_id",
        ],
        "research_cache": ["idx_research_cache_category", "idx_research_cache_created_at"],
    }

    print("\n" + "=" * 100)
    print("CHECKING EXPECTED INDEXES:")
    print("=" * 100)

    # Query to check if specific indexes exist
    query = """
    SELECT indexname
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND tablename = %s;
    """

    missing_indexes = []
    existing_indexes = []

    try:
        from psycopg2.extras import RealDictCursor

        with db_session() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for table, index_names in expected.items():
                    cur.execute(query, (table,))
                    table_indexes = {row["indexname"] for row in cur.fetchall()}

                    print(f"\n{table}:")
                    for expected_index in index_names:
                        if expected_index in table_indexes:
                            print(f"  ✅ {expected_index} (EXISTS)")
                            existing_indexes.append((table, expected_index))
                        else:
                            print(f"  ❌ {expected_index} (MISSING)")
                            missing_indexes.append((table, expected_index))

        print("\n" + "=" * 100)
        if missing_indexes:
            print("MISSING INDEXES:")
            for table, index_name in missing_indexes:
                print(f"  - {table}.{index_name}")
        else:
            print("✅ All expected indexes exist!")

        return existing_indexes, missing_indexes

    except Exception as e:
        print(f"Error checking specific indexes: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("Verifying PostgreSQL database indexes...\n")
    check_indexes()
    check_specific_indexes()
