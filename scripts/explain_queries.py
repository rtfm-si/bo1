#!/usr/bin/env python3
"""Show query execution plans to verify index usage.

This script uses EXPLAIN ANALYZE to show how PostgreSQL executes queries
and whether it uses indexes or performs full table scans.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from psycopg2.extras import RealDictCursor

from bo1.state.database import db_session


def explain_query(query: str, params: tuple = None, description: str = "") -> None:
    """Show query execution plan."""
    # Note: EXPLAIN ANALYZE actually executes the query, so use carefully
    # For non-existent data, use EXPLAIN (without ANALYZE) to avoid runtime errors
    explain_query_text = f"EXPLAIN {query}"

    print(f"\n{description}")
    print("=" * 100)
    print(f"Query: {query}")
    if params:
        print(f"Params: {params}")
    print()

    with db_session() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(explain_query_text, params or ())
            plan = cur.fetchall()

    print("Execution Plan:")
    for row in plan:
        # RealDictCursor returns dict-like objects
        plan_line = row.get("QUERY PLAN", "") if isinstance(row, dict) else str(row)
        print(f"  {plan_line}")


def show_query_plans() -> None:
    """Show execution plans for key queries."""
    # Query 1: user_context by user_id
    explain_query(
        "SELECT * FROM user_context WHERE user_id = %s;",
        ("test-user-id",),
        "Query 1: user_context by user_id (should use idx_user_context_user_id)",
    )

    # Query 2: session_clarifications by session_id
    explain_query(
        "SELECT * FROM session_clarifications WHERE session_id = %s;",
        ("test-session-id",),
        "Query 2: session_clarifications by session_id (should use idx_clarifications_session)",
    )

    # Query 3: research_cache by category and date (DESC order)
    explain_query(
        "SELECT * FROM research_cache WHERE category = %s ORDER BY research_date DESC LIMIT 10;",
        ("saas_metrics",),
        "Query 3: research_cache by category + date sorting (should use indexes)",
    )

    # Query 4: research_cache date range filter
    explain_query(
        """
        SELECT * FROM research_cache
        WHERE research_date >= NOW() - INTERVAL '90 days'
        ORDER BY research_date DESC
        LIMIT 10;
        """,
        None,
        "Query 4: research_cache date range filtering (should use idx_research_cache_research_date)",
    )

    # Query 5: Combined category + date filter (composite query)
    explain_query(
        """
        SELECT * FROM research_cache
        WHERE category = %s
        AND research_date >= NOW() - INTERVAL '30 days'
        ORDER BY research_date DESC
        LIMIT 10;
        """,
        ("saas_metrics",),
        "Query 5: Combined category + date filter (should use both indexes efficiently)",
    )

    print("\n" + "=" * 100)
    print("INTERPRETATION:")
    print("=" * 100)
    print("✅ GOOD: 'Index Scan using idx_...' or 'Bitmap Index Scan on idx_...'")
    print("   - PostgreSQL is using the index (fast)")
    print()
    print("❌ BAD: 'Seq Scan on table_name'")
    print("   - PostgreSQL is doing a full table scan (slow on large datasets)")
    print()
    print("ℹ️  NOTE: With small datasets (<1000 rows), PostgreSQL may choose Seq Scan")
    print("   because it's actually faster than using an index. This is expected.")
    print("   Indexes show their value with large datasets (>10K rows).")


if __name__ == "__main__":
    print("Analyzing Query Execution Plans...")
    print("This shows whether PostgreSQL uses indexes or does full table scans.\n")
    show_query_plans()
