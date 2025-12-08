#!/usr/bin/env python3
"""Check table columns to verify correct column names for indexes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from psycopg2.extras import RealDictCursor

from bo1.state.database import db_session


def get_table_columns(table_name: str) -> list[dict]:
    """Get all columns for a table.

    Args:
        table_name: Name of the table to query.

    Returns:
        List of dictionaries containing column information.
    """
    query = """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = %s
    ORDER BY ordinal_position;
    """

    with db_session() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (table_name,))
            return cur.fetchall()


if __name__ == "__main__":
    tables = ["session_clarifications", "research_cache"]

    for table in tables:
        print(f"\n{table.upper()}:")
        print("=" * 80)
        columns = get_table_columns(table)
        for col in columns:
            nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
            print(f"  {col['column_name']:30} {col['data_type']:20} {nullable}")
