"""Benchmark LangGraph (v2) implementation performance.

This script measures:
- Total execution time
- Per-phase latency
- Memory usage
- Cost per deliberation

Results will be documented for future v1 vs v2 comparison.
"""

import asyncio
import time
import tracemalloc
from typing import Any

from bo1.interfaces.console import run_console_deliberation
from bo1.models.problem import Problem


async def benchmark_deliberation(problem: Problem, max_rounds: int = 3) -> dict[str, Any]:
    """Benchmark a single deliberation.

    Args:
        problem: Problem to deliberate
        max_rounds: Maximum rounds

    Returns:
        Benchmark results
    """
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
    total_cost = state["metrics"]["total_cost"]
    phase_costs = state["metrics"]["phase_costs"]

    return {
        "total_time_seconds": total_time,
        "total_cost_dollars": total_cost,
        "peak_memory_mb": peak / 1024 / 1024,
        "phase_costs": phase_costs,
        "rounds": state["round_number"],
        "num_contributions": len(state["contributions"]),
        "num_personas": len(state["personas"]),
    }


async def run_benchmarks() -> None:
    """Run benchmark suite."""
    print("=== LangGraph (v2) Performance Benchmark ===\n")

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
            description="Should we expand to a new market?",
            context="Current revenue: $500K/year, considering international expansion",
        ),
    ]

    results = []

    for i, problem in enumerate(problems, 1):
        print(f"\n[{i}/{len(problems)}] Benchmarking: {problem.statement[:60]}...")

        try:
            result = await benchmark_deliberation(problem, max_rounds=3)
            results.append(result)

            print(f"  ✓ Time: {result['total_time_seconds']:.2f}s")
            print(f"  ✓ Cost: ${result['total_cost_dollars']:.4f}")
            print(f"  ✓ Memory: {result['peak_memory_mb']:.2f}MB")
            print(f"  ✓ Rounds: {result['rounds']}")
            print(f"  ✓ Contributions: {result['num_contributions']}")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({"error": str(e)})

    # Calculate averages
    print("\n=== Summary ===\n")

    valid_results = [r for r in results if "error" not in r]

    if valid_results:
        avg_time = sum(r["total_time_seconds"] for r in valid_results) / len(valid_results)
        avg_cost = sum(r["total_cost_dollars"] for r in valid_results) / len(valid_results)
        avg_memory = sum(r["peak_memory_mb"] for r in valid_results) / len(valid_results)

        print(f"Average Time: {avg_time:.2f}s")
        print(f"Average Cost: ${avg_cost:.4f}")
        print(f"Average Memory: {avg_memory:.2f}MB")
        print(f"\nSuccessful: {len(valid_results)}/{len(problems)}")
    else:
        print("No successful runs to average")

    # Save results
    import json
    from pathlib import Path

    output_dir = Path("zzz_project")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "WEEK4_BENCHMARK_RESULTS.json"

    with open(output_file, "w") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": results,
                "summary": {
                    "avg_time_seconds": avg_time if valid_results else None,
                    "avg_cost_dollars": avg_cost if valid_results else None,
                    "avg_memory_mb": avg_memory if valid_results else None,
                    "success_rate": len(valid_results) / len(problems) if problems else 0,
                },
            },
            f,
            indent=2,
        )

    print(f"\n✓ Results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
