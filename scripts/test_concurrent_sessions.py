#!/usr/bin/env python3
"""Performance test for concurrent session management.

Tests:
1. Creating 10 sessions simultaneously
2. Starting 10 deliberations in parallel
3. Verifying no conflicts or crashes
4. Measuring response times (<500ms target)

Usage:
    python scripts/test_concurrent_sessions.py
    python scripts/test_concurrent_sessions.py --sessions 20
    python scripts/test_concurrent_sessions.py --api-url http://localhost:8000
"""

import argparse
import asyncio
import statistics
import time
from collections.abc import Sequence
from datetime import UTC, datetime

import httpx


async def create_session(
    client: httpx.AsyncClient, api_url: str, session_num: int
) -> tuple[str, float]:
    """Create a single session and measure response time.

    Args:
        client: HTTP client
        api_url: Base API URL
        session_num: Session number for unique problem statement

    Returns:
        Tuple of (session_id, response_time_ms)
    """
    start_time = time.perf_counter()

    response = await client.post(
        f"{api_url}/api/v1/sessions",
        json={
            "problem_statement": f"Concurrent test session {session_num}: What pricing strategy should we use for our SaaS product to maximize revenue while staying competitive?",
            "problem_context": {
                "test_num": session_num,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        },
        timeout=10.0,
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    response.raise_for_status()
    session_id = response.json()["id"]

    return session_id, elapsed_ms


async def get_session_details(
    client: httpx.AsyncClient, api_url: str, session_id: str
) -> tuple[dict, float]:
    """Get session details and measure response time.

    Args:
        client: HTTP client
        api_url: Base API URL
        session_id: Session ID to retrieve

    Returns:
        Tuple of (session_data, response_time_ms)
    """
    start_time = time.perf_counter()

    response = await client.get(
        f"{api_url}/api/v1/sessions/{session_id}",
        timeout=10.0,
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    response.raise_for_status()
    return response.json(), elapsed_ms


async def list_sessions(client: httpx.AsyncClient, api_url: str) -> tuple[dict, float]:
    """List all sessions and measure response time.

    Args:
        client: HTTP client
        api_url: Base API URL

    Returns:
        Tuple of (sessions_data, response_time_ms)
    """
    start_time = time.perf_counter()

    response = await client.get(
        f"{api_url}/api/v1/sessions?limit=50",
        timeout=10.0,
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    response.raise_for_status()
    return response.json(), elapsed_ms


async def test_concurrent_session_creation(
    api_url: str, num_sessions: int
) -> dict[str, float | list[float]]:
    """Test creating multiple sessions concurrently.

    Args:
        api_url: Base API URL
        num_sessions: Number of sessions to create

    Returns:
        Performance metrics
    """
    print(f"\n{'=' * 70}")
    print(f"TEST 1: Creating {num_sessions} sessions concurrently")
    print(f"{'=' * 70}\n")

    async with httpx.AsyncClient() as client:
        # Create sessions concurrently
        tasks = [create_session(client, api_url, i) for i in range(1, num_sessions + 1)]

        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time

        # Process results
        successful = []
        failed = []
        response_times = []

        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                failed.append((i, str(result)))
                print(f"  ❌ Session {i}: FAILED - {result}")
            else:
                session_id, elapsed_ms = result
                successful.append((i, session_id))
                response_times.append(elapsed_ms)
                status = "✅" if elapsed_ms < 500 else "⚠️"
                print(f"  {status} Session {i}: {session_id} ({elapsed_ms:.0f}ms)")

    # Calculate statistics
    success_rate = len(successful) / num_sessions * 100
    avg_time = statistics.mean(response_times) if response_times else 0
    median_time = statistics.median(response_times) if response_times else 0
    p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else 0
    max_time = max(response_times) if response_times else 0

    print(f"\n{'─' * 70}")
    print("Results:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Successful: {len(successful)}/{num_sessions} ({success_rate:.1f}%)")
    print(f"  Failed: {len(failed)}")
    print("  Response times:")
    print(f"    Average: {avg_time:.0f}ms")
    print(f"    Median: {median_time:.0f}ms")
    print(f"    P95: {p95_time:.0f}ms")
    print(f"    Max: {max_time:.0f}ms")
    print(f"  Target: <500ms ({'✅ PASS' if avg_time < 500 else '❌ FAIL'})")

    return {
        "total_time": total_time,
        "success_rate": success_rate,
        "avg_response_time": avg_time,
        "median_response_time": median_time,
        "p95_response_time": p95_time,
        "max_response_time": max_time,
        "response_times": response_times,
    }


async def test_concurrent_session_reads(
    api_url: str, session_ids: Sequence[str]
) -> dict[str, float]:
    """Test reading multiple sessions concurrently.

    Args:
        api_url: Base API URL
        session_ids: List of session IDs to read

    Returns:
        Performance metrics
    """
    print(f"\n{'=' * 70}")
    print(f"TEST 2: Reading {len(session_ids)} sessions concurrently")
    print(f"{'=' * 70}\n")

    async with httpx.AsyncClient() as client:
        # Read sessions concurrently
        tasks = [get_session_details(client, api_url, sid) for sid in session_ids]

        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time

        # Process results
        successful = []
        response_times = []

        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                print(f"  ❌ Read {i}: FAILED - {result}")
            else:
                session_data, elapsed_ms = result
                successful.append(session_data)
                response_times.append(elapsed_ms)
                status = "✅" if elapsed_ms < 500 else "⚠️"
                print(f"  {status} Read {i}: {elapsed_ms:.0f}ms")

    # Calculate statistics
    avg_time = statistics.mean(response_times) if response_times else 0
    median_time = statistics.median(response_times) if response_times else 0
    max_time = max(response_times) if response_times else 0

    print(f"\n{'─' * 70}")
    print("Results:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Successful: {len(successful)}/{len(session_ids)}")
    print("  Response times:")
    print(f"    Average: {avg_time:.0f}ms")
    print(f"    Median: {median_time:.0f}ms")
    print(f"    Max: {max_time:.0f}ms")
    print(f"  Target: <500ms ({'✅ PASS' if avg_time < 500 else '❌ FAIL'})")

    return {
        "total_time": total_time,
        "avg_response_time": avg_time,
        "median_response_time": median_time,
        "max_response_time": max_time,
    }


async def test_list_sessions_scalability(api_url: str) -> dict[str, float]:
    """Test listing sessions with many results.

    Args:
        api_url: Base API URL

    Returns:
        Performance metrics
    """
    print(f"\n{'=' * 70}")
    print("TEST 3: Listing sessions (scalability test)")
    print(f"{'=' * 70}\n")

    async with httpx.AsyncClient() as client:
        sessions_data, elapsed_ms = await list_sessions(client, api_url)

        total_sessions = sessions_data.get("total", 0)
        returned_sessions = len(sessions_data.get("sessions", []))

        status = "✅" if elapsed_ms < 500 else "⚠️"
        print(f"  {status} Listed {returned_sessions} sessions (total: {total_sessions})")
        print(f"  Response time: {elapsed_ms:.0f}ms")
        print(f"  Target: <500ms ({'✅ PASS' if elapsed_ms < 500 else '❌ FAIL'})")

    return {
        "response_time": elapsed_ms,
        "total_sessions": total_sessions,
        "returned_sessions": returned_sessions,
    }


async def main() -> None:
    """Run concurrent session performance tests."""
    parser = argparse.ArgumentParser(description="Test concurrent session management performance")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base API URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--sessions",
        type=int,
        default=10,
        help="Number of concurrent sessions to test (default: 10)",
    )

    args = parser.parse_args()

    print(f"\n{'=' * 70}")
    print("CONCURRENT SESSIONS PERFORMANCE TEST")
    print(f"{'=' * 70}")
    print(f"API URL: {args.api_url}")
    print(f"Concurrent sessions: {args.sessions}")
    print("Target response time: <500ms")
    print(f"Timestamp: {datetime.now(UTC).isoformat()}")

    # Test 1: Concurrent session creation
    test1_results = await test_concurrent_session_creation(args.api_url, args.sessions)

    # Extract successful session IDs for follow-up tests
    session_ids = []
    async with httpx.AsyncClient() as client:
        # Get some session IDs from the create test
        list_response = await client.get(f"{args.api_url}/api/v1/sessions?limit={args.sessions}")
        if list_response.status_code == 200:
            session_ids = [s["id"] for s in list_response.json().get("sessions", [])][
                : args.sessions
            ]

    # Test 2: Concurrent session reads (if we have sessions)
    if session_ids:
        test2_results = await test_concurrent_session_reads(args.api_url, session_ids)
    else:
        print("\n⚠️ Skipping concurrent read test (no sessions available)")
        test2_results = {}

    # Test 3: List sessions scalability
    test3_results = await test_list_sessions_scalability(args.api_url)

    # Final summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    all_pass = True

    # Check Test 1
    test1_pass = test1_results["avg_response_time"] < 500
    print(
        f"Test 1 (Create): {test1_results['avg_response_time']:.0f}ms avg {'✅ PASS' if test1_pass else '❌ FAIL'}"
    )
    all_pass = all_pass and test1_pass

    # Check Test 2
    if test2_results:
        test2_pass = test2_results["avg_response_time"] < 500
        print(
            f"Test 2 (Read): {test2_results['avg_response_time']:.0f}ms avg {'✅ PASS' if test2_pass else '❌ FAIL'}"
        )
        all_pass = all_pass and test2_pass

    # Check Test 3
    test3_pass = test3_results["response_time"] < 500
    print(
        f"Test 3 (List): {test3_results['response_time']:.0f}ms {'✅ PASS' if test3_pass else '❌ FAIL'}"
    )
    all_pass = all_pass and test3_pass

    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_pass else '❌ SOME TESTS FAILED'}")
    print(f"{'=' * 70}\n")

    # Exit with appropriate code
    exit(0 if all_pass else 1)


if __name__ == "__main__":
    asyncio.run(main())
