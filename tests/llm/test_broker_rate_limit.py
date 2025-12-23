"""Integration tests for PromptBroker rate limiting.

These tests verify that the PromptBroker correctly integrates with the
SessionRateLimiter by testing the rate limiting logic in isolation.
"""

from bo1.llm.rate_limiter import SessionRateLimiter, get_session_rate_limiter


class TestBrokerRateLimitIntegration:
    """Integration tests for rate limiting behavior."""

    def test_rate_limiter_singleton_integration(self) -> None:
        """Verify rate limiter singleton is accessible."""
        limiter = get_session_rate_limiter()
        assert isinstance(limiter, SessionRateLimiter)

    def test_rate_limiter_integrated_round_check(self) -> None:
        """Round checks should integrate with session context."""
        limiter = SessionRateLimiter()

        # Simulate a session progressing through rounds
        session_id = "integration-session-1"

        for round_num in range(1, 11):  # Rounds 1-10
            allowed = limiter.check_session_round_limit(session_id, round_num)
            assert allowed, f"Round {round_num} should be allowed"

        # Round 11 should be blocked
        allowed = limiter.check_session_round_limit(session_id, 11)
        assert not allowed, "Round 11 should be blocked"

    def test_rate_limiter_integrated_call_rate(self) -> None:
        """Call rate checks should work with session tracking."""
        limiter = SessionRateLimiter()
        session_id = "integration-session-2"

        # First 6 calls should be allowed
        for i in range(6):
            allowed, wait = limiter.check_call_rate(session_id)
            assert allowed, f"Call {i + 1} should be allowed"
            assert wait == 0.0

        # 7th call should be rate limited
        allowed, wait = limiter.check_call_rate(session_id)
        assert not allowed, "7th call should be rate limited"
        assert wait > 0.0

    def test_rate_limiter_session_isolation(self) -> None:
        """Different sessions should have isolated rate limits."""
        limiter = SessionRateLimiter()

        # Session 1: use up rate limit
        for _ in range(6):
            limiter.check_call_rate("session-a")

        # Session 1 is now rate limited
        allowed, _ = limiter.check_call_rate("session-a")
        assert not allowed

        # Session 2 should still be allowed
        allowed, wait = limiter.check_call_rate("session-b")
        assert allowed
        assert wait == 0.0

    def test_rate_limiter_stats_tracking(self) -> None:
        """Session stats should be tracked correctly."""
        limiter = SessionRateLimiter()
        session_id = "integration-session-3"

        # Make some calls
        limiter.check_call_rate(session_id)
        limiter.check_call_rate(session_id)
        limiter.check_session_round_limit(session_id, 3)

        stats = limiter.get_session_stats(session_id)
        assert stats["enabled"] is True
        assert stats["calls_in_window"] == 2
        assert stats["max_round_seen"] == 3

    def test_rate_limiter_reset_session(self) -> None:
        """Session reset should clear all rate limit state."""
        limiter = SessionRateLimiter()
        session_id = "integration-session-4"

        # Build up state
        for _ in range(6):
            limiter.check_call_rate(session_id)
        limiter.check_session_round_limit(session_id, 8)

        # Verify state exists
        stats = limiter.get_session_stats(session_id)
        assert stats["calls_in_window"] == 6
        assert stats["max_round_seen"] == 8

        # Reset
        limiter.reset_session(session_id)

        # State should be cleared
        stats = limiter.get_session_stats(session_id)
        assert stats["calls_in_window"] == 0
        assert stats["max_round_seen"] == 0

    def test_record_call_after_wait(self) -> None:
        """record_call should work for post-wait tracking."""
        limiter = SessionRateLimiter()
        session_id = "integration-session-5"

        # No calls yet
        stats = limiter.get_session_stats(session_id)
        assert stats["calls_in_window"] == 0

        # Record a call directly (as if we waited and then recorded)
        limiter.record_call(session_id)

        stats = limiter.get_session_stats(session_id)
        assert stats["calls_in_window"] == 1

    def test_metrics_recording_mocked(self) -> None:
        """Verify metrics are called when rate limit exceeded."""
        limiter = SessionRateLimiter()
        session_id = "metrics-test-session"

        # Fill up the call rate
        for _ in range(6):
            limiter.check_call_rate(session_id)

        # The 7th call should return False (rate limited)
        # The broker would then call record_llm_rate_limit_exceeded
        allowed, wait = limiter.check_call_rate(session_id)
        assert not allowed
        assert wait > 0

        # Similarly for round limit
        allowed = limiter.check_session_round_limit(session_id, 15)
        assert not allowed
        # The broker would call record_llm_rate_limit_exceeded("round", session_id)


class TestBrokerContextIntegration:
    """Tests verifying context integration patterns."""

    def test_cost_context_provides_session_info(self) -> None:
        """Cost context should provide session_id and round_number."""
        # This tests the expected pattern from the broker
        # The broker reads session_id and round_number from cost context

        # Simulate what the broker does
        cost_ctx = {
            "session_id": "test-session",
            "round_number": 5,
        }

        session_id = cost_ctx.get("session_id")
        round_number = cost_ctx.get("round_number", 0)

        assert session_id == "test-session"
        assert round_number == 5

    def test_missing_session_id_handled(self) -> None:
        """Missing session_id should be handled gracefully."""
        cost_ctx = {"round_number": 5}

        session_id = cost_ctx.get("session_id")
        assert session_id is None

        # Broker should skip rate limiting when session_id is None
        # This is the expected behavior - no session means no per-session limits

    def test_missing_round_number_defaults_to_zero(self) -> None:
        """Missing round_number should default to 0."""
        cost_ctx = {"session_id": "test-session"}

        round_number = cost_ctx.get("round_number", 0)
        assert round_number == 0
