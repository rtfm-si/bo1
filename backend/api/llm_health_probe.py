"""LLM provider health probing with cached results.

Background probes Anthropic and OpenAI providers at configurable intervals,
caching results to avoid hammering providers on every health check.

Usage:
    probe = LLMHealthProbe()
    await probe.start()  # Start background refresh

    # Non-blocking reads from cache
    status = probe.get_cached_status("anthropic")

    # On shutdown
    await probe.stop()
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Literal

logger = logging.getLogger(__name__)

# Supported providers
ProviderName = Literal["anthropic", "openai"]

# Configuration from environment
LLM_HEALTH_PROBE_TTL_SECONDS = int(os.environ.get("LLM_HEALTH_PROBE_TTL_SECONDS", "30"))
LLM_HEALTH_PROBE_TIMEOUT_SECONDS = float(os.environ.get("LLM_HEALTH_PROBE_TIMEOUT_SECONDS", "5.0"))
LLM_HEALTH_PROBE_ENABLED = os.environ.get("LLM_HEALTH_PROBE_ENABLED", "true").lower() == "true"


@dataclass
class ProbeResult:
    """Result of a single provider probe."""

    healthy: bool
    latency_ms: float
    error: str | None
    timestamp: datetime

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "healthy": self.healthy,
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


class LLMHealthProbe:
    """Background health probe for LLM providers.

    Probes each provider at TTL intervals and caches results.
    Uses lightweight API calls (list models) to minimize costs.
    """

    def __init__(self, ttl_seconds: int = LLM_HEALTH_PROBE_TTL_SECONDS) -> None:
        """Initialize the health probe.

        Args:
            ttl_seconds: Cache TTL and probe interval (default from env)
        """
        self._ttl_seconds = ttl_seconds
        self._cache: dict[str, ProbeResult] = {}
        self._cache_lock = Lock()
        self._refresh_task: asyncio.Task | None = None
        self._shutdown_event: asyncio.Event | None = None
        self._providers: list[ProviderName] = ["anthropic", "openai"]

    async def probe_provider(self, provider: ProviderName) -> ProbeResult:
        """Probe a single provider with a lightweight API call.

        Uses list models endpoint which is fast and free on most providers.

        Args:
            provider: Provider name ("anthropic" or "openai")

        Returns:
            ProbeResult with health status, latency, and any error
        """
        from backend.api.middleware.metrics import (
            bo1_llm_probe_failures_total,
            bo1_llm_probe_latency_seconds,
            bo1_llm_provider_healthy,
        )
        from bo1.llm.circuit_breaker import get_circuit_breaker

        start_time = time.perf_counter()
        error_msg: str | None = None
        healthy = False

        try:
            # Check circuit breaker first - if open, skip actual probe
            cb = get_circuit_breaker(provider)
            if cb.is_open:
                error_msg = "circuit_breaker_open"
                return ProbeResult(
                    healthy=False,
                    latency_ms=0.0,
                    error=error_msg,
                    timestamp=datetime.now(UTC),
                )

            if provider == "anthropic":
                healthy, error_msg = await self._probe_anthropic()
            elif provider == "openai":
                healthy, error_msg = await self._probe_openai()
            else:
                error_msg = f"unknown_provider: {provider}"

        except TimeoutError:
            error_msg = "timeout"
            bo1_llm_probe_failures_total.labels(provider=provider, error_type="timeout").inc()
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)[:100]}"
            error_type = type(e).__name__.lower()
            bo1_llm_probe_failures_total.labels(provider=provider, error_type=error_type).inc()
            logger.warning(f"LLM probe failed for {provider}: {error_msg}")

        latency_ms = (time.perf_counter() - start_time) * 1000
        latency_seconds = latency_ms / 1000

        # Record metrics
        bo1_llm_probe_latency_seconds.labels(provider=provider).observe(latency_seconds)
        bo1_llm_provider_healthy.labels(provider=provider).set(1 if healthy else 0)

        result = ProbeResult(
            healthy=healthy,
            latency_ms=latency_ms,
            error=error_msg,
            timestamp=datetime.now(UTC),
        )

        # Update cache
        with self._cache_lock:
            self._cache[provider] = result

        return result

    async def _probe_anthropic(self) -> tuple[bool, str | None]:
        """Probe Anthropic API with minimal request.

        Returns:
            Tuple of (healthy, error_message)
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return False, "api_key_not_configured"

        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=api_key, timeout=LLM_HEALTH_PROBE_TIMEOUT_SECONDS)

            # Use count_tokens endpoint - lightweight and doesn't incur generation costs
            # Alternatively, could use models.list() if available
            async with asyncio.timeout(LLM_HEALTH_PROBE_TIMEOUT_SECONDS):
                # Simple message count - minimal tokens
                _ = await client.messages.count_tokens(
                    model="claude-3-haiku-20240307",
                    messages=[{"role": "user", "content": "hi"}],
                )
            return True, None

        except Exception as e:
            return False, f"{type(e).__name__}"

    async def _probe_openai(self) -> tuple[bool, str | None]:
        """Probe OpenAI API with minimal request.

        Returns:
            Tuple of (healthy, error_message)
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return False, "api_key_not_configured"

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key, timeout=LLM_HEALTH_PROBE_TIMEOUT_SECONDS)

            # List models is free and fast
            async with asyncio.timeout(LLM_HEALTH_PROBE_TIMEOUT_SECONDS):
                _ = await client.models.list()
            return True, None

        except Exception as e:
            return False, f"{type(e).__name__}"

    def get_cached_status(self, provider: ProviderName) -> ProbeResult | None:
        """Get cached probe result for a provider (non-blocking).

        Args:
            provider: Provider name

        Returns:
            Cached ProbeResult or None if not yet probed
        """
        with self._cache_lock:
            return self._cache.get(provider)

    def get_all_cached_statuses(self) -> dict[str, ProbeResult]:
        """Get all cached probe results (non-blocking).

        Returns:
            Dict mapping provider name to ProbeResult
        """
        with self._cache_lock:
            return dict(self._cache)

    def is_cache_stale(self, provider: ProviderName) -> bool:
        """Check if cached result is stale (older than TTL).

        Args:
            provider: Provider name

        Returns:
            True if stale or missing, False if fresh
        """
        with self._cache_lock:
            result = self._cache.get(provider)
            if result is None:
                return True
            age_seconds = (datetime.now(UTC) - result.timestamp).total_seconds()
            return age_seconds > self._ttl_seconds

    async def _refresh_loop(self) -> None:
        """Background refresh loop - probes each provider at intervals.

        Staggers probes to avoid simultaneous API calls.
        """
        logger.info(f"LLM health probe refresh loop started (TTL: {self._ttl_seconds}s)")

        while True:
            try:
                # Check shutdown
                if self._shutdown_event and self._shutdown_event.is_set():
                    logger.info("LLM health probe shutting down")
                    break

                # Probe each provider with stagger
                for i, provider in enumerate(self._providers):
                    try:
                        if self._shutdown_event and self._shutdown_event.is_set():
                            break

                        await self.probe_provider(provider)

                        # Stagger between providers (2s apart)
                        if i < len(self._providers) - 1:
                            await asyncio.sleep(2)

                    except Exception as e:
                        logger.warning(f"Probe error for {provider}: {e}")

                # Wait for next cycle
                if self._shutdown_event:
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self._ttl_seconds,
                        )
                        # Event was set, exit loop
                        break
                    except TimeoutError:
                        # Normal timeout, continue loop
                        pass
                else:
                    await asyncio.sleep(self._ttl_seconds)

            except asyncio.CancelledError:
                logger.info("LLM health probe refresh loop cancelled")
                break
            except Exception as e:
                logger.exception(f"Unexpected error in probe refresh loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    async def start(self) -> None:
        """Start background refresh task."""
        if not LLM_HEALTH_PROBE_ENABLED:
            logger.info("LLM health probe disabled via LLM_HEALTH_PROBE_ENABLED=false")
            return

        if self._refresh_task is not None:
            logger.warning("LLM health probe already started")
            return

        self._shutdown_event = asyncio.Event()

        # Initial probe of all providers
        for provider in self._providers:
            try:
                await self.probe_provider(provider)
            except Exception as e:
                logger.warning(f"Initial probe failed for {provider}: {e}")

        # Start background refresh
        self._refresh_task = asyncio.create_task(self._refresh_loop())
        logger.info("LLM health probe started")

    async def stop(self) -> None:
        """Stop background refresh task."""
        if self._shutdown_event:
            self._shutdown_event.set()

        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self._refresh_task = None

        logger.info("LLM health probe stopped")


# Singleton instance
_probe_instance: LLMHealthProbe | None = None


def get_llm_health_probe() -> LLMHealthProbe:
    """Get or create the singleton LLM health probe instance."""
    global _probe_instance
    if _probe_instance is None:
        _probe_instance = LLMHealthProbe()
    return _probe_instance
