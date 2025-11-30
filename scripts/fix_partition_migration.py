#!/usr/bin/env python3
"""Fix partition migration issues"""

import os
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

# Get database connection
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False

try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        print("=== Checking current database state ===\n")

        # Check what tables exist
        cur.execute("""
            SELECT tablename FROM pg_tables
            WHERE tablename LIKE 'api_costs%'
               OR tablename LIKE 'session_events%'
            ORDER BY tablename
        """)
        tables = [row["tablename"] for row in cur.fetchall()]
        print(f"Existing tables: {tables}\n")

        # Check api_costs_old schema
        if "api_costs_old" in tables:
            print("=== api_costs_old schema ===")
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'api_costs_old'
                ORDER BY ordinal_position
            """)
            for row in cur.fetchall():
                print(f"  {row['column_name']}: {row['data_type']}")
            print()

        # Check session_events_old schema
        if "session_events_old" in tables:
            print("=== session_events_old schema ===")
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'session_events_old'
                ORDER BY ordinal_position
            """)
            for row in cur.fetchall():
                print(f"  {row['column_name']}: {row['data_type']}")
            print()

        # Check for partitions
        cur.execute("""
            SELECT tablename FROM pg_tables
            WHERE tablename ~ 'api_costs_\\d{4}_\\d{2}'
               OR tablename ~ 'session_events_\\d{4}_\\d{2}'
            ORDER BY tablename
        """)
        partitions = [row["tablename"] for row in cur.fetchall()]
        print(f"Existing partitions ({len(partitions)}): {partitions}\n")

        # Check materialized views
        cur.execute("""
            SELECT matviewname FROM pg_matviews
            WHERE schemaname = 'public'
        """)
        mvs = [row["matviewname"] for row in cur.fetchall()]
        print(f"Materialized views: {mvs}\n")

        print("=== CLEANUP PLAN ===")
        print("1. Drop all partition tables")
        print("2. Drop api_costs_old and session_events_old (CASCADE)")
        print("3. Reset alembic version to b0d1100890ab")
        print("4. Re-run partition migration with fixes")

        response = input("\nProceed with cleanup? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted")
            sys.exit(0)

        print("\n=== EXECUTING CLEANUP ===\n")

        # Drop all partition tables
        for partition in partitions:
            print(f"Dropping partition: {partition}")
            cur.execute(f"DROP TABLE IF EXISTS {partition} CASCADE")

        # Drop old tables
        if "api_costs_old" in tables:
            print("Dropping api_costs_old CASCADE")
            cur.execute("DROP TABLE IF EXISTS api_costs_old CASCADE")

        if "session_events_old" in tables:
            print("Dropping session_events_old CASCADE")
            cur.execute("DROP TABLE IF EXISTS session_events_old CASCADE")

        # Reset alembic version
        print("Resetting alembic version to b0d1100890ab")
        cur.execute("DELETE FROM alembic_version")
        cur.execute("INSERT INTO alembic_version (version_num) VALUES ('b0d1100890ab')")

        conn.commit()
        print("\n✅ Cleanup complete!")
        print("\nNext steps:")
        print("1. Fix the partition migration SQL")
        print("2. Run: uv run alembic upgrade head")

except Exception as e:
    conn.rollback()
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    conn.close()
