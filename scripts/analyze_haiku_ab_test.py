#!/usr/bin/env python3
"""Analyze Haiku A/B test results from api_costs table.

This script queries the api_costs table to compare cost and quality metrics
between test (round 3 Haiku) and control (round 3 Sonnet) groups.

Usage:
    # Analyze last 7 days (default)
    python scripts/analyze_haiku_ab_test.py

    # Analyze specific date range
    python scripts/analyze_haiku_ab_test.py --start 2025-01-01 --end 2025-01-07

    # Output as JSON
    python scripts/analyze_haiku_ab_test.py --format json

Environment:
    Requires DATABASE_URL or individual DB connection env vars.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_connection() -> Any:
    """Get database connection from environment."""
    import psycopg2

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)

    # Fallback to individual env vars
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "bo1"),
        user=os.getenv("DB_USER", "bo1"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def analyze_ab_test(
    start_date: datetime,
    end_date: datetime,
) -> dict[str, Any]:
    """Analyze A/B test results from api_costs table.

    Args:
        start_date: Start of analysis period
        end_date: End of analysis period

    Returns:
        Dictionary with analysis results including:
        - session_counts: Number of sessions per group
        - cost_metrics: Average/median/total costs per group
        - round_3_analysis: Specific analysis of round 3 costs
        - completion_rates: Session completion rates
        - recommendation: Action recommendation based on results
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Query to get session-level costs with metadata
        # Note: ab_group is stored in metadata JSONB field
        session_costs_query = """
        WITH session_costs AS (
            SELECT
                session_id,
                COALESCE(metadata->>'ab_group', 'none') as ab_group,
                SUM(cost) as total_cost,
                COUNT(*) as call_count,
                SUM(CASE WHEN metadata->>'round_number' = '3' THEN cost ELSE 0 END) as round_3_cost,
                SUM(CASE WHEN metadata->>'round_number' = '3' THEN 1 ELSE 0 END) as round_3_calls
            FROM api_costs
            WHERE created_at >= %s AND created_at < %s
                AND session_id IS NOT NULL
            GROUP BY session_id, COALESCE(metadata->>'ab_group', 'none')
        )
        SELECT
            ab_group,
            COUNT(*) as session_count,
            AVG(total_cost) as avg_cost,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_cost) as median_cost,
            SUM(total_cost) as total_cost,
            AVG(call_count) as avg_calls,
            AVG(round_3_cost) as avg_round_3_cost,
            AVG(round_3_calls) as avg_round_3_calls
        FROM session_costs
        GROUP BY ab_group
        ORDER BY ab_group
        """

        cur.execute(session_costs_query, (start_date, end_date))
        rows = cur.fetchall()

        # Parse results into groups
        groups: dict[str, dict[str, Any]] = {}
        for row in rows:
            ab_group = row[0]
            groups[ab_group] = {
                "session_count": row[1],
                "avg_cost": float(row[2]) if row[2] else 0,
                "median_cost": float(row[3]) if row[3] else 0,
                "total_cost": float(row[4]) if row[4] else 0,
                "avg_calls": float(row[5]) if row[5] else 0,
                "avg_round_3_cost": float(row[6]) if row[6] else 0,
                "avg_round_3_calls": float(row[7]) if row[7] else 0,
            }

        # Get completion rates (sessions with 'complete' status)
        completion_query = """
        SELECT
            COALESCE(ac.metadata->>'ab_group', 'none') as ab_group,
            COUNT(DISTINCT ac.session_id) as total_sessions,
            COUNT(DISTINCT CASE WHEN s.status = 'complete' THEN ac.session_id END) as completed
        FROM api_costs ac
        LEFT JOIN sessions s ON ac.session_id::uuid = s.id
        WHERE ac.created_at >= %s AND ac.created_at < %s
            AND ac.session_id IS NOT NULL
        GROUP BY COALESCE(ac.metadata->>'ab_group', 'none')
        """

        cur.execute(completion_query, (start_date, end_date))
        completion_rows = cur.fetchall()

        completion_rates: dict[str, float] = {}
        for row in completion_rows:
            ab_group = row[0]
            total = row[1]
            completed = row[2] or 0
            completion_rates[ab_group] = (completed / total * 100) if total > 0 else 0

        # Calculate savings and make recommendation
        test_data = groups.get("test", {})
        control_data = groups.get("control", {})

        savings_analysis = None
        recommendation = "insufficient_data"

        if test_data and control_data:
            test_sessions = test_data.get("session_count", 0)
            control_sessions = control_data.get("session_count", 0)

            if test_sessions >= 30 and control_sessions >= 30:
                # Sufficient data for analysis
                test_avg = test_data.get("avg_cost", 0)
                control_avg = control_data.get("avg_cost", 0)

                if control_avg > 0:
                    cost_diff_pct = ((control_avg - test_avg) / control_avg) * 100
                    savings_analysis = {
                        "test_avg_cost": test_avg,
                        "control_avg_cost": control_avg,
                        "cost_difference_pct": cost_diff_pct,
                        "round_3_savings": control_data.get("avg_round_3_cost", 0)
                        - test_data.get("avg_round_3_cost", 0),
                    }

                    # Compare completion rates
                    test_completion = completion_rates.get("test", 0)
                    control_completion = completion_rates.get("control", 0)
                    completion_diff = test_completion - control_completion

                    # Make recommendation
                    if cost_diff_pct > 3 and completion_diff >= -2:
                        recommendation = "expand_to_all"
                    elif cost_diff_pct > 0 and completion_diff >= -5:
                        recommendation = "continue_testing"
                    elif completion_diff < -5:
                        recommendation = "revert_to_control"
                    else:
                        recommendation = "no_significant_difference"
            else:
                recommendation = "insufficient_sample_size"

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "groups": groups,
            "completion_rates": completion_rates,
            "savings_analysis": savings_analysis,
            "recommendation": recommendation,
            "recommendation_explanation": {
                "expand_to_all": "Test shows >3% savings with minimal quality impact. Recommend setting HAIKU_ROUND_LIMIT=3 globally.",
                "continue_testing": "Positive trend but more data needed. Continue A/B test for another week.",
                "revert_to_control": "Completion rate dropped significantly. Haiku may not handle round 3 challenge phase well.",
                "no_significant_difference": "No significant cost difference. Keep current settings.",
                "insufficient_sample_size": "Need at least 30 sessions per group for statistical significance.",
                "insufficient_data": "No test/control data found. Ensure HAIKU_AB_TEST_ENABLED=true.",
            }.get(recommendation, "Unknown recommendation state."),
        }

    finally:
        cur.close()
        conn.close()


def format_table(results: dict[str, Any]) -> str:
    """Format results as a readable table."""
    lines = []
    lines.append("=" * 60)
    lines.append("HAIKU A/B TEST ANALYSIS")
    lines.append("=" * 60)
    lines.append(f"Period: {results['period']['start']} to {results['period']['end']}")
    lines.append("")

    # Group comparison table
    lines.append("GROUP COMPARISON:")
    lines.append("-" * 60)
    lines.append(
        f"{'Group':<12} {'Sessions':<10} {'Avg Cost':<12} {'Median':<12} {'Completion':<10}"
    )
    lines.append("-" * 60)

    for group, data in results.get("groups", {}).items():
        completion = results.get("completion_rates", {}).get(group, 0)
        lines.append(
            f"{group:<12} {data['session_count']:<10} "
            f"${data['avg_cost']:.4f}     ${data['median_cost']:.4f}     {completion:.1f}%"
        )

    lines.append("")

    # Savings analysis
    if results.get("savings_analysis"):
        lines.append("SAVINGS ANALYSIS:")
        lines.append("-" * 60)
        sa = results["savings_analysis"]
        lines.append(f"  Test avg cost:    ${sa['test_avg_cost']:.4f}")
        lines.append(f"  Control avg cost: ${sa['control_avg_cost']:.4f}")
        lines.append(f"  Cost difference:  {sa['cost_difference_pct']:.2f}%")
        lines.append(f"  Round 3 savings:  ${sa['round_3_savings']:.4f}")
        lines.append("")

    # Recommendation
    lines.append("RECOMMENDATION:")
    lines.append("-" * 60)
    lines.append(f"  {results['recommendation'].upper()}")
    lines.append(f"  {results['recommendation_explanation']}")
    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze Haiku A/B test results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--start",
        type=str,
        help="Start date (YYYY-MM-DD). Defaults to 7 days ago.",
    )
    parser.add_argument(
        "--end",
        type=str,
        help="End date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )

    args = parser.parse_args()

    # Parse dates
    end_date = datetime.now()
    if args.end:
        end_date = datetime.strptime(args.end, "%Y-%m-%d")

    start_date = end_date - timedelta(days=7)
    if args.start:
        start_date = datetime.strptime(args.start, "%Y-%m-%d")

    # Run analysis
    try:
        results = analyze_ab_test(start_date, end_date)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Output results
    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(format_table(results))


if __name__ == "__main__":
    main()
