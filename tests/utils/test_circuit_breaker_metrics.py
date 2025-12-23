"""Tests for circuit breaker Prometheus metrics."""

from backend.api.middleware.metrics import (
    bo1_circuit_breaker_state,
    bo1_circuit_breaker_state_labeled,
    record_circuit_breaker_state,
)


class TestCircuitBreakerMetrics:
    """Test circuit breaker gauge updates on state transitions."""

    def test_gauge_set_to_1_on_open(self) -> None:
        """Verify gauge set to 1 when circuit breaker opens."""
        record_circuit_breaker_state("anthropic", "open")

        # Check labeled gauge
        open_value = bo1_circuit_breaker_state_labeled.labels(
            provider="anthropic", state="open"
        )._value.get()
        assert open_value == 1

        # Other states should be 0
        closed_value = bo1_circuit_breaker_state_labeled.labels(
            provider="anthropic", state="closed"
        )._value.get()
        half_open_value = bo1_circuit_breaker_state_labeled.labels(
            provider="anthropic", state="half_open"
        )._value.get()
        assert closed_value == 0
        assert half_open_value == 0

    def test_gauge_set_on_half_open(self) -> None:
        """Verify gauge set correctly when circuit breaker is half_open."""
        record_circuit_breaker_state("openai", "half_open")

        half_open_value = bo1_circuit_breaker_state_labeled.labels(
            provider="openai", state="half_open"
        )._value.get()
        assert half_open_value == 1

        open_value = bo1_circuit_breaker_state_labeled.labels(
            provider="openai", state="open"
        )._value.get()
        closed_value = bo1_circuit_breaker_state_labeled.labels(
            provider="openai", state="closed"
        )._value.get()
        assert open_value == 0
        assert closed_value == 0

    def test_gauge_set_to_0_on_closed(self) -> None:
        """Verify all state gauges correct when circuit breaker is closed."""
        record_circuit_breaker_state("voyage", "closed")

        closed_value = bo1_circuit_breaker_state_labeled.labels(
            provider="voyage", state="closed"
        )._value.get()
        assert closed_value == 1

        open_value = bo1_circuit_breaker_state_labeled.labels(
            provider="voyage", state="open"
        )._value.get()
        half_open_value = bo1_circuit_breaker_state_labeled.labels(
            provider="voyage", state="half_open"
        )._value.get()
        assert open_value == 0
        assert half_open_value == 0

    def test_provider_label_propagated(self) -> None:
        """Verify provider label is correctly propagated to gauges."""
        # Set different states for different providers
        record_circuit_breaker_state("anthropic", "open")
        record_circuit_breaker_state("openai", "closed")
        record_circuit_breaker_state("voyage", "half_open")

        # Verify each provider has independent state
        assert (
            bo1_circuit_breaker_state_labeled.labels(
                provider="anthropic", state="open"
            )._value.get()
            == 1
        )
        assert (
            bo1_circuit_breaker_state_labeled.labels(provider="openai", state="closed")._value.get()
            == 1
        )
        assert (
            bo1_circuit_breaker_state_labeled.labels(
                provider="voyage", state="half_open"
            )._value.get()
            == 1
        )

        # Verify cross-provider states are 0
        assert (
            bo1_circuit_breaker_state_labeled.labels(
                provider="anthropic", state="closed"
            )._value.get()
            == 0
        )
        assert (
            bo1_circuit_breaker_state_labeled.labels(provider="openai", state="open")._value.get()
            == 0
        )

    def test_legacy_gauge_also_updated(self) -> None:
        """Verify legacy gauge with numeric state values is also updated."""
        record_circuit_breaker_state("anthropic", "open")
        legacy_value = bo1_circuit_breaker_state.labels(service="anthropic")._value.get()
        assert legacy_value == 2  # open = 2 in legacy gauge

        record_circuit_breaker_state("anthropic", "half_open")
        legacy_value = bo1_circuit_breaker_state.labels(service="anthropic")._value.get()
        assert legacy_value == 1  # half_open = 1 in legacy gauge

        record_circuit_breaker_state("anthropic", "closed")
        legacy_value = bo1_circuit_breaker_state.labels(service="anthropic")._value.get()
        assert legacy_value == 0  # closed = 0 in legacy gauge

    def test_state_transition_open_to_closed(self) -> None:
        """Verify gauge correctly transitions from open to closed."""
        # First set to open
        record_circuit_breaker_state("brave", "open")
        assert (
            bo1_circuit_breaker_state_labeled.labels(provider="brave", state="open")._value.get()
            == 1
        )

        # Then transition to closed
        record_circuit_breaker_state("brave", "closed")
        assert (
            bo1_circuit_breaker_state_labeled.labels(provider="brave", state="open")._value.get()
            == 0
        )
        assert (
            bo1_circuit_breaker_state_labeled.labels(provider="brave", state="closed")._value.get()
            == 1
        )

    def test_multiple_providers_independent(self) -> None:
        """Verify multiple providers have independent gauge values."""
        # Set anthropic to open, openai to closed
        record_circuit_breaker_state("anthropic", "open")
        record_circuit_breaker_state("openai", "closed")

        # Verify independence
        assert (
            bo1_circuit_breaker_state_labeled.labels(
                provider="anthropic", state="open"
            )._value.get()
            == 1
        )
        assert (
            bo1_circuit_breaker_state_labeled.labels(provider="openai", state="open")._value.get()
            == 0
        )

        # Change anthropic to closed, should not affect openai
        record_circuit_breaker_state("anthropic", "closed")
        assert (
            bo1_circuit_breaker_state_labeled.labels(
                provider="anthropic", state="closed"
            )._value.get()
            == 1
        )
        assert (
            bo1_circuit_breaker_state_labeled.labels(provider="openai", state="closed")._value.get()
            == 1
        )
