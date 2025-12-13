"""Tests for error pattern detection service."""

import re
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.services.error_detector import (
    ErrorDetector,
    ErrorPattern,
    PatternFrequency,
    detect_patterns,
    get_error_detector,
    match_error_to_pattern,
)


@pytest.fixture
def sample_patterns() -> list[ErrorPattern]:
    """Create sample patterns for testing."""
    return [
        ErrorPattern(
            id=1,
            pattern_name="redis_connection_refused",
            pattern_regex=r"(Connection refused|ECONNREFUSED|redis\.exceptions\.ConnectionError)",
            error_type="redis",
            severity="critical",
            description="Redis unavailable",
            enabled=True,
            threshold_count=3,
            threshold_window_minutes=5,
            cooldown_minutes=5,
            created_at=datetime.now(UTC),
        ),
        ErrorPattern(
            id=2,
            pattern_name="llm_rate_limit",
            pattern_regex=r"(rate_limit|429|too_many_requests)",
            error_type="llm",
            severity="high",
            description="LLM rate limit hit",
            enabled=True,
            threshold_count=5,
            threshold_window_minutes=1,
            cooldown_minutes=2,
            created_at=datetime.now(UTC),
        ),
    ]


class TestErrorPattern:
    """Tests for ErrorPattern dataclass."""

    def test_regex_compilation(self, sample_patterns: list[ErrorPattern]) -> None:
        """Test regex property compiles and caches pattern."""
        pattern = sample_patterns[0]

        # First access should compile
        regex = pattern.regex
        assert isinstance(regex, re.Pattern)

        # Second access should return same compiled pattern
        regex2 = pattern.regex
        assert regex is regex2

    def test_regex_matches(self, sample_patterns: list[ErrorPattern]) -> None:
        """Test regex matches expected error messages."""
        redis_pattern = sample_patterns[0]

        assert redis_pattern.regex.search("Connection refused")
        assert redis_pattern.regex.search("ECONNREFUSED localhost:6379")
        assert redis_pattern.regex.search("redis.exceptions.ConnectionError: cannot connect")
        assert not redis_pattern.regex.search("Connection successful")


class TestErrorDetector:
    """Tests for ErrorDetector class."""

    @pytest.fixture
    def detector(self, sample_patterns: list[ErrorPattern]) -> ErrorDetector:
        """Create detector with mocked patterns."""
        detector = ErrorDetector()
        detector._patterns = {p.id: p for p in sample_patterns}
        detector._patterns_loaded_at = time.time()
        return detector

    def test_match_error_to_pattern_redis(self, detector: ErrorDetector) -> None:
        """Test matching Redis connection error."""
        pattern = detector.match_error_to_pattern("Connection refused to localhost:6379")
        assert pattern is not None
        assert pattern.pattern_name == "redis_connection_refused"

    def test_match_error_to_pattern_rate_limit(self, detector: ErrorDetector) -> None:
        """Test matching rate limit error."""
        pattern = detector.match_error_to_pattern("Error: rate_limit exceeded, retry after 60s")
        assert pattern is not None
        assert pattern.pattern_name == "llm_rate_limit"

    def test_match_error_no_match(self, detector: ErrorDetector) -> None:
        """Test no match for unknown error."""
        pattern = detector.match_error_to_pattern("Unknown error occurred")
        assert pattern is None

    def test_detect_patterns_batch(self, detector: ErrorDetector) -> None:
        """Test detecting patterns in batch of log entries."""
        log_entries = [
            "Connection refused to redis",
            "rate_limit exceeded",
            "Normal log message",
            "Connection refused again",
        ]

        detected = detector.detect_patterns(log_entries, source="test")

        assert len(detected) == 3
        assert detected[0].pattern.pattern_name == "redis_connection_refused"
        assert detected[1].pattern.pattern_name == "llm_rate_limit"
        assert detected[2].pattern.pattern_name == "redis_connection_refused"
        assert all(d.source == "test" for d in detected)

    def test_frequency_tracking(self, detector: ErrorDetector) -> None:
        """Test error frequency tracking."""
        pattern_id = 1

        # Record some errors
        detector._record_error(pattern_id)
        detector._record_error(pattern_id)
        detector._record_error(pattern_id)

        freq = detector.get_error_frequency(pattern_id)
        assert freq == 3

    def test_frequency_window_pruning(self, detector: ErrorDetector) -> None:
        """Test old timestamps are pruned from frequency window."""
        pattern_id = 1

        # Add old timestamp (6 minutes ago)
        old_time = time.time() - 360  # 6 minutes
        detector._error_timestamps[pattern_id].append(old_time)

        # Add recent timestamp
        detector._error_timestamps[pattern_id].append(time.time())

        # With 5 minute window, only recent should count
        freq = detector.get_error_frequency(pattern_id, window_minutes=5)
        assert freq == 1

    def test_should_trigger_remediation_below_threshold(self, detector: ErrorDetector) -> None:
        """Test remediation not triggered below threshold."""
        pattern_id = 1  # threshold_count = 3

        detector._record_error(pattern_id)
        detector._record_error(pattern_id)

        assert not detector.should_trigger_remediation(pattern_id)

    def test_should_trigger_remediation_at_threshold(self, detector: ErrorDetector) -> None:
        """Test remediation triggered at threshold."""
        pattern_id = 1  # threshold_count = 3

        detector._record_error(pattern_id)
        detector._record_error(pattern_id)
        detector._record_error(pattern_id)

        assert detector.should_trigger_remediation(pattern_id)

    def test_should_trigger_remediation_cooldown(self, detector: ErrorDetector) -> None:
        """Test remediation blocked during cooldown."""
        pattern_id = 1  # cooldown_minutes = 5

        # Record errors to exceed threshold
        for _ in range(3):
            detector._record_error(pattern_id)

        # First check should trigger
        assert detector.should_trigger_remediation(pattern_id)

        # Record remediation
        detector.record_remediation(pattern_id)

        # Add more errors
        for _ in range(3):
            detector._record_error(pattern_id)

        # Should be blocked by cooldown
        assert not detector.should_trigger_remediation(pattern_id)

    def test_record_remediation_resets_state(self, detector: ErrorDetector) -> None:
        """Test recording remediation resets error count."""
        pattern_id = 1

        detector._record_error(pattern_id)
        detector._record_error(pattern_id)
        assert detector.get_error_frequency(pattern_id) == 2

        detector.record_remediation(pattern_id)
        assert detector.get_error_frequency(pattern_id) == 0
        assert detector._last_remediation[pattern_id] > 0

    def test_get_all_frequencies(self, detector: ErrorDetector) -> None:
        """Test getting frequency data for all patterns."""
        detector._record_error(1)
        detector._record_error(1)
        detector._record_error(2)

        frequencies = detector.get_all_frequencies()

        assert len(frequencies) == 2
        assert frequencies[1].count == 2
        assert frequencies[2].count == 1
        assert isinstance(frequencies[1], PatternFrequency)


class TestGlobalFunctions:
    """Tests for module-level helper functions."""

    @patch("backend.services.error_detector._error_detector", None)
    def test_get_error_detector_creates_singleton(self) -> None:
        """Test singleton pattern for global detector."""
        detector1 = get_error_detector()
        detector2 = get_error_detector()
        assert detector1 is detector2

    @patch("backend.services.error_detector.get_error_detector")
    def test_detect_patterns_uses_global(self, mock_get: MagicMock) -> None:
        """Test detect_patterns uses global detector."""
        mock_detector = MagicMock()
        mock_detector.detect_patterns.return_value = []
        mock_get.return_value = mock_detector

        detect_patterns(["error 1", "error 2"], source="test")

        mock_detector.detect_patterns.assert_called_once_with(["error 1", "error 2"], "test")

    @patch("backend.services.error_detector.get_error_detector")
    def test_match_error_to_pattern_uses_global(self, mock_get: MagicMock) -> None:
        """Test match_error_to_pattern uses global detector."""
        mock_detector = MagicMock()
        mock_detector.match_error_to_pattern.return_value = None
        mock_get.return_value = mock_detector

        match_error_to_pattern("some error")

        mock_detector.match_error_to_pattern.assert_called_once_with("some error")
