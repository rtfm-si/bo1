#!/usr/bin/env python3
"""Performance test for SSE (Server-Sent Events) streaming scalability.

Tests:
1. Connecting 50 SSE clients simultaneously
2. Verifying all clients receive events
3. Measuring event latency (<100ms target)
4. Testing connection stability

Usage:
    python scripts/test_sse_scalability.py
    python scripts/test_sse_scalability.py --clients 100
    python scripts/test_sse_scalability.py --api-url http://localhost:8000
"""

import argparse
import asyncio
import statistics
import time
from datetime import UTC, datetime

import httpx


class SSEClient:
    """SSE client for tracking events and latency."""

    def __init__(self, client_id: int, session_id: str):
        """Initialize SSE client.

        Args:
            client_id: Unique client identifier
            session_id: Session ID to stream
        """
        self.client_id = client_id
        self.session_id = session_id
        self.events_received = []
        self.connection_time: float | None = None
        self.first_event_time: float | None = None
        self.last_event_time: float | None = None
        self.error: str | None = None


async def create_test_session(api_url: str) -> str:
    """Create a test session for SSE streaming.

    Args:
        api_url: Base API URL

    Returns:
        Session ID
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_url}/api/v1/sessions",
            json={
                "problem_statement": "SSE scalability test: What pricing strategy should we use for our B2B SaaS product?",
                "problem_context": {"test_type": "sse_scalability"},
            },
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()["id"]


async def sse_stream_client(
    client: httpx.AsyncClient,
    api_url: str,
    session_id: str,
    client_id: int,
    duration_seconds: int = 10,
) -> SSEClient:
    """Connect to SSE stream and collect events.

    Args:
        client: HTTP client
        api_url: Base API URL
        session_id: Session ID to stream
        client_id: Unique client identifier
        duration_seconds: How long to listen for events

    Returns:
        SSEClient with collected events
    """
    sse_client = SSEClient(client_id, session_id)

    try:
        connection_start = time.perf_counter()

        async with client.stream(
            "GET",
            f"{api_url}/api/v1/sessions/{session_id}/stream",
            timeout=httpx.Timeout(duration_seconds + 5.0, connect=5.0),
        ) as response:
            sse_client.connection_time = (time.perf_counter() - connection_start) * 1000

            if response.status_code != 200:
                sse_client.error = f"HTTP {response.status_code}"
                return sse_client

            # Read events for specified duration
            timeout_at = time.perf_counter() + duration_seconds

            async for line in response.aiter_lines():
                # Check timeout
                if time.perf_counter() >= timeout_at:
                    break

                # Parse SSE events
                if line.startswith("data:"):
                    event_time = time.perf_counter()
                    event_data = line[5:].strip()  # Remove "data:" prefix

                    # Track first event
                    if sse_client.first_event_time is None:
                        sse_client.first_event_time = (event_time - connection_start) * 1000

                    sse_client.last_event_time = event_time
                    sse_client.events_received.append({"data": event_data, "timestamp": event_time})

    except TimeoutError:
        sse_client.error = "Timeout"
    except Exception as e:
        sse_client.error = str(e)

    return sse_client


async def test_sse_concurrent_connections(api_url: str, num_clients: int, session_id: str) -> dict:
    """Test multiple SSE clients connecting simultaneously.

    Args:
        api_url: Base API URL
        num_clients: Number of concurrent clients
        session_id: Session ID to stream

    Returns:
        Performance metrics
    """
    print(f"\n{'=' * 70}")
    print(f"TEST 1: Connecting {num_clients} SSE clients concurrently")
    print(f"{'=' * 70}\n")

    async with httpx.AsyncClient() as client:
        # Create SSE client tasks
        tasks = [
            sse_stream_client(client, api_url, session_id, i, duration_seconds=5)
            for i in range(1, num_clients + 1)
        ]

        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time

        # Process results
        successful = []
        failed = []
        connection_times = []
        events_per_client = []

        for result in results:
            if isinstance(result, Exception):
                failed.append(str(result))
                print(f"  ❌ Client {len(failed)}: EXCEPTION - {result}")
            elif result.error:
                failed.append(result.error)
                print(f"  ❌ Client {result.client_id}: ERROR - {result.error}")
            else:
                successful.append(result)
                if result.connection_time:
                    connection_times.append(result.connection_time)
                events_per_client.append(len(result.events_received))

                status = "✅" if result.connection_time and result.connection_time < 1000 else "⚠️"
                print(
                    f"  {status} Client {result.client_id}: "
                    f"Connected in {result.connection_time:.0f}ms, "
                    f"received {len(result.events_received)} events"
                )

    # Calculate statistics
    success_rate = len(successful) / num_clients * 100
    avg_connection = statistics.mean(connection_times) if connection_times else 0
    avg_events = statistics.mean(events_per_client) if events_per_client else 0
    total_events = sum(events_per_client)

    print(f"\n{'─' * 70}")
    print("Results:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Successful: {len(successful)}/{num_clients} ({success_rate:.1f}%)")
    print(f"  Failed: {len(failed)}")
    print("  Connection times:")
    print(f"    Average: {avg_connection:.0f}ms")
    print(f"    Target: <1000ms ({'✅ PASS' if avg_connection < 1000 else '❌ FAIL'})")
    print("  Events:")
    print(f"    Total received: {total_events}")
    print(f"    Average per client: {avg_events:.1f}")

    return {
        "total_time": total_time,
        "success_rate": success_rate,
        "avg_connection_time": avg_connection,
        "total_events": total_events,
        "avg_events_per_client": avg_events,
        "successful_clients": successful,
        "connection_times": connection_times,
    }


async def test_sse_event_latency(api_url: str, session_id: str, num_clients: int = 5) -> dict:
    """Test event latency with multiple clients.

    Args:
        api_url: Base API URL
        session_id: Session ID to stream
        num_clients: Number of clients to test

    Returns:
        Performance metrics
    """
    print(f"\n{'=' * 70}")
    print(f"TEST 2: Testing event latency with {num_clients} clients")
    print(f"{'=' * 70}\n")

    async with httpx.AsyncClient() as client:
        # Start deliberation to generate events
        start_response = await client.post(
            f"{api_url}/api/v1/sessions/{session_id}/start",
            timeout=10.0,
        )

        if start_response.status_code != 202:
            print(f"  ❌ Failed to start session: HTTP {start_response.status_code}")
            return {"error": "Failed to start session"}

        # Connect SSE clients
        tasks = [
            sse_stream_client(client, api_url, session_id, i, duration_seconds=15)
            for i in range(1, num_clients + 1)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze event timing
        first_event_times = []
        all_events = []

        for result in results:
            if isinstance(result, Exception) or result.error:
                continue

            if result.first_event_time:
                first_event_times.append(result.first_event_time)

            all_events.extend(result.events_received)

        # Calculate latency
        avg_first_event = statistics.mean(first_event_times) if first_event_times else 0

        print("  Time to first event:")
        for i, latency in enumerate(first_event_times, 1):
            status = "✅" if latency < 100 else "⚠️"
            print(f"    {status} Client {i}: {latency:.0f}ms")

        print(f"\n{'─' * 70}")
        print("Results:")
        print(f"  Average time to first event: {avg_first_event:.0f}ms")
        print(f"  Total events across all clients: {len(all_events)}")
        print(f"  Target: <100ms ({'✅ PASS' if avg_first_event < 100 else '❌ FAIL'})")

        return {
            "avg_first_event_latency": avg_first_event,
            "total_events": len(all_events),
            "first_event_times": first_event_times,
        }


async def test_sse_connection_stability(api_url: str, num_clients: int = 10) -> dict:
    """Test SSE connection stability over time.

    Args:
        api_url: Base API URL
        num_clients: Number of concurrent clients

    Returns:
        Performance metrics
    """
    print(f"\n{'=' * 70}")
    print(f"TEST 3: Testing connection stability with {num_clients} clients")
    print(f"{'=' * 70}\n")

    # Create multiple sessions for testing
    async with httpx.AsyncClient() as client:
        # Create sessions
        session_ids = []
        for i in range(min(3, num_clients)):
            session_id = await create_test_session(api_url)
            session_ids.append(session_id)
            print(f"  Created session {i + 1}: {session_id}")

        # Connect clients to different sessions
        tasks = []
        for i in range(num_clients):
            session_id = session_ids[i % len(session_ids)]
            tasks.append(sse_stream_client(client, api_url, session_id, i + 1, duration_seconds=10))

        print(f"\n  Connecting {num_clients} clients...")
        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time

        # Count stable connections (no errors, received events)
        stable = [
            r
            for r in results
            if not isinstance(r, Exception) and not r.error and len(r.events_received) > 0
        ]
        unstable = num_clients - len(stable)

        stability_rate = len(stable) / num_clients * 100

        print(f"\n{'─' * 70}")
        print("Results:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Stable connections: {len(stable)}/{num_clients} ({stability_rate:.1f}%)")
        print(f"  Unstable: {unstable}")
        print(f"  Target: >95% stable ({'✅ PASS' if stability_rate >= 95 else '❌ FAIL'})")

        return {
            "total_time": total_time,
            "stability_rate": stability_rate,
            "stable_count": len(stable),
            "unstable_count": unstable,
        }


async def main() -> None:
    """Run SSE scalability performance tests."""
    parser = argparse.ArgumentParser(description="Test SSE streaming scalability")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base API URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--clients",
        type=int,
        default=50,
        help="Number of concurrent SSE clients to test (default: 50)",
    )

    args = parser.parse_args()

    print(f"\n{'=' * 70}")
    print("SSE STREAMING SCALABILITY TEST")
    print(f"{'=' * 70}")
    print(f"API URL: {args.api_url}")
    print(f"Concurrent clients: {args.clients}")
    print("Target connection time: <1000ms")
    print("Target event latency: <100ms")
    print(f"Timestamp: {datetime.now(UTC).isoformat()}")

    # Create a test session
    print("\nCreating test session...")
    session_id = await create_test_session(args.api_url)
    print(f"Session ID: {session_id}")

    # Test 1: Concurrent connections
    test1_results = await test_sse_concurrent_connections(args.api_url, args.clients, session_id)

    # Test 2: Event latency (with fewer clients to avoid overwhelming)
    test2_results = await test_sse_event_latency(
        args.api_url, session_id, num_clients=min(5, args.clients)
    )

    # Test 3: Connection stability
    test3_results = await test_sse_connection_stability(
        args.api_url, num_clients=min(10, args.clients)
    )

    # Final summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    all_pass = True

    # Check Test 1
    test1_pass = test1_results["success_rate"] >= 95
    print(
        f"Test 1 (Connections): {test1_results['success_rate']:.1f}% success {'✅ PASS' if test1_pass else '❌ FAIL'}"
    )
    all_pass = all_pass and test1_pass

    # Check Test 2
    if "error" not in test2_results:
        test2_pass = test2_results["avg_first_event_latency"] < 100
        print(
            f"Test 2 (Latency): {test2_results['avg_first_event_latency']:.0f}ms avg {'✅ PASS' if test2_pass else '❌ FAIL'}"
        )
        all_pass = all_pass and test2_pass

    # Check Test 3
    test3_pass = test3_results["stability_rate"] >= 95
    print(
        f"Test 3 (Stability): {test3_results['stability_rate']:.1f}% stable {'✅ PASS' if test3_pass else '❌ FAIL'}"
    )
    all_pass = all_pass and test3_pass

    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_pass else '❌ SOME TESTS FAILED'}")
    print(f"{'=' * 70}\n")

    # Exit with appropriate code
    exit(0 if all_pass else 1)


if __name__ == "__main__":
    asyncio.run(main())
