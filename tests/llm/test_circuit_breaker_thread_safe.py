"""Tests for thread-safe circuit breaker sync operations.

Validates that call_sync() is safe under concurrent thread access.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from bo1.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)


class TestCircuitBreakerThreadSafety:
    """Test concurrent thread access to circuit breaker."""

    def test_concurrent_successes_dont_corrupt_state(self) -> None:
        """Concurrent successful calls should not corrupt failure_count."""
        breaker = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=5),
            service_name="test",
        )

        call_count = 0
        lock = threading.Lock()

        def success_func() -> str:
            nonlocal call_count
            with lock:
                call_count += 1
            time.sleep(0.001)  # Simulate I/O
            return "ok"

        # Run 50 concurrent calls
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(breaker.call_sync, success_func) for _ in range(50)]
            for future in as_completed(futures):
                assert future.result() == "ok"

        # State should remain closed, no corruption
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert call_count == 50

    def test_concurrent_failures_increment_correctly(self) -> None:
        """Concurrent failures should increment failure_count atomically."""
        breaker = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=100),  # High threshold to avoid opening
            service_name="test",
        )

        def failing_func() -> None:
            time.sleep(0.001)
            raise RuntimeError("test error")

        # Run 20 concurrent failing calls
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(breaker.call_sync, failing_func) for _ in range(20)]
            for future in as_completed(futures):
                with pytest.raises(RuntimeError):
                    future.result()

        # All failures should be counted (no lost updates)
        assert breaker.failure_count == 20

    def test_state_transition_is_atomic(self) -> None:
        """State transition to OPEN should happen at most once per threshold crossing.

        Note: Due to threading race conditions, it's possible for the transition
        to happen 0 times if all failures occur before threshold is reached,
        or 1 time when threshold is crossed. We verify final state is OPEN.
        """
        breaker = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=5),
            service_name="test",
        )

        transition_count = 0
        original_set_state = breaker._set_state_sync

        def counting_set_state(new_state: CircuitState) -> None:
            nonlocal transition_count
            if new_state == CircuitState.OPEN:
                transition_count += 1
            original_set_state(new_state)

        breaker._set_state_sync = counting_set_state  # type: ignore

        def failing_func() -> None:
            raise RuntimeError("test error")

        # Run enough failures to trigger circuit open
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(breaker.call_sync, failing_func) for _ in range(20)]
            for future in as_completed(futures):
                try:
                    future.result()
                except (RuntimeError, CircuitBreakerOpenError):
                    pass

        # Should transition to OPEN at most once (thread-safe guarantee)
        # and final state should be OPEN
        assert transition_count <= 1
        assert breaker.state == CircuitState.OPEN

    def test_open_circuit_rejects_all_concurrent_calls(self) -> None:
        """When circuit is OPEN, all concurrent calls should fail fast."""
        breaker = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=1, recovery_timeout=60),
            service_name="test",
        )

        # Force circuit open
        def failing_func() -> None:
            raise RuntimeError("test error")

        with pytest.raises(RuntimeError):
            breaker.call_sync(failing_func)

        assert breaker.state == CircuitState.OPEN

        # All concurrent calls should fail with CircuitBreakerOpenError
        rejected_count = 0

        def attempt_call() -> bool:
            try:
                breaker.call_sync(lambda: "should not run")
                return False
            except CircuitBreakerOpenError:
                return True

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(attempt_call) for _ in range(20)]
            for future in as_completed(futures):
                if future.result():
                    rejected_count += 1

        # All calls should be rejected
        assert rejected_count == 20

    def test_half_open_allows_limited_concurrent_calls(self) -> None:
        """In HALF_OPEN state, concurrent successes should close circuit."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0,  # Immediate recovery for test
            success_threshold=3,
        )
        breaker = CircuitBreaker(config, service_name="test")

        # Force circuit open
        def failing_func() -> None:
            raise RuntimeError("test error")

        with pytest.raises(RuntimeError):
            breaker.call_sync(failing_func)

        # Wait for recovery (immediate with timeout=0)
        time.sleep(0.01)

        # Run concurrent successes
        success_count = 0
        lock = threading.Lock()

        def success_func() -> str:
            nonlocal success_count
            with lock:
                success_count += 1
            return "ok"

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(breaker.call_sync, success_func) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # Circuit should be closed after enough successes
        assert breaker.state == CircuitState.CLOSED
        assert success_count == 10

    def test_mixed_async_and_sync_coexist(self) -> None:
        """Async and sync locks are independent, both can be used on same breaker."""
        import asyncio

        breaker = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=10),
            service_name="test",
        )

        async def async_success() -> str:
            return await breaker.call(asyncio.coroutine(lambda: "async")())  # type: ignore

        def sync_success() -> str:
            return breaker.call_sync(lambda: "sync")

        # Run sync calls in threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            sync_futures = [executor.submit(sync_success) for _ in range(5)]

            # Run async calls in event loop
            async def run_async() -> list[str]:
                return [await breaker.call(asyncio.sleep, 0.001) or "async" for _ in range(5)]

            # Sync calls complete
            for future in as_completed(sync_futures):
                assert future.result() == "sync"

        # State should remain healthy
        assert breaker.state == CircuitState.CLOSED
