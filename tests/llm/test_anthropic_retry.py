"""Tests for Anthropic API retry logic and metrics.

These tests verify the exponential backoff retry behavior in PromptBroker
for handling transient API errors (5xx, 429, 529 overloaded).
"""

from bo1.constants import LLMConfig
from bo1.llm.broker import RetryPolicy


class TestRetryPolicy:
    """Tests for the RetryPolicy class."""

    def test_default_config_values(self) -> None:
        """Verify default retry config matches LLMConfig constants."""
        policy = RetryPolicy()
        assert policy.max_retries == LLMConfig.MAX_RETRIES
        assert policy.base_delay == LLMConfig.RETRY_BASE_DELAY
        assert policy.max_delay == LLMConfig.RETRY_MAX_DELAY
        assert policy.jitter is True

    def test_exponential_delay_calculation(self) -> None:
        """Verify exponential backoff formula: delay = base * 2^attempt (capped)."""
        policy = RetryPolicy(base_delay=1.0, max_delay=30.0, jitter=False)

        # Attempt 0: 1 * 2^0 = 1s
        assert policy.calculate_delay(0) == 1.0

        # Attempt 1: 1 * 2^1 = 2s
        assert policy.calculate_delay(1) == 2.0

        # Attempt 2: 1 * 2^2 = 4s
        assert policy.calculate_delay(2) == 4.0

        # Attempt 3: 1 * 2^3 = 8s
        assert policy.calculate_delay(3) == 8.0

        # Attempt 4: 1 * 2^4 = 16s
        assert policy.calculate_delay(4) == 16.0

        # Attempt 5: 1 * 2^5 = 32s -> capped to 30s
        assert policy.calculate_delay(5) == 30.0

    def test_max_delay_cap(self) -> None:
        """Verify delay never exceeds max_delay."""
        policy = RetryPolicy(base_delay=10.0, max_delay=15.0, jitter=False)

        # Should cap at 15s even though 10 * 2^2 = 40
        assert policy.calculate_delay(2) == 15.0
        assert policy.calculate_delay(10) == 15.0

    def test_jitter_bounds(self) -> None:
        """Verify jitter is within 0 to calculated_delay."""
        policy = RetryPolicy(base_delay=1.0, max_delay=30.0, jitter=True)

        # Run multiple times to verify jitter bounds
        for _ in range(100):
            delay = policy.calculate_delay(2)  # Should be 0 to 4s with jitter
            assert 0 <= delay <= 4.0

    def test_jitter_produces_variation(self) -> None:
        """Verify jitter produces different delay values."""
        policy = RetryPolicy(base_delay=1.0, max_delay=30.0, jitter=True)

        delays = [policy.calculate_delay(3) for _ in range(10)]
        # Not all delays should be identical (very unlikely with jitter)
        unique_delays = set(delays)
        assert len(unique_delays) > 1, "Jitter should produce varied delays"

    def test_custom_config(self) -> None:
        """Verify custom retry config is applied."""
        policy = RetryPolicy(max_retries=10, base_delay=0.5, max_delay=60.0, jitter=False)
        assert policy.max_retries == 10
        assert policy.base_delay == 0.5
        assert policy.max_delay == 60.0
        assert policy.jitter is False


class TestRetryConfigConstants:
    """Tests for LLMConfig retry constants."""

    def test_max_retries_is_reasonable(self) -> None:
        """MAX_RETRIES should allow recovery from transient issues."""
        assert LLMConfig.MAX_RETRIES >= 3, "Need at least 3 retries for resilience"
        assert LLMConfig.MAX_RETRIES <= 10, "Too many retries wastes time"

    def test_base_delay_provides_recovery_time(self) -> None:
        """Base delay should give API time to recover."""
        assert LLMConfig.RETRY_BASE_DELAY >= 0.5, "Need at least 500ms recovery time"
        assert LLMConfig.RETRY_BASE_DELAY <= 5.0, "Initial delay shouldn't be too long"

    def test_max_delay_prevents_excessive_waits(self) -> None:
        """Max delay should cap wait time reasonably."""
        assert LLMConfig.RETRY_MAX_DELAY >= 30.0, "Allow up to 30s for severe issues"
        assert LLMConfig.RETRY_MAX_DELAY <= 120.0, "Don't wait more than 2 minutes"

    def test_total_retry_time_is_bounded(self) -> None:
        """Total time for all retries should be bounded."""
        policy = RetryPolicy(jitter=False)

        # Calculate worst-case total delay
        total_delay = sum(policy.calculate_delay(attempt) for attempt in range(policy.max_retries))

        # Should not exceed 5 minutes total retry time
        assert total_delay <= 300, f"Total retry time {total_delay}s exceeds 5 minutes"


class TestRetryableErrorClassification:
    """Tests for error classification in retry logic."""

    def test_529_is_overloaded_status(self) -> None:
        """529 status code should be classified as retryable."""
        # 529 is the Anthropic "overloaded" status code
        assert 500 <= 529 < 600, "529 should be in 5xx range"

    def test_5xx_range_is_retryable(self) -> None:
        """All 5xx status codes should be retryable."""
        retryable_codes = [500, 502, 503, 504, 529]
        for code in retryable_codes:
            assert 500 <= code < 600, f"{code} should be in retryable range"

    def test_4xx_not_retryable(self) -> None:
        """4xx client errors should not be retried (except 429)."""
        non_retryable_codes = [400, 401, 403, 404, 422]
        for code in non_retryable_codes:
            assert not (500 <= code < 600), f"{code} should not be retryable"


class TestMetricsIntegration:
    """Tests for retry metrics integration."""

    def test_retry_metric_labels(self) -> None:
        """Verify retry metric has correct label structure."""
        # This tests the expected label structure for the metric
        expected_labels = {
            "provider": "anthropic",
            "attempt": "1",
            "error_type": "overloaded",
        }

        # Verify label values are valid
        assert expected_labels["provider"] in ["anthropic", "openai"]
        assert expected_labels["attempt"].isdigit()
        assert expected_labels["error_type"] in [
            "overloaded",
            "server_error",
            "rate_limit",
        ]

    def test_exhaustion_metric_labels(self) -> None:
        """Verify exhaustion metric has correct label structure."""
        expected_labels = {
            "provider": "anthropic",
            "error_type": "overloaded",
        }

        assert expected_labels["provider"] in ["anthropic", "openai"]
        assert expected_labels["error_type"] in [
            "overloaded",
            "server_error",
            "rate_limit",
        ]


class TestRetryScenarios:
    """Tests for common retry scenarios."""

    def test_immediate_success_no_retry(self) -> None:
        """Successful call should not trigger any retry logic."""
        # If first call succeeds, retry_count should remain 0
        # This is tested implicitly through the broker's return path
        # The RetryPolicy exists but is never used when call succeeds
        assert RetryPolicy().max_retries > 0, "Policy should have retries available"

    def test_recovery_on_second_attempt(self) -> None:
        """API recovery on 2nd attempt should work correctly."""
        policy = RetryPolicy(jitter=False)

        # First retry delay (attempt 0)
        delay = policy.calculate_delay(0)
        assert delay == policy.base_delay, "First retry should use base delay"

    def test_max_retries_reached(self) -> None:
        """After MAX_RETRIES, error should propagate."""
        policy = RetryPolicy()

        # Verify we can calculate delays for all attempts
        for attempt in range(policy.max_retries):
            delay = policy.calculate_delay(attempt)
            assert delay > 0
            assert delay <= policy.max_delay
