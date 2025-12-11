"""Tests for multi-provider circuit breaker functionality."""

from bo1.llm.circuit_breaker import (
    SERVICE_CONFIGS,
    CircuitState,
    get_active_llm_provider,
    get_service_circuit_breaker,
    is_provider_healthy,
    reset_service_circuit_breaker,
)


class TestServiceConfigs:
    """Test service configurations."""

    def test_openai_config_exists(self) -> None:
        """Test that OpenAI is configured in SERVICE_CONFIGS."""
        assert "openai" in SERVICE_CONFIGS
        assert "failure_threshold" in SERVICE_CONFIGS["openai"]
        assert "recovery_timeout" in SERVICE_CONFIGS["openai"]
        assert "success_threshold" in SERVICE_CONFIGS["openai"]


class TestGetActiveProvider:
    """Test get_active_llm_provider function."""

    def setup_method(self) -> None:
        """Reset circuit breakers before each test."""
        reset_service_circuit_breaker("anthropic")
        reset_service_circuit_breaker("openai")

    def test_returns_primary_when_healthy(self) -> None:
        """Test that primary provider is returned when healthy."""
        result = get_active_llm_provider(primary="anthropic", fallback="openai")
        assert result == "anthropic"

    def test_returns_fallback_when_primary_open(self) -> None:
        """Test fallback when primary circuit is open."""
        # Force primary circuit open
        breaker = get_service_circuit_breaker("anthropic")
        breaker.state = CircuitState.OPEN

        result = get_active_llm_provider(
            primary="anthropic",
            fallback="openai",
            fallback_enabled=True,
        )
        assert result == "openai"

    def test_returns_primary_when_fallback_disabled(self) -> None:
        """Test that primary is returned even when open if fallback disabled."""
        breaker = get_service_circuit_breaker("anthropic")
        breaker.state = CircuitState.OPEN

        result = get_active_llm_provider(
            primary="anthropic",
            fallback="openai",
            fallback_enabled=False,
        )
        assert result == "anthropic"

    def test_returns_primary_when_both_open(self) -> None:
        """Test that primary is returned when both circuits are open."""
        get_service_circuit_breaker("anthropic").state = CircuitState.OPEN
        get_service_circuit_breaker("openai").state = CircuitState.OPEN

        result = get_active_llm_provider(
            primary="anthropic",
            fallback="openai",
            fallback_enabled=True,
        )
        # Returns primary (will fail on call, but that's expected)
        assert result == "anthropic"

    def test_half_open_counts_as_healthy(self) -> None:
        """Test that half-open state is treated as healthy."""
        breaker = get_service_circuit_breaker("anthropic")
        breaker.state = CircuitState.HALF_OPEN

        result = get_active_llm_provider(primary="anthropic", fallback="openai")
        assert result == "anthropic"


class TestIsProviderHealthy:
    """Test is_provider_healthy function."""

    def setup_method(self) -> None:
        """Reset circuit breakers before each test."""
        reset_service_circuit_breaker("anthropic")
        reset_service_circuit_breaker("openai")

    def test_closed_is_healthy(self) -> None:
        """Test that closed circuit is healthy."""
        assert is_provider_healthy("anthropic") is True

    def test_half_open_is_healthy(self) -> None:
        """Test that half-open circuit is healthy."""
        breaker = get_service_circuit_breaker("anthropic")
        breaker.state = CircuitState.HALF_OPEN
        assert is_provider_healthy("anthropic") is True

    def test_open_is_not_healthy(self) -> None:
        """Test that open circuit is not healthy."""
        breaker = get_service_circuit_breaker("anthropic")
        breaker.state = CircuitState.OPEN
        assert is_provider_healthy("anthropic") is False
