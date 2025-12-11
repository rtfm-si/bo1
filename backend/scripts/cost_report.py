#!/usr/bin/env python3
"""CLI script for generating cost reports.

Usage:
    python -m backend.scripts.cost_report --period day
    python -m backend.scripts.cost_report --period week --format csv
    python -m backend.scripts.cost_report --start-date 2025-01-01 --end-date 2025-01-31
    python -m backend.scripts.cost_report --top-users 10

Options:
    --period: Predefined period (day, week, month)
    --start-date: Custom start date (YYYY-MM-DD)
    --end-date: Custom end date (YYYY-MM-DD)
    --format: Output format (text, json, csv)
    --top-users: Number of top users to show (default: 10)
"""

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from io import StringIO

from backend.services import analytics


def format_currency(amount: float) -> str:
    """Format amount as USD currency."""
    return f"${amount:.2f}"


def generate_text_report(
    report: analytics.CostReport,
    start_date: date | None,
    end_date: date | None,
) -> str:
    """Generate human-readable text report."""
    lines = []
    lines.append("=" * 60)
    lines.append("COST REPORT")
    lines.append("=" * 60)

    # Date range
    if start_date and end_date:
        lines.append(f"Period: {start_date} to {end_date}")
    lines.append("")

    # Summary
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(
        f"  Today:      {format_currency(report.summary.today):>12} ({report.summary.session_count_today} sessions)"
    )
    lines.append(
        f"  This Week:  {format_currency(report.summary.this_week):>12} ({report.summary.session_count_week} sessions)"
    )
    lines.append(
        f"  This Month: {format_currency(report.summary.this_month):>12} ({report.summary.session_count_month} sessions)"
    )
    lines.append(
        f"  All Time:   {format_currency(report.summary.all_time):>12} ({report.summary.session_count_total} sessions)"
    )
    lines.append("")

    # Top users
    if report.by_user:
        lines.append("TOP USERS BY COST")
        lines.append("-" * 40)
        for i, user in enumerate(report.by_user, 1):
            email = user.email or user.user_id[:20]
            lines.append(
                f"  {i:2}. {email:<30} {format_currency(user.total_cost):>10} ({user.session_count} sessions)"
            )
        lines.append("")

    # Daily breakdown
    if report.by_day:
        lines.append("DAILY BREAKDOWN")
        lines.append("-" * 40)
        for day in report.by_day[-14:]:  # Last 14 days
            lines.append(
                f"  {day.date}: {format_currency(day.total_cost):>10} ({day.session_count} sessions)"
            )
        if len(report.by_day) > 14:
            lines.append(f"  ... ({len(report.by_day) - 14} more days)")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def generate_json_report(
    report: analytics.CostReport,
    start_date: date | None,
    end_date: date | None,
) -> str:
    """Generate JSON report."""
    data = {
        "period": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
        "summary": {
            "today": report.summary.today,
            "this_week": report.summary.this_week,
            "this_month": report.summary.this_month,
            "all_time": report.summary.all_time,
            "session_count_today": report.summary.session_count_today,
            "session_count_week": report.summary.session_count_week,
            "session_count_month": report.summary.session_count_month,
            "session_count_total": report.summary.session_count_total,
        },
        "by_user": [
            {
                "user_id": u.user_id,
                "email": u.email,
                "total_cost": u.total_cost,
                "session_count": u.session_count,
            }
            for u in report.by_user
        ],
        "by_day": [
            {
                "date": d.date.isoformat(),
                "total_cost": d.total_cost,
                "session_count": d.session_count,
            }
            for d in report.by_day
        ],
    }
    return json.dumps(data, indent=2)


def generate_csv_report(
    report: analytics.CostReport,
    start_date: date | None,
    end_date: date | None,
) -> str:
    """Generate CSV report (daily costs)."""
    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["date", "total_cost", "session_count"])

    # Data
    for day in report.by_day:
        writer.writerow([day.date.isoformat(), f"{day.total_cost:.4f}", day.session_count])

    return output.getvalue()


def parse_date(date_str: str) -> date:
    """Parse date string (YYYY-MM-DD)."""
    return date.fromisoformat(date_str)


def main() -> int:
    """Run cost report CLI."""
    parser = argparse.ArgumentParser(description="Generate cost reports")
    parser.add_argument(
        "--period",
        choices=["day", "week", "month"],
        help="Predefined period",
    )
    parser.add_argument(
        "--start-date",
        type=parse_date,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--top-users",
        type=int,
        default=10,
        help="Number of top users to show (default: 10)",
    )

    args = parser.parse_args()

    # Determine date range
    end_date = args.end_date or date.today()

    if args.period:
        if args.period == "day":
            start_date = end_date
        elif args.period == "week":
            start_date = end_date - timedelta(days=7)
        elif args.period == "month":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = None
    else:
        start_date = args.start_date

    # Generate report
    report = analytics.get_full_report(
        start_date=start_date,
        end_date=end_date,
        top_users=args.top_users,
    )

    # Output
    if args.format == "json":
        print(generate_json_report(report, start_date, end_date))
    elif args.format == "csv":
        print(generate_csv_report(report, start_date, end_date))
    else:
        print(generate_text_report(report, start_date, end_date))

    return 0


if __name__ == "__main__":
    sys.exit(main())
