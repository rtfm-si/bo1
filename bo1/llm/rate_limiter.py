"""Session-level LLM rate limiter for PromptBroker.

Provides sliding window rate limiting per session to prevent runaway
sessions from consuming excessive LLM resources.

Thread-safe implementation using stdlib threading.Lock.
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field

from bo1.constants import LLMRateLimiterConfig
from bo1.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SessionRateState:
    """Rate limiting state for a single session."""

    # Sliding window timestamps for call rate limiting
    call_timestamps: list[float] = field(default_factory=list)

    # Maximum round number seen for this session
    max_round_seen: int = 0

    # Last activity timestamp for cleanup
    last_activity: float = field(default_factory=time.time)


class SessionRateLimiter:
    """Thread-safe session-level rate limiter for LLM calls.

    Implements two limits:
    1. Round limit: Maximum rounds per session (hard cap)
    2. Call rate: Maximum calls per minute (sliding window)

    Example:
        >>> limiter = SessionRateLimiter()
        >>> # Check if session can proceed
        >>> allowed = limiter.check_session_round_limit("session-123", round_number=5)
        >>> # Check call rate (returns wait time if throttled)
        >>> allowed, wait = limiter.check_call_rate("session-123")
        >>> if not allowed:
        ...     await asyncio.sleep(wait)
    """

    def __init__(self) -> None:
        """Initialize the rate limiter."""
        self._lock = threading.Lock()
        self._sessions: dict[str, SessionRateState] = defaultdict(SessionRateState)
        self._last_cleanup = time.time()

    def check_session_round_limit(self, session_id: str, round_number: int) -> bool:
        """Check if session has exceeded the round limit.

        Args:
            session_id: Session identifier
            round_number: Current round number (1-indexed)

        Returns:
            True if allowed, False if round limit exceeded
        """
        if not LLMRateLimiterConfig.is_enabled():
            return True

        with self._lock:
            state = self._sessions[session_id]
            state.last_activity = time.time()

            # Track max round seen
            if round_number > state.max_round_seen:
                state.max_round_seen = round_number

            # Check limit
            if round_number > LLMRateLimiterConfig.MAX_ROUNDS_PER_SESSION:
                logger.warning(
                    f"Session {session_id[:8]} exceeded round limit: "
                    f"{round_number}/{LLMRateLimiterConfig.MAX_ROUNDS_PER_SESSION}"
                )
                return False

            return True

    def check_call_rate(self, session_id: str) -> tuple[bool, float]:
        """Check if session can make another LLM call.

        Uses sliding window algorithm to enforce calls per minute limit.

        Args:
            session_id: Session identifier

        Returns:
            Tuple of (allowed: bool, wait_seconds: float).
            If not allowed, wait_seconds indicates how long to wait.
        """
        if not LLMRateLimiterConfig.is_enabled():
            return True, 0.0

        now = time.time()
        window_start = now - LLMRateLimiterConfig.WINDOW_SECONDS

        with self._lock:
            state = self._sessions[session_id]
            state.last_activity = now

            # Cleanup old timestamps outside window
            state.call_timestamps = [ts for ts in state.call_timestamps if ts > window_start]

            # Check if under limit
            if len(state.call_timestamps) < LLMRateLimiterConfig.MAX_CALLS_PER_MINUTE:
                # Record this call
                state.call_timestamps.append(now)
                return True, 0.0

            # Calculate wait time until oldest call exits window
            oldest_timestamp = state.call_timestamps[0]
            wait_seconds = (oldest_timestamp + LLMRateLimiterConfig.WINDOW_SECONDS) - now

            logger.warning(
                f"Session {session_id[:8]} call rate limited: "
                f"{len(state.call_timestamps)}/{LLMRateLimiterConfig.MAX_CALLS_PER_MINUTE} "
                f"calls in {LLMRateLimiterConfig.WINDOW_SECONDS}s window, "
                f"wait {wait_seconds:.1f}s"
            )

            return False, max(0.0, wait_seconds)

    def record_call(self, session_id: str) -> None:
        """Record an LLM call for rate limiting.

        Use this when a call is made without prior check_call_rate call
        (e.g., after sleeping for the wait period).

        Args:
            session_id: Session identifier
        """
        if not LLMRateLimiterConfig.is_enabled():
            return

        now = time.time()
        with self._lock:
            state = self._sessions[session_id]
            state.last_activity = now
            state.call_timestamps.append(now)

    def cleanup_stale_sessions(self) -> int:
        """Remove stale session entries.

        Should be called periodically to prevent memory growth.

        Returns:
            Number of sessions cleaned up
        """
        if not LLMRateLimiterConfig.is_enabled():
            return 0

        now = time.time()
        stale_threshold = (
            LLMRateLimiterConfig.WINDOW_SECONDS * LLMRateLimiterConfig.CLEANUP_MULTIPLIER
        )

        with self._lock:
            stale_sessions = [
                sid
                for sid, state in self._sessions.items()
                if now - state.last_activity > stale_threshold
            ]

            for sid in stale_sessions:
                del self._sessions[sid]

            if stale_sessions:
                logger.debug(f"Cleaned up {len(stale_sessions)} stale rate limit entries")

            self._last_cleanup = now
            return len(stale_sessions)

    def maybe_cleanup(self) -> None:
        """Cleanup if enough time has passed since last cleanup.

        Safe to call frequently - only performs cleanup periodically.
        """
        if not LLMRateLimiterConfig.is_enabled():
            return

        now = time.time()
        cleanup_interval = (
            LLMRateLimiterConfig.WINDOW_SECONDS * LLMRateLimiterConfig.CLEANUP_MULTIPLIER
        )

        # Check without lock first (optimization)
        if now - self._last_cleanup < cleanup_interval:
            return

        self.cleanup_stale_sessions()

    def get_session_stats(self, session_id: str) -> dict[str, int | float]:
        """Get rate limiting stats for a session (for debugging/metrics).

        Args:
            session_id: Session identifier

        Returns:
            Dict with calls_in_window, max_round_seen, last_activity
        """
        if not LLMRateLimiterConfig.is_enabled():
            return {"enabled": False}

        now = time.time()
        window_start = now - LLMRateLimiterConfig.WINDOW_SECONDS

        with self._lock:
            if session_id not in self._sessions:
                return {"enabled": True, "calls_in_window": 0, "max_round_seen": 0}

            state = self._sessions[session_id]
            calls_in_window = len([ts for ts in state.call_timestamps if ts > window_start])

            return {
                "enabled": True,
                "calls_in_window": calls_in_window,
                "max_round_seen": state.max_round_seen,
                "last_activity": state.last_activity,
            }

    def reset_session(self, session_id: str) -> None:
        """Reset rate limiting state for a session.

        Use when retrying a session from checkpoint.

        Args:
            session_id: Session identifier
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.debug(f"Reset rate limit state for session {session_id[:8]}")


# Module-level singleton
_rate_limiter: SessionRateLimiter | None = None
_rate_limiter_lock = threading.Lock()


def get_session_rate_limiter() -> SessionRateLimiter:
    """Get the singleton rate limiter instance.

    Thread-safe lazy initialization.

    Returns:
        SessionRateLimiter singleton
    """
    global _rate_limiter
    if _rate_limiter is None:
        with _rate_limiter_lock:
            if _rate_limiter is None:
                _rate_limiter = SessionRateLimiter()
    return _rate_limiter
