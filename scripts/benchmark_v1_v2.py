"""Benchmark v1 (sequential) vs v2 (LangGraph) implementation performance.

Note: v1 implementation has been fully migrated to v2 (LangGraph).
This script establishes baseline performance metrics for v2 and validates
that the migration maintains acceptable performance characteristics.

Measurements:
- Total execution time
- Per-phase latency
- Memory usage
- Cost per deliberation

Target: Document baseline performance for future optimization.
"""

import asyncio
import csv
import json
import time
import tracemalloc
from pathlib import Path
from typing import Any

from bo1.interfaces.console import run_console_deliberation
from bo1.models.problem import Problem


async def benchmark_deliberation(
    problem: Problem, max_rounds: int = 3, run_number: int = 1
) -> dict[str, Any]:
    """Benchmark a single deliberation.

    Args:
        problem: Problem to deliberate
        max_rounds: Maximum rounds
        run_number: Run identifier for tracking

    Returns:
        Benchmark results
    """
    print(f"  Run {run_number}: Starting...")

    # Start memory tracking
    tracemalloc.start()

    # Start timer
    start_time = time.time()

    # Run deliberation
    state = await run_console_deliberation(
        problem=problem, session_id=None, max_rounds=max_rounds, debug=False
    )

    # End timer
    end_time = time.time()

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Calculate metrics
    total_time = end_time - start_time

    # Handle both dict-like access and object attribute access for metrics
    if hasattr(state["metrics"], "total_cost"):
        # DeliberationMetrics object
        total_cost = state["metrics"].total_cost
        total_tokens = state["metrics"].total_tokens
        phase_costs = (
            state["metrics"].phase_costs if hasattr(state["metrics"], "phase_costs") else {}
        )
    else:
        # Dict-like access (fallback)
        total_cost = state["metrics"].get("total_cost", 0.0)
        total_tokens = state["metrics"].get("total_tokens", 0)
        phase_costs = state["metrics"].get("phase_costs", {})

    print(f"  Run {run_number}: Complete - {total_time:.2f}s, ${total_cost:.4f}")

    return {
        "run_number": run_number,
        "total_time_seconds": total_time,
        "total_cost_dollars": total_cost,
        "total_tokens": total_tokens,
        "peak_memory_mb": peak / 1024 / 1024,
        "current_memory_mb": current / 1024 / 1024,
        "phase_costs": phase_costs,
        "rounds": state["round_number"],
        "num_contributions": len(state["contributions"]),
        "num_personas": len(state["personas"]),
        "stop_reason": state.get("stop_reason", "N/A"),
    }


async def run_benchmarks(num_runs: int = 5) -> None:
    """Run benchmark suite comparing v1 (baseline) and v2 (LangGraph).

    Note: Since v1 has been fully migrated, we establish v2 baseline metrics.

    Args:
        num_runs: Number of runs per problem (default: 5)
    """
    print("=" * 80)
    print("Board of One - Performance Benchmark (v2 LangGraph Baseline)")
    print("=" * 80)
    print()
    print("Note: v1 implementation has been migrated to v2 (LangGraph).")
    print("This benchmark establishes baseline performance for v2.")
    print()

    # Test problems
    problems = [
        Problem(
            title="CRM Investment",
            description="Should we invest $10K in a new CRM system?",
            context="Budget: $10K available, currently using spreadsheets",
        ),
        Problem(
            title="Hiring Decision",
            description="Should we hire a full-time developer or use contractors?",
            context="Budget: $100K, need to scale engineering team",
        ),
        Problem(
            title="Market Expansion",
            description="Should we expand to European markets?",
            context="Current revenue: $500K/year, considering international expansion",
        ),
    ]

    all_results = []

    for i, problem in enumerate(problems, 1):
        print(f"\n[Problem {i}/{len(problems)}] {problem.title}")
        print(f"Description: {problem.description[:60]}...")
        print(f"Running {num_runs} benchmarks...")

        problem_results = []

        for run in range(1, num_runs + 1):
            try:
                result = await benchmark_deliberation(problem, max_rounds=3, run_number=run)
                result["problem_id"] = i
                result["problem_title"] = problem.title
                problem_results.append(result)
                all_results.append(result)

            except Exception as e:
                print(f"  Run {run}: ERROR - {e}")
                error_result = {
                    "run_number": run,
                    "problem_id": i,
                    "problem_title": problem.title,
                    "error": str(e),
                }
                problem_results.append(error_result)
                all_results.append(error_result)

        # Calculate statistics for this problem
        valid_results = [r for r in problem_results if "error" not in r]
        if valid_results:
            avg_time = sum(r["total_time_seconds"] for r in valid_results) / len(valid_results)
            avg_cost = sum(r["total_cost_dollars"] for r in valid_results) / len(valid_results)
            avg_memory = sum(r["peak_memory_mb"] for r in valid_results) / len(valid_results)

            print(f"\n  Summary for {problem.title}:")
            print(f"    Avg Time:   {avg_time:.2f}s")
            print(f"    Avg Cost:   ${avg_cost:.4f}")
            print(f"    Avg Memory: {avg_memory:.2f}MB")
            print(f"    Success:    {len(valid_results)}/{num_runs}")

    # Calculate overall statistics
    print("\n" + "=" * 80)
    print("Overall Summary")
    print("=" * 80)

    valid_results = [r for r in all_results if "error" not in r]

    if valid_results:
        avg_time = sum(r["total_time_seconds"] for r in valid_results) / len(valid_results)
        avg_cost = sum(r["total_cost_dollars"] for r in valid_results) / len(valid_results)
        avg_memory = sum(r["peak_memory_mb"] for r in valid_results) / len(valid_results)
        avg_tokens = sum(r["total_tokens"] for r in valid_results) / len(valid_results)

        min_time = min(r["total_time_seconds"] for r in valid_results)
        max_time = max(r["total_time_seconds"] for r in valid_results)

        print(f"\nAverage Time:     {avg_time:.2f}s (min: {min_time:.2f}s, max: {max_time:.2f}s)")
        print(f"Average Cost:     ${avg_cost:.4f}")
        print(f"Average Memory:   {avg_memory:.2f}MB")
        print(f"Average Tokens:   {avg_tokens:,.0f}")
        print(
            f"Success Rate:     {len(valid_results)}/{len(all_results)} ({len(valid_results) / len(all_results) * 100:.1f}%)"
        )

        # Performance targets
        print("\n" + "-" * 80)
        print("Performance Targets (for future optimization):")
        print("-" * 80)
        print(
            f"Time per deliberation:  Target <300s, Actual: {avg_time:.2f}s {'✓' if avg_time < 300 else '✗'}"
        )
        print(
            f"Cost per deliberation:  Target <$0.15, Actual: ${avg_cost:.4f} {'✓' if avg_cost < 0.15 else '✗'}"
        )
        print(
            f"Memory usage:           Target <500MB, Actual: {avg_memory:.2f}MB {'✓' if avg_memory < 500 else '✗'}"
        )

    else:
        print("\nNo successful runs to analyze.")

    # Save detailed results
    output_dir = Path("zzz_project")
    output_dir.mkdir(exist_ok=True)

    # JSON report
    json_file = output_dir / "WEEK4_BENCHMARK_RESULTS.json"
    with open(json_file, "w") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "version": "v2 (LangGraph)",
                "num_problems": len(problems),
                "runs_per_problem": num_runs,
                "results": all_results,
                "summary": {
                    "avg_time_seconds": avg_time if valid_results else None,
                    "avg_cost_dollars": avg_cost if valid_results else None,
                    "avg_memory_mb": avg_memory if valid_results else None,
                    "avg_tokens": avg_tokens if valid_results else None,
                    "success_rate": len(valid_results) / len(all_results) if all_results else 0,
                    "min_time_seconds": min_time if valid_results else None,
                    "max_time_seconds": max_time if valid_results else None,
                },
            },
            f,
            indent=2,
        )

    print(f"\n✓ JSON results saved to: {json_file}")

    # CSV report
    csv_file = output_dir / "WEEK4_BENCHMARK_RESULTS.csv"
    if valid_results:
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "problem_id",
                    "problem_title",
                    "run_number",
                    "total_time_seconds",
                    "total_cost_dollars",
                    "total_tokens",
                    "peak_memory_mb",
                    "rounds",
                    "num_contributions",
                    "num_personas",
                    "stop_reason",
                ],
            )
            writer.writeheader()
            for result in valid_results:
                writer.writerow(result)

        print(f"✓ CSV results saved to: {csv_file}")

    # Markdown report
    md_file = output_dir / "WEEK4_BENCHMARK_RESULTS.md"
    with open(md_file, "w") as f:
        f.write("# Week 4 Benchmark Results - v2 (LangGraph) Baseline\n\n")
        f.write(f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("**Version**: v2 (LangGraph)\n\n")
        f.write("## Overview\n\n")
        f.write(
            "This benchmark establishes baseline performance metrics for the v2 (LangGraph) implementation.\n"
        )
        f.write("v1 implementation has been fully migrated to v2.\n\n")

        f.write("## Summary Statistics\n\n")
        if valid_results:
            f.write(f"- **Average Time**: {avg_time:.2f}s\n")
            f.write(f"- **Average Cost**: ${avg_cost:.4f}\n")
            f.write(f"- **Average Memory**: {avg_memory:.2f}MB\n")
            f.write(f"- **Average Tokens**: {avg_tokens:,.0f}\n")
            f.write(
                f"- **Success Rate**: {len(valid_results)}/{len(all_results)} ({len(valid_results) / len(all_results) * 100:.1f}%)\n\n"
            )

            f.write("## Performance Targets\n\n")
            f.write("| Metric | Target | Actual | Status |\n")
            f.write("|--------|--------|--------|--------|\n")
            f.write(
                f"| Time per deliberation | <300s | {avg_time:.2f}s | {'✓ Pass' if avg_time < 300 else '✗ Fail'} |\n"
            )
            f.write(
                f"| Cost per deliberation | <$0.15 | ${avg_cost:.4f} | {'✓ Pass' if avg_cost < 0.15 else '✗ Fail'} |\n"
            )
            f.write(
                f"| Memory usage | <500MB | {avg_memory:.2f}MB | {'✓ Pass' if avg_memory < 500 else '✗ Fail'} |\n\n"
            )

            f.write("## Detailed Results\n\n")
            f.write(
                "| Problem | Run | Time (s) | Cost ($) | Memory (MB) | Rounds | Contributions |\n"
            )
            f.write(
                "|---------|-----|----------|----------|-------------|--------|---------------|\n"
            )
            for result in valid_results:
                f.write(
                    f"| {result['problem_title']} | {result['run_number']} | "
                    f"{result['total_time_seconds']:.2f} | ${result['total_cost_dollars']:.4f} | "
                    f"{result['peak_memory_mb']:.2f} | {result['rounds']} | "
                    f"{result['num_contributions']} |\n"
                )
        else:
            f.write("No successful runs to report.\n")

    print(f"✓ Markdown report saved to: {md_file}")

    print("\n" + "=" * 80)
    print("Benchmark complete!")
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark Board of One performance")
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of runs per problem (default: 5)",
    )
    args = parser.parse_args()

    asyncio.run(run_benchmarks(num_runs=args.runs))
