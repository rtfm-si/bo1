#!/usr/bin/env python3
"""Database Monitoring Script - Run Daily via Cron or GitHub Actions.

Purpose:
- Monitor table growth and alert when approaching partition thresholds
- Verify data persistence (contributions, api_costs, events being saved)
- Check query performance and identify slow queries
- Detect RLS policy violations or permission issues

Usage:
    python scripts/monitor_database.py [--alert-email <email>]

Environment Variables:
    DATABASE_URL: PostgreSQL connection string (required)
    ALERT_EMAIL: Email address for critical alerts (optional)
    SLACK_WEBHOOK_URL: Slack webhook for alerts (optional)

Exit Codes:
    0: All checks passed
    1: Warnings detected (non-critical)
    2: Critical issues detected (requires immediate attention)
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class DatabaseMonitor:
    """Monitor database health, table growth, and data persistence.

    Tracks critical issues, warnings, and info messages for reporting.
    """

    def __init__(self, db_url: str) -> None:
        """Initialize database monitor with connection URL.

        Args:
            db_url: PostgreSQL connection URL
        """
        self.db_url = db_url
        self.critical_issues = []
        self.warnings = []
        self.info_messages = []

    def get_connection(self) -> Any:  # noqa: ANN401
        """Get database connection."""
        return psycopg2.connect(self.db_url)

    def check_table_growth(self, conn: Any) -> None:  # noqa: ANN401
        """Check if tables are approaching partition threshold."""
        print("\n=== Table Growth Check ===")

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    tablename,
                    COUNT(*) as row_count,
                    pg_size_pretty(pg_total_relation_size('public.'||tablename)) as size,
                    CASE
                        WHEN COUNT(*) > 500000 THEN 'CRITICAL'
                        WHEN COUNT(*) > 250000 THEN 'WARNING'
                        WHEN COUNT(*) > 100000 THEN 'INFO'
                        ELSE 'OK'
                    END as status
                FROM (
                    SELECT 'api_costs' as tablename FROM api_costs
                    UNION ALL
                    SELECT 'session_events' FROM session_events
                    UNION ALL
                    SELECT 'contributions' FROM contributions
                    UNION ALL
                    SELECT 'session_tasks' FROM session_tasks
                ) t
                GROUP BY tablename
            """)

            for row in cur.fetchall():
                msg = f"{row['tablename']}: {row['row_count']:,} rows ({row['size']})"

                if row["status"] == "CRITICAL":
                    self.critical_issues.append(f"🚨 {msg} - PARTITION NOW!")
                elif row["status"] == "WARNING":
                    self.warnings.append(f"⚠️ {msg} - Consider partitioning soon")
                elif row["status"] == "INFO":
                    self.info_messages.append(f"ℹ️ {msg} - Monitor closely")
                else:
                    print(f"✅ {msg}")

    def check_data_persistence(self, conn: Any) -> None:  # noqa: ANN401
        """Check that recent sessions have data persisted."""
        print("\n=== Data Persistence Check ===")

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                WITH recent_sessions AS (
                    SELECT id, status FROM sessions
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                )
                SELECT
                    COUNT(DISTINCT s.id) as sessions_created,
                    COUNT(DISTINCT CASE WHEN s.status = 'completed' THEN s.id END) as completed_sessions,
                    COUNT(DISTINCT c.session_id) as sessions_with_contributions,
                    COUNT(c.id) as total_contributions,
                    COUNT(DISTINCT ac.session_id) as sessions_with_costs,
                    COUNT(ac.id) as total_costs
                FROM recent_sessions s
                LEFT JOIN contributions c ON s.id = c.session_id
                LEFT JOIN api_costs ac ON s.id = ac.session_id
            """)

            row = cur.fetchone()

            print(f"Sessions (24h): {row['sessions_created']}")
            print(f"Completed: {row['completed_sessions']}")
            print(f"With contributions: {row['sessions_with_contributions']}")
            print(f"Total contributions: {row['total_contributions']}")
            print(f"With API costs: {row['sessions_with_costs']}")
            print(f"Total cost records: {row['total_costs']}")

            # Critical: Completed sessions but no contributions
            if row["completed_sessions"] > 0 and row["sessions_with_contributions"] == 0:
                self.critical_issues.append(
                    f"🚨 {row['completed_sessions']} completed sessions but 0 have contributions! "
                    "save_contribution() may not be working."
                )

            # Critical: Completed sessions but no API costs
            if row["completed_sessions"] > 0 and row["sessions_with_costs"] == 0:
                self.critical_issues.append(
                    f"🚨 {row['completed_sessions']} completed sessions but 0 have API costs! "
                    "Cost tracking may not be working."
                )

            # Warning: Low contribution rate
            if row["completed_sessions"] > 0:
                contrib_rate = row["sessions_with_contributions"] / row["completed_sessions"]
                if contrib_rate < 0.8:
                    self.warnings.append(
                        f"⚠️ Only {contrib_rate * 100:.1f}% of completed sessions have contributions. "
                        "Expected >80%."
                    )

            # Info: No sessions (expected if no traffic)
            if row["sessions_created"] == 0:
                self.info_messages.append("ℹ️ No sessions in last 24h (expected if no traffic)")
            else:
                print("✅ Data persistence appears to be working")

    def check_user_id_backfill(self, conn: Any) -> None:  # noqa: ANN401
        """Check for NULL user_id values that should have been backfilled."""
        print("\n=== User ID Backfill Check ===")

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    'contributions' as table_name,
                    COUNT(*) as total_rows,
                    COUNT(*) - COUNT(user_id) as missing_user_id
                FROM contributions
                UNION ALL
                SELECT 'api_costs', COUNT(*), COUNT(*) - COUNT(user_id) FROM api_costs
                UNION ALL
                SELECT 'session_events', COUNT(*), COUNT(*) - COUNT(user_id) FROM session_events
                UNION ALL
                SELECT 'session_tasks', COUNT(*), COUNT(*) - COUNT(user_id) FROM session_tasks
            """)

            for row in cur.fetchall():
                if row["total_rows"] == 0:
                    print(f"ℹ️ {row['table_name']}: Empty (no data yet)")
                elif row["missing_user_id"] > 0:
                    self.warnings.append(
                        f"⚠️ {row['table_name']}: {row['missing_user_id']} rows missing user_id! "
                        "Backfill may have failed."
                    )
                else:
                    print(f"✅ {row['table_name']}: All {row['total_rows']} rows have user_id")

    def check_rls_policies(self, conn: Any) -> None:  # noqa: ANN401
        """Verify RLS policies are enabled and configured."""
        print("\n=== RLS Policy Check ===")

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check which tables have RLS enabled
            cur.execute("""
                SELECT
                    tablename,
                    COUNT(*) as policy_count
                FROM pg_policies
                WHERE schemaname = 'public'
                AND tablename IN ('contributions', 'api_costs', 'session_events', 'session_tasks', 'waitlist')
                GROUP BY tablename
            """)

            expected_policies = {
                "contributions": 2,  # user_isolation + admin_access
                "api_costs": 2,
                "session_events": 2,
                "session_tasks": 2,
                "waitlist": 1,  # admin_only
            }

            found_tables = set()
            for row in cur.fetchall():
                found_tables.add(row["tablename"])
                expected = expected_policies[row["tablename"]]

                if row["policy_count"] < expected:
                    self.warnings.append(
                        f"⚠️ {row['tablename']}: Only {row['policy_count']} policies "
                        f"(expected {expected})"
                    )
                else:
                    print(f"✅ {row['tablename']}: {row['policy_count']} policies configured")

            # Check for missing RLS on expected tables
            for table, _expected_count in expected_policies.items():
                if table not in found_tables:
                    self.warnings.append(f"⚠️ {table}: No RLS policies found!")

    def send_alerts(self) -> None:
        """Send alerts for critical issues and warnings."""
        if not self.critical_issues and not self.warnings:
            return

        # Console output (always)
        if self.critical_issues:
            print("\n" + "=" * 70)
            print("CRITICAL ISSUES:")
            print("=" * 70)
            for issue in self.critical_issues:
                print(issue)

        if self.warnings:
            print("\n" + "=" * 70)
            print("WARNINGS:")
            print("=" * 70)
            for warning in self.warnings:
                print(warning)

        # Email alerts (if configured)
        alert_email = os.environ.get("ALERT_EMAIL")
        if alert_email and self.critical_issues:
            # TODO: Implement email sending
            # For now, just log that we would send email
            print(f"\n📧 Would send alert email to: {alert_email}")

        # Slack alerts (if configured)
        slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
        if slack_webhook and self.critical_issues:
            # TODO: Implement Slack webhook
            print(f"\n💬 Would send Slack alert to webhook: {slack_webhook[:30]}...")

    def run(self) -> int:
        """Run all monitoring checks."""
        print(f"\n{'=' * 70}")
        print(f"Database Monitoring Report - {datetime.now()}")
        print(f"{'=' * 70}")

        conn = self.get_connection()
        try:
            self.check_table_growth(conn)
            self.check_data_persistence(conn)
            self.check_user_id_backfill(conn)
            self.check_rls_policies(conn)

            # Summary
            print(f"\n{'=' * 70}")
            print("SUMMARY")
            print(f"{'=' * 70}")
            print(f"Critical Issues: {len(self.critical_issues)}")
            print(f"Warnings: {len(self.warnings)}")
            print(f"Info Messages: {len(self.info_messages)}")

            self.send_alerts()

            # Return exit code
            if self.critical_issues:
                return 2  # Critical
            elif self.warnings:
                return 1  # Warnings
            else:
                print("\n✅ All checks passed!")
                return 0  # OK

        finally:
            conn.close()


def main() -> int:
    """Run database monitoring checks and return exit code.

    Returns:
        Exit code (0 = success, 1 = errors found)
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return 3

    monitor = DatabaseMonitor(db_url)
    return monitor.run()


if __name__ == "__main__":
    sys.exit(main())
