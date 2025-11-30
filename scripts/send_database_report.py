#!/usr/bin/env python3
"""Generate and send database reports via ntfy.

Usage:
    python scripts/send_database_report.py daily
    python scripts/send_database_report.py weekly
"""

import asyncio
import os
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.api.ntfy import notify_database_alert, notify_database_report

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)


def get_daily_report() -> tuple[str, str, str]:
    """Generate daily database health report with business metrics.

    Returns:
        Tuple of (summary, details, status)
        status: "ok" | "warning" | "critical"
    """
    conn = psycopg2.connect(DATABASE_URL)
    issues = []
    warnings = []
    status = "ok"

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # ===== BUSINESS METRICS (Last 24h) =====

            # Meetings/sessions run in last 24 hours
            cur.execute("""
                SELECT COUNT(*) as count
                FROM sessions
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            meetings_24h = cur.fetchone()["count"]

            # Total cost in last 24 hours
            cur.execute("""
                SELECT
                    COALESCE(SUM(total_cost), 0) as total_cost,
                    COUNT(*) as api_calls
                FROM api_costs
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            cost_24h = cur.fetchone()

            # New users in last 24 hours
            cur.execute("""
                SELECT COUNT(*) as count
                FROM users
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            new_users_24h = cur.fetchone()["count"]

            # Users logged in (last 7 days)
            cur.execute("""
                SELECT COUNT(DISTINCT user_id) as count
                FROM sessions
                WHERE created_at > NOW() - INTERVAL '7 days'
            """)
            active_users_7d = cur.fetchone()["count"]

            # Total users (all time)
            cur.execute("SELECT COUNT(*) as count FROM users")
            total_users = cur.fetchone()["count"]

            # ===== DATABASE HEALTH CHECKS =====

            # Check table growth
            cur.execute("""
                SELECT
                    'api_costs' as table_name,
                    COUNT(*) as row_count
                FROM api_costs
                UNION ALL
                SELECT 'session_events', COUNT(*) FROM session_events
                UNION ALL
                SELECT 'contributions', COUNT(*) FROM contributions
                UNION ALL
                SELECT 'sessions', COUNT(*) FROM sessions
            """)
            table_counts = {row["table_name"]: row["row_count"] for row in cur.fetchall()}

            # Check for high-growth tables approaching partition threshold
            for table, count in table_counts.items():
                if count > 500000:
                    issues.append(f"🔴 {table}: {count:,} rows (CRITICAL - needs partitioning)")
                    status = "critical"
                elif count > 250000:
                    warnings.append(f"🟡 {table}: {count:,} rows (WARNING)")
                    if status == "ok":
                        status = "warning"

            # Check data persistence (last 24 hours)
            cur.execute("""
                WITH recent_sessions AS (
                    SELECT id FROM sessions WHERE created_at > NOW() - INTERVAL '24 hours'
                )
                SELECT
                    COUNT(DISTINCT s.id) as sessions_created,
                    COUNT(DISTINCT c.session_id) as sessions_with_contributions
                FROM recent_sessions s
                LEFT JOIN contributions c ON s.id = c.session_id
            """)
            persistence = cur.fetchone()

            if persistence["sessions_created"] > 0:
                contrib_rate = (
                    persistence["sessions_with_contributions"] / persistence["sessions_created"]
                ) * 100
                if contrib_rate < 50:
                    issues.append(
                        f"🔴 Contribution save rate: {contrib_rate:.0f}% (CRITICAL - data loss)"
                    )
                    status = "critical"
                elif contrib_rate < 80:
                    warnings.append(f"🟡 Contribution save rate: {contrib_rate:.0f}%")
                    if status == "ok":
                        status = "warning"

            # ===== BUILD SUMMARY =====

            # Build summary based on status and business metrics
            if status == "critical":
                summary = "🔴 CRITICAL ISSUES DETECTED"
            elif status == "warning":
                summary = (
                    f"🟡 {meetings_24h} meetings, ${cost_24h['total_cost']:.2f} cost (warnings)"
                )
            else:
                summary = f"✅ {meetings_24h} meetings, {new_users_24h} new users, {active_users_7d} active"

            # ===== BUILD DETAILS =====
            details_parts = []

            # Business Metrics (always first)
            details_parts.append("**📊 Business Metrics (24h)**")
            details_parts.append(f"  • Meetings run: {meetings_24h}")
            details_parts.append(
                f"  • Total cost: ${cost_24h['total_cost']:.2f} ({cost_24h['api_calls']} API calls)"
            )
            details_parts.append(f"  • New users: {new_users_24h}")
            details_parts.append("\n**👥 User Activity**")
            details_parts.append(f"  • Active users (7d): {active_users_7d}")
            details_parts.append(f"  • Total users: {total_users}")

            # Database Health
            details_parts.append("\n**💾 Database Health**")
            for table, count in sorted(table_counts.items()):
                details_parts.append(f"  • {table}: {count:,} rows")

            # Data Persistence
            if persistence["sessions_created"] > 0:
                details_parts.append("\n**🔄 Data Persistence (24h)**")
                details_parts.append(f"  • Sessions created: {persistence['sessions_created']}")
                details_parts.append(
                    f"  • With contributions: {persistence['sessions_with_contributions']}"
                )
                if persistence["sessions_created"] > 0:
                    contrib_rate = (
                        persistence["sessions_with_contributions"] / persistence["sessions_created"]
                    ) * 100
                    details_parts.append(f"  • Save rate: {contrib_rate:.0f}%")

            # Issues
            if issues:
                details_parts.append("\n**🔴 Critical Issues**")
                details_parts.extend(f"  • {issue}" for issue in issues)

            # Warnings
            if warnings:
                details_parts.append("\n**🟡 Warnings**")
                details_parts.extend(f"  • {warning}" for warning in warnings)

            details = "\n".join(details_parts)

            return summary, details, status

    finally:
        conn.close()


def get_weekly_report() -> tuple[str, str, str]:
    """Generate weekly database summary report.

    Returns:
        Tuple of (summary, details, status)
    """
    conn = psycopg2.connect(DATABASE_URL)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get 7-day metrics
            cur.execute("""
                SELECT
                    COUNT(*) as total_sessions,
                    COUNT(DISTINCT user_id) as unique_users,
                    SUM(CASE WHEN created_at > NOW() - INTERVAL '7 days' THEN 1 ELSE 0 END) as sessions_7d
                FROM sessions
                WHERE created_at > NOW() - INTERVAL '30 days'
            """)
            sessions_data = cur.fetchone()

            # Get cost data (last 7 days)
            cur.execute("""
                SELECT
                    COUNT(*) as api_calls,
                    SUM(total_cost) as total_cost,
                    AVG(total_cost) as avg_cost,
                    SUM(input_tokens + output_tokens) as total_tokens
                FROM api_costs
                WHERE created_at > NOW() - INTERVAL '7 days'
            """)
            cost_data = cur.fetchone()

            # Get partition sizes
            cur.execute("""
                SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename IN ('api_costs', 'session_events', 'contributions', 'sessions')
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """)
            table_sizes = cur.fetchall()

            # Build summary
            summary = f"📈 Weekly Report: {sessions_data['sessions_7d']} sessions, {sessions_data['unique_users']} users"

            # Build details
            details_parts = []

            details_parts.append("**Usage (Last 7 Days)**")
            details_parts.append(f"  • Sessions: {sessions_data['sessions_7d']}")
            details_parts.append(f"  • Unique users: {sessions_data['unique_users']}")

            if cost_data["api_calls"]:
                details_parts.append("\n**API Costs (Last 7 Days)**")
                details_parts.append(f"  • Total calls: {cost_data['api_calls']:,}")
                details_parts.append(f"  • Total cost: ${cost_data['total_cost']:.2f}")
                details_parts.append(f"  • Avg cost/call: ${cost_data['avg_cost']:.4f}")
                details_parts.append(f"  • Total tokens: {cost_data['total_tokens']:,}")

            details_parts.append("\n**Database Size**")
            for table in table_sizes:
                details_parts.append(f"  • {table['tablename']}: {table['size']}")

            details = "\n".join(details_parts)

            return summary, details, "ok"

    finally:
        conn.close()


async def send_report(report_type: str):
    """Generate and send database report via ntfy.

    Args:
        report_type: "daily" or "weekly"
    """
    print(f"Generating {report_type} report...")

    if report_type == "daily":
        summary, details, status = get_daily_report()
    elif report_type == "weekly":
        summary, details, status = get_weekly_report()
    else:
        print(f"ERROR: Invalid report type: {report_type}")
        print("Usage: python send_database_report.py [daily|weekly]")
        sys.exit(1)

    print(f"\nSummary: {summary}")
    print(f"Status: {status}")
    print(f"\nDetails:\n{details}")

    # Send critical alerts separately
    if status == "critical":
        print("\n⚠️ Sending critical alert...")
        await notify_database_alert(
            alert_type="critical",
            title="Database Health Check Failed",
            message=f"{summary}\n\n{details[:500]}...",  # Truncate for alert
        )

    # Send regular report
    print(f"\n📤 Sending {report_type} report via ntfy...")
    priority = "default" if status == "ok" else "high"

    success = await notify_database_report(
        report_type=report_type, summary=summary, details=details, priority=priority
    )

    if success:
        print("✅ Report sent successfully!")
        sys.exit(0)
    else:
        print("❌ Failed to send report")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python send_database_report.py [daily|weekly]")
        sys.exit(1)

    report_type = sys.argv[1].lower()
    asyncio.run(send_report(report_type))
