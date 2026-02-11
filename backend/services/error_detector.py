"""Error pattern detection service for AI ops self-healing.

Analyzes error logs and matches them against known error patterns.
Tracks error frequency and determines when remediation should be triggered.
"""

import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@dataclass
class ErrorPattern:
    """Database error pattern record."""

    id: int
    pattern_name: str
    pattern_regex: str
    error_type: str
    severity: str
    description: str | None
    enabled: bool
    threshold_count: int
    threshold_window_minutes: int
    cooldown_minutes: int
    created_at: datetime
    _compiled_regex: re.Pattern | None = field(default=None, repr=False)

    @property
    def regex(self) -> re.Pattern:
        """Get compiled regex pattern."""
        if self._compiled_regex is None:
            self._compiled_regex = re.compile(self.pattern_regex, re.IGNORECASE)
        return self._compiled_regex


@dataclass
class DetectedError:
    """Result of error pattern detection."""

    pattern: ErrorPattern
    matched_text: str
    timestamp: datetime
    source: str | None = None  # Log source (e.g., service name)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternFrequency:
    """Tracks error frequency for a pattern within its window."""

    pattern_id: int
    count: int
    window_start: datetime
    window_end: datetime
    last_remediation: datetime | None = None


class ErrorDetector:
    """Detects and tracks error patterns from log entries.

    Maintains in-memory sliding windows for frequency tracking.
    Queries database for pattern definitions.
    """

    def __init__(self) -> None:
        """Initialize detector with empty state."""
        # Pattern cache: pattern_id -> ErrorPattern
        self._patterns: dict[int, ErrorPattern] = {}
        self._patterns_loaded_at: float = 0
        self._pattern_cache_ttl_seconds: int = 60

        # Frequency tracking: pattern_id -> list of timestamps
        self._error_timestamps: dict[int, list[float]] = defaultdict(list)

        # Last remediation tracking: pattern_id -> timestamp
        self._last_remediation: dict[int, float] = {}

    def _should_reload_patterns(self) -> bool:
        """Check if patterns need to be reloaded from DB."""
        return time.time() - self._patterns_loaded_at > self._pattern_cache_ttl_seconds

    def _load_patterns(self) -> None:
        """Load enabled patterns from database."""
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, pattern_name, pattern_regex, error_type, severity,
                               description, enabled, threshold_count,
                               threshold_window_minutes, cooldown_minutes, created_at
                        FROM error_patterns
                        WHERE enabled = true
                        ORDER BY id
                        """
                    )
                    rows = cur.fetchall()

            self._patterns = {}
            for row in rows:
                pattern = ErrorPattern(
                    id=row[0],
                    pattern_name=row[1],
                    pattern_regex=row[2],
                    error_type=row[3],
                    severity=row[4],
                    description=row[5],
                    enabled=row[6],
                    threshold_count=row[7],
                    threshold_window_minutes=row[8],
                    cooldown_minutes=row[9],
                    created_at=row[10],
                )
                self._patterns[pattern.id] = pattern

            self._patterns_loaded_at = time.time()
            logger.debug(f"Loaded {len(self._patterns)} error patterns")

        except Exception as e:
            logger.error(f"Failed to load error patterns: {e}")
            # Keep existing patterns if reload fails
            if not self._patterns:
                self._patterns = {}

    def get_patterns(self) -> list[ErrorPattern]:
        """Get all enabled patterns, reloading if stale."""
        if self._should_reload_patterns():
            self._load_patterns()
        return list(self._patterns.values())

    def match_error_to_pattern(self, error_msg: str) -> ErrorPattern | None:
        """Match an error message to a known pattern.

        Args:
            error_msg: Error message string to match

        Returns:
            Matching ErrorPattern or None if no match
        """
        if self._should_reload_patterns():
            self._load_patterns()

        for pattern in self._patterns.values():
            try:
                if pattern.regex.search(error_msg):
                    return pattern
            except re.error as e:
                logger.warning(f"Invalid regex for pattern {pattern.pattern_name}: {e}")

        return None

    def detect_patterns(
        self,
        log_entries: list[str],
        source: str | None = None,
    ) -> list[DetectedError]:
        """Detect patterns in a batch of log entries.

        Args:
            log_entries: List of log/error message strings
            source: Optional source identifier (service name)

        Returns:
            List of DetectedError for each match
        """
        detected = []
        now = datetime.now(UTC)

        for entry in log_entries:
            pattern = self.match_error_to_pattern(entry)
            if pattern:
                detected.append(
                    DetectedError(
                        pattern=pattern,
                        matched_text=entry[:500],  # Truncate long messages
                        timestamp=now,
                        source=source,
                    )
                )
                # Record timestamp for frequency tracking
                self._record_error(pattern.id)

        return detected

    def _record_error(self, pattern_id: int) -> None:
        """Record an error occurrence for frequency tracking.

        Also increments the match_count in the database for persistent tracking.
        """
        self._error_timestamps[pattern_id].append(time.time())

        # Increment match_count in database (fire-and-forget, non-blocking)
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE error_patterns
                        SET match_count = match_count + 1,
                            last_match_at = now()
                        WHERE id = %s
                        """,
                        (pattern_id,),
                    )
        except Exception as e:
            # Log but don't fail - match tracking is non-critical
            logger.debug(f"Failed to increment match_count for pattern {pattern_id}: {e}")

    def _prune_old_timestamps(self, pattern_id: int, window_minutes: int) -> None:
        """Remove timestamps older than the window."""
        cutoff = time.time() - (window_minutes * 60)
        timestamps = self._error_timestamps[pattern_id]
        self._error_timestamps[pattern_id] = [t for t in timestamps if t > cutoff]

    def get_error_frequency(
        self,
        pattern_id: int,
        window_minutes: int | None = None,
    ) -> int:
        """Get error count for a pattern within its window.

        Args:
            pattern_id: Pattern ID to check
            window_minutes: Override window (uses pattern default if None)

        Returns:
            Number of errors in window
        """
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return 0

        window = window_minutes or pattern.threshold_window_minutes
        self._prune_old_timestamps(pattern_id, window)
        return len(self._error_timestamps[pattern_id])

    def should_trigger_remediation(self, pattern_id: int) -> bool:
        """Check if remediation should be triggered for a pattern.

        Considers:
        - Error count exceeds threshold
        - Cooldown period has elapsed since last remediation

        Args:
            pattern_id: Pattern ID to check

        Returns:
            True if remediation should be triggered
        """
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return False

        # Check frequency threshold
        count = self.get_error_frequency(pattern_id)
        if count < pattern.threshold_count:
            return False

        # Check cooldown
        last_remediation = self._last_remediation.get(pattern_id)
        if last_remediation:
            cooldown_elapsed = time.time() - last_remediation
            if cooldown_elapsed < (pattern.cooldown_minutes * 60):
                logger.debug(
                    f"Pattern {pattern.pattern_name} in cooldown "
                    f"({cooldown_elapsed:.0f}s / {pattern.cooldown_minutes * 60}s)"
                )
                return False

        return True

    def record_remediation(self, pattern_id: int) -> None:
        """Record that remediation was triggered for a pattern.

        This resets the error count and starts the cooldown timer.
        """
        self._last_remediation[pattern_id] = time.time()
        self._error_timestamps[pattern_id] = []

    def get_all_frequencies(self) -> dict[int, PatternFrequency]:
        """Get frequency data for all tracked patterns.

        Returns:
            Dict of pattern_id to PatternFrequency
        """
        result = {}
        now = datetime.now(UTC)

        for pattern_id, pattern in self._patterns.items():
            count = self.get_error_frequency(pattern_id)
            window_start = now - timedelta(minutes=pattern.threshold_window_minutes)
            last_rem_ts = self._last_remediation.get(pattern_id)
            last_rem = datetime.fromtimestamp(last_rem_ts, UTC) if last_rem_ts else None

            result[pattern_id] = PatternFrequency(
                pattern_id=pattern_id,
                count=count,
                window_start=window_start,
                window_end=now,
                last_remediation=last_rem,
            )

        return result


# Global instance


@lru_cache(maxsize=1)
def get_error_detector() -> ErrorDetector:
    """Get the global error detector instance."""
    return ErrorDetector()


def detect_patterns(
    log_entries: list[str],
    source: str | None = None,
) -> list[DetectedError]:
    """Detect patterns in log entries using global detector."""
    return get_error_detector().detect_patterns(log_entries, source)


def match_error_to_pattern(error_msg: str) -> ErrorPattern | None:
    """Match error message to pattern using global detector."""
    return get_error_detector().match_error_to_pattern(error_msg)


def get_error_frequency(pattern_id: int, window_minutes: int | None = None) -> int:
    """Get error frequency using global detector."""
    return get_error_detector().get_error_frequency(pattern_id, window_minutes)


def should_trigger_remediation(pattern_id: int) -> bool:
    """Check if remediation should trigger using global detector."""
    return get_error_detector().should_trigger_remediation(pattern_id)
