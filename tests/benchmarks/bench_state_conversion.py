"""Benchmark for state conversion caching performance.

This script measures the performance improvement from caching state conversions.
Expected results:
- First call (uncached): 1-5ms
- Subsequent calls (cached): <0.1ms
- Performance improvement: 10-50x faster
"""

import time

from bo1.graph.state import (
    clear_state_conversion_cache,
    create_initial_state,
    get_cache_stats,
    graph_state_to_deliberation_state,
)
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem
from bo1.models.state import ContributionMessage


def create_large_test_state() -> dict:
    """Create a realistic state with many personas and contributions."""
    from bo1.data import get_active_personas

    # Load all personas (45 experts)
    all_persona_data = get_active_personas()
    personas = [PersonaProfile(**p) for p in all_persona_data[:10]]  # Use 10 personas

    # Create problem
    problem = Problem(
        title="Complex Strategic Decision",
        description="Should we expand to international markets?",
        context="B2B SaaS company, $10M ARR, 50 employees, evaluating Europe expansion",
        sub_problems=[],
    )

    # Create state
    state = create_initial_state(
        session_id="benchmark-session",
        problem=problem,
        personas=personas,
        max_rounds=10,
    )

    # Add many contributions (simulate round 5)
    contributions = []
    for round_num in range(1, 6):
        for persona in personas[:5]:  # 5 active personas
            contribution = ContributionMessage(
                persona_code=persona.code,
                persona_name=persona.display_name,
                content=f"Round {round_num} contribution from {persona.display_name}. "
                * 20,  # Realistic length
                round_number=round_num,
                token_count=500,
                cost=0.01,
            )
            contributions.append(contribution)

    state["contributions"] = contributions
    state["round_number"] = 5

    return state


def benchmark_uncached_conversion() -> float:
    """Measure time for uncached conversion."""
    clear_state_conversion_cache()
    state = create_large_test_state()

    start = time.perf_counter()
    graph_state_to_deliberation_state(state)
    elapsed = time.perf_counter() - start

    return elapsed * 1000  # Convert to milliseconds


def benchmark_cached_conversion() -> float:
    """Measure time for cached conversion."""
    clear_state_conversion_cache()
    state = create_large_test_state()

    # First call to populate cache
    graph_state_to_deliberation_state(state)

    # Measure second call (cached)
    start = time.perf_counter()
    graph_state_to_deliberation_state(state)
    elapsed = time.perf_counter() - start

    return elapsed * 1000  # Convert to milliseconds


def benchmark_multiple_conversions(iterations: int = 10) -> dict:
    """Benchmark multiple conversions with caching."""
    clear_state_conversion_cache()
    state = create_large_test_state()

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        graph_state_to_deliberation_state(state)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)

    stats = get_cache_stats()

    return {
        "total_iterations": iterations,
        "first_call_ms": times[0],
        "avg_cached_ms": sum(times[1:]) / (iterations - 1) if iterations > 1 else 0,
        "min_cached_ms": min(times[1:]) if iterations > 1 else 0,
        "max_cached_ms": max(times[1:]) if iterations > 1 else 0,
        "cache_hits": stats["hits"],
        "cache_misses": stats["misses"],
        "hit_rate": stats["hit_rate"],
        "speedup": times[0] / (sum(times[1:]) / (iterations - 1)) if iterations > 1 else 1,
    }


def run_benchmark():
    """Run complete benchmark suite."""
    print("=" * 80)
    print("State Conversion Caching Performance Benchmark")
    print("=" * 80)
    print()

    # Test 1: Uncached conversion
    print("Test 1: Uncached Conversion (Cache Miss)")
    print("-" * 80)
    uncached_times = [benchmark_uncached_conversion() for _ in range(5)]
    avg_uncached = sum(uncached_times) / len(uncached_times)
    print(f"Average time: {avg_uncached:.3f}ms")
    print(f"Min time: {min(uncached_times):.3f}ms")
    print(f"Max time: {max(uncached_times):.3f}ms")
    print()

    # Test 2: Cached conversion
    print("Test 2: Cached Conversion (Cache Hit)")
    print("-" * 80)
    cached_times = [benchmark_cached_conversion() for _ in range(5)]
    avg_cached = sum(cached_times) / len(cached_times)
    print(f"Average time: {avg_cached:.3f}ms")
    print(f"Min time: {min(cached_times):.3f}ms")
    print(f"Max time: {max(cached_times):.3f}ms")
    print()

    # Test 3: Performance improvement
    print("Test 3: Performance Improvement")
    print("-" * 80)
    speedup = avg_uncached / avg_cached if avg_cached > 0 else float("inf")
    improvement_pct = ((avg_uncached - avg_cached) / avg_uncached) * 100
    print(f"Speedup: {speedup:.1f}x faster")
    print(f"Time saved: {improvement_pct:.1f}%")
    print(f"Absolute time saved: {avg_uncached - avg_cached:.3f}ms per conversion")
    print()

    # Test 4: Multiple conversions
    print("Test 4: Realistic Workload (10 Conversions)")
    print("-" * 80)
    results = benchmark_multiple_conversions(iterations=10)
    print(f"First call (uncached): {results['first_call_ms']:.3f}ms")
    print(f"Average cached call: {results['avg_cached_ms']:.3f}ms")
    print(f"Min cached call: {results['min_cached_ms']:.3f}ms")
    print(f"Max cached call: {results['max_cached_ms']:.3f}ms")
    print(f"Cache hits: {results['cache_hits']}")
    print(f"Cache misses: {results['cache_misses']}")
    print(f"Hit rate: {results['hit_rate']:.1%}")
    print(f"Overall speedup: {results['speedup']:.1f}x")
    print()

    # Test 5: Estimate impact on deliberation
    print("Test 5: Estimated Impact on Full Deliberation")
    print("-" * 80)
    # Typical deliberation: 11 conversions (initial + 5 rounds * 2 + vote)
    typical_conversions = 11
    time_without_cache = avg_uncached * typical_conversions
    time_with_cache = avg_uncached + (avg_cached * (typical_conversions - 1))
    total_saved = time_without_cache - time_with_cache
    print(f"Conversions per deliberation: {typical_conversions}")
    print(f"Time without cache: {time_without_cache:.1f}ms")
    print(f"Time with cache: {time_with_cache:.1f}ms")
    print(
        f"Total time saved: {total_saved:.1f}ms ({(total_saved / time_without_cache) * 100:.1f}%)"
    )
    print()

    print("=" * 80)
    print("Benchmark Complete")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  - Cache provides {speedup:.1f}x speedup for repeated conversions")
    print(f"  - Saves {total_saved:.1f}ms per typical deliberation")
    print(f"  - Hit rate: {results['hit_rate']:.1%}")
    print()


if __name__ == "__main__":
    run_benchmark()
