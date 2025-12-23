"""Tests for session-level LLM rate limiter."""

import threading
import time
from unittest.mock import patch

from bo1.constants import LLMRateLimiterConfig
from bo1.llm.rate_limiter import SessionRateLimiter, get_session_rate_limiter


class TestRoundLimitEnforcement:
    """Test round limit enforcement (10 rounds max)."""

    def test_allows_rounds_within_limit(self) -> None:
        """Rounds 1-10 should be allowed."""
        limiter = SessionRateLimiter()

        for round_num in range(1, 11):  # 1-10
            allowed = limiter.check_session_round_limit("session-1", round_num)
            assert allowed, f"Round {round_num} should be allowed"

    def test_blocks_rounds_exceeding_limit(self) -> None:
        """Rounds > 10 should be blocked."""
        limiter = SessionRateLimiter()

        # Round 11 should be blocked
        allowed = limiter.check_session_round_limit("session-1", 11)
        assert not allowed

        # Round 15 should also be blocked
        allowed = limiter.check_session_round_limit("session-1", 15)
        assert not allowed

    def test_tracks_max_round_seen(self) -> None:
        """Should track the maximum round seen."""
        limiter = SessionRateLimiter()

        limiter.check_session_round_limit("session-1", 5)
        stats = limiter.get_session_stats("session-1")
        assert stats["max_round_seen"] == 5

        limiter.check_session_round_limit("session-1", 3)  # Lower round
        stats = limiter.get_session_stats("session-1")
        assert stats["max_round_seen"] == 5  # Still 5

        limiter.check_session_round_limit("session-1", 8)  # Higher round
        stats = limiter.get_session_stats("session-1")
        assert stats["max_round_seen"] == 8

    def test_separate_sessions_tracked_independently(self) -> None:
        """Different sessions should have independent round limits."""
        limiter = SessionRateLimiter()

        # Session 1 at round 10 (limit)
        allowed = limiter.check_session_round_limit("session-1", 10)
        assert allowed

        # Session 2 should also be allowed at round 10
        allowed = limiter.check_session_round_limit("session-2", 10)
        assert allowed

        # Session 1 at round 11 should be blocked
        allowed = limiter.check_session_round_limit("session-1", 11)
        assert not allowed

        # Session 2 should still be allowed at round 1
        allowed = limiter.check_session_round_limit("session-2", 1)
        assert allowed


class TestCallRateSlidingWindow:
    """Test call rate sliding window (6/min)."""

    def test_allows_calls_within_limit(self) -> None:
        """Up to 6 calls per minute should be allowed."""
        limiter = SessionRateLimiter()

        for i in range(6):
            allowed, wait = limiter.check_call_rate("session-1")
            assert allowed, f"Call {i + 1} should be allowed"
            assert wait == 0.0

    def test_blocks_exceeding_calls(self) -> None:
        """7th call within the window should be blocked."""
        limiter = SessionRateLimiter()

        # Make 6 allowed calls
        for _ in range(6):
            limiter.check_call_rate("session-1")

        # 7th call should be blocked with wait time
        allowed, wait = limiter.check_call_rate("session-1")
        assert not allowed
        assert wait > 0.0
        assert wait <= LLMRateLimiterConfig.WINDOW_SECONDS

    def test_sliding_window_expires_old_calls(self) -> None:
        """Old calls should expire and new ones should be allowed."""
        limiter = SessionRateLimiter()

        # Make 6 calls
        for _ in range(6):
            limiter.check_call_rate("session-1")

        # Manually expire old timestamps by modifying the state directly
        # This simulates time passing without patching time.time globally
        expired_time = time.time() - LLMRateLimiterConfig.WINDOW_SECONDS - 1
        with limiter._lock:
            state = limiter._sessions["session-1"]
            state.call_timestamps = [expired_time] * 6  # All calls are now "old"

        # New call should be allowed since all old calls expired
        allowed, wait = limiter.check_call_rate("session-1")
        assert allowed
        assert wait == 0.0

    def test_separate_sessions_tracked_independently(self) -> None:
        """Different sessions should have independent rate limits."""
        limiter = SessionRateLimiter()

        # Fill session 1's quota
        for _ in range(6):
            limiter.check_call_rate("session-1")

        # Session 2 should still be allowed
        allowed, wait = limiter.check_call_rate("session-2")
        assert allowed


class TestTTLCleanup:
    """Test TTL cleanup of stale entries."""

    def test_cleanup_removes_stale_sessions(self) -> None:
        """Stale sessions should be cleaned up."""
        limiter = SessionRateLimiter()

        # Create a session
        limiter.check_call_rate("session-1")
        assert "session-1" in limiter._sessions

        # Simulate time passing beyond cleanup threshold by directly modifying last_activity
        stale_threshold = (
            LLMRateLimiterConfig.WINDOW_SECONDS * LLMRateLimiterConfig.CLEANUP_MULTIPLIER
        )
        with limiter._lock:
            state = limiter._sessions["session-1"]
            # Set last_activity to far in the past
            state.last_activity = time.time() - stale_threshold - 10

        # Cleanup should remove the session
        removed = limiter.cleanup_stale_sessions()
        assert removed == 1
        assert "session-1" not in limiter._sessions

    def test_cleanup_preserves_active_sessions(self) -> None:
        """Recently active sessions should not be cleaned up."""
        limiter = SessionRateLimiter()

        # Create a session
        limiter.check_call_rate("session-1")

        # Cleanup should not remove the session (still active)
        removed = limiter.cleanup_stale_sessions()
        assert removed == 0
        assert "session-1" in limiter._sessions

    def test_maybe_cleanup_throttled(self) -> None:
        """maybe_cleanup should only run periodically."""
        limiter = SessionRateLimiter()

        # First call should set _last_cleanup
        limiter.maybe_cleanup()

        # Immediate second call should not trigger cleanup
        with patch.object(limiter, "cleanup_stale_sessions") as mock_cleanup:
            limiter.maybe_cleanup()
            mock_cleanup.assert_not_called()


class TestThreadSafety:
    """Test thread safety with concurrent access."""

    def test_concurrent_round_checks(self) -> None:
        """Concurrent round checks should be thread-safe."""
        limiter = SessionRateLimiter()
        results: list[bool] = []
        errors: list[Exception] = []

        def check_round(session_id: str, round_num: int) -> None:
            try:
                result = limiter.check_session_round_limit(session_id, round_num)
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=check_round, args=(f"session-{i}", i % 12)) for i in range(100)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 100

    def test_concurrent_call_rate_checks(self) -> None:
        """Concurrent call rate checks should be thread-safe."""
        limiter = SessionRateLimiter()
        results: list[tuple[bool, float]] = []
        errors: list[Exception] = []

        def check_rate(session_id: str) -> None:
            try:
                result = limiter.check_call_rate(session_id)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # All threads checking same session
        threads = [threading.Thread(target=check_rate, args=("session-1",)) for _ in range(100)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 100

        # At most 6 should be allowed (first 6 threads)
        allowed_count = sum(1 for allowed, _ in results if allowed)
        assert allowed_count <= 6


class TestDisabledMode:
    """Test disabled mode via env toggle."""

    def test_round_limit_bypassed_when_disabled(self) -> None:
        """Round limit should be bypassed when disabled."""
        limiter = SessionRateLimiter()

        with patch.object(LLMRateLimiterConfig, "is_enabled", return_value=False):
            # Round 100 should be allowed when disabled
            allowed = limiter.check_session_round_limit("session-1", 100)
            assert allowed

    def test_call_rate_bypassed_when_disabled(self) -> None:
        """Call rate limit should be bypassed when disabled."""
        limiter = SessionRateLimiter()

        with patch.object(LLMRateLimiterConfig, "is_enabled", return_value=False):
            # Should allow unlimited calls when disabled
            for _ in range(20):
                allowed, wait = limiter.check_call_rate("session-1")
                assert allowed
                assert wait == 0.0

    def test_stats_indicate_disabled(self) -> None:
        """Stats should indicate when rate limiter is disabled."""
        limiter = SessionRateLimiter()

        with patch.object(LLMRateLimiterConfig, "is_enabled", return_value=False):
            stats = limiter.get_session_stats("session-1")
            assert stats == {"enabled": False}


class TestSessionReset:
    """Test session state reset."""

    def test_reset_clears_session_state(self) -> None:
        """reset_session should clear all state for a session."""
        limiter = SessionRateLimiter()

        # Build up some state
        for _ in range(5):
            limiter.check_call_rate("session-1")
        limiter.check_session_round_limit("session-1", 8)

        stats = limiter.get_session_stats("session-1")
        assert stats["calls_in_window"] == 5
        assert stats["max_round_seen"] == 8

        # Reset the session
        limiter.reset_session("session-1")

        # State should be cleared
        stats = limiter.get_session_stats("session-1")
        assert stats["calls_in_window"] == 0
        assert stats["max_round_seen"] == 0

    def test_reset_nonexistent_session_safe(self) -> None:
        """Resetting a nonexistent session should not raise."""
        limiter = SessionRateLimiter()
        limiter.reset_session("nonexistent-session")  # Should not raise


class TestSingleton:
    """Test singleton accessor."""

    def test_get_session_rate_limiter_returns_same_instance(self) -> None:
        """get_session_rate_limiter should return the same instance."""
        instance1 = get_session_rate_limiter()
        instance2 = get_session_rate_limiter()
        assert instance1 is instance2

    def test_singleton_is_thread_safe(self) -> None:
        """Singleton creation should be thread-safe."""
        instances: list[SessionRateLimiter] = []

        def get_instance() -> None:
            instances.append(get_session_rate_limiter())

        threads = [threading.Thread(target=get_instance) for _ in range(50)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should be the same instance
        assert len({id(i) for i in instances}) == 1


class TestRecordCall:
    """Test record_call method."""

    def test_record_call_tracks_timestamp(self) -> None:
        """record_call should add a timestamp to the session."""
        limiter = SessionRateLimiter()

        # No calls yet
        stats = limiter.get_session_stats("session-1")
        assert stats["calls_in_window"] == 0

        # Record a call
        limiter.record_call("session-1")

        stats = limiter.get_session_stats("session-1")
        assert stats["calls_in_window"] == 1

    def test_record_call_respects_disabled_mode(self) -> None:
        """record_call should be a no-op when disabled."""
        limiter = SessionRateLimiter()

        with patch.object(LLMRateLimiterConfig, "is_enabled", return_value=False):
            limiter.record_call("session-1")

        # Session should not exist
        assert "session-1" not in limiter._sessions
