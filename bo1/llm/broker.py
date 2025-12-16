"""Prompt Broker: Centralized LLM interaction layer with retry/rate-limit handling.

This module provides a unified interface for all LLM calls with:
- Retry logic with exponential backoff + jitter
- Rate limit handling (429 errors, Retry-After headers)
- Standardized LLMResponse format
- Comprehensive error handling
- Request tracking and observability
"""

import asyncio
import random
import time
import uuid
from typing import Any

from anthropic import APIError, RateLimitError
from pydantic import BaseModel, Field, field_validator

from bo1.config import get_settings, resolve_tier_to_model
from bo1.constants import LLMConfig
from bo1.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    get_active_llm_provider,
    get_service_circuit_breaker,
)
from bo1.llm.client import ClaudeClient, TokenUsage
from bo1.llm.context import get_cost_context
from bo1.llm.cost_tracker import CostTracker
from bo1.llm.response import LLMResponse
from bo1.utils.logging import get_logger, log_llm_call

# Import metrics for tracking LLM calls
try:
    from backend.api.middleware.metrics import (
        record_llm_cost,
        record_llm_request,
    )

    _metrics_available = True
except ImportError:
    # Metrics may not be available in all contexts (e.g., console-only mode)
    _metrics_available = False

    def record_llm_cost(model: str, provider: str, cost_cents: float) -> None:  # noqa: D103
        """No-op when metrics unavailable."""

    def record_llm_request(model: str, provider: str, success: bool = True) -> None:  # noqa: D103
        """No-op when metrics unavailable."""


logger = get_logger(__name__)


class RetryPolicy(BaseModel):
    """Configuration for retry behavior with exponential backoff.

    Examples:
        >>> policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=30.0)
        >>> delay = policy.calculate_delay(attempt=2)  # Returns ~4s with jitter
    """

    max_retries: int = Field(
        default=LLMConfig.MAX_RETRIES, description="Maximum number of retry attempts"
    )
    base_delay: float = Field(
        default=LLMConfig.RETRY_BASE_DELAY, description="Initial delay in seconds"
    )
    max_delay: float = Field(
        default=LLMConfig.RETRY_MAX_DELAY, description="Maximum delay in seconds"
    )
    jitter: bool = Field(default=True, description="Add random jitter to prevent thundering herd")

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given retry attempt with exponential backoff.

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds with optional jitter
        """
        # Exponential backoff: base_delay * 2^attempt
        delay: float = min(self.base_delay * (2**attempt), self.max_delay)

        # Add jitter: random value between 0 and delay
        if self.jitter:
            delay = random.uniform(0, delay)  # noqa: S311 - not cryptographic

        return delay


class PromptRequest(BaseModel):
    """Structured request for LLM call.

    This provides a clean interface for composing prompts without
    worrying about low-level API details.

    Examples:
        >>> request = PromptRequest(
        ...     system="You are a helpful assistant.",
        ...     user_message="What is 2+2?",
        ...     model="core",  # Provider-agnostic tier
        ...     prefill=None,
        ...     cache_system=False,
        ...     phase="test",
        ...     agent_type="TestAgent"
        ... )
    """

    system: str = Field(description="System prompt")
    user_message: str = Field(description="User message content")
    model: str = Field(
        default="core", description="Model tier ('core', 'fast') or alias ('sonnet', 'haiku')"
    )
    prefill: str | None = Field(default=None, description="Assistant prefill (e.g., '{' for JSON)")
    cache_system: bool = Field(default=False, description="Enable prompt caching for system prompt")
    temperature: float = Field(
        default=LLMConfig.DEFAULT_TEMPERATURE, description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=LLMConfig.DEFAULT_MAX_TOKENS, description="Maximum output tokens"
    )

    # Metadata for tracking
    phase: str | None = Field(default=None, description="Deliberation phase")
    agent_type: str | None = Field(default=None, description="Agent making the request")
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique request ID"
    )

    @field_validator("temperature", mode="before")
    @classmethod
    def clamp_temperature(cls, v: float) -> float:
        """Clamp temperature to valid 0-1 range (Anthropic API limit).

        Logs a warning if clamping occurs for graceful degradation.
        """
        if v is None:
            return LLMConfig.DEFAULT_TEMPERATURE
        clamped = max(LLMConfig.TEMPERATURE_MIN, min(v, LLMConfig.TEMPERATURE_MAX))
        if clamped != v:
            logger.warning(
                f"Temperature {v} clamped to {clamped} (valid range: "
                f"{LLMConfig.TEMPERATURE_MIN}-{LLMConfig.TEMPERATURE_MAX})"
            )
        return clamped


class PromptBroker:
    """Centralized broker for all LLM interactions.

    This class handles:
    - Retry logic with exponential backoff + jitter
    - Rate limit handling (429 errors, Retry-After headers)
    - Standardized LLMResponse format
    - Error handling and logging
    - Request tracking
    - Provider fallback (Anthropic → OpenAI)

    Examples:
        >>> broker = PromptBroker()
        >>> request = PromptRequest(
        ...     system="You are an expert.",
        ...     user_message="Analyze this problem.",
        ...     model="core",  # Provider-agnostic tier
        ...     prefill="{",
        ...     phase="decomposition",
        ...     agent_type="DecomposerAgent"
        ... )
        >>> response = await broker.call(request)
        >>> print(f"Cost: ${response.cost_total:.4f}")
    """

    def __init__(
        self,
        client: ClaudeClient | None = None,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        """Initialize the Prompt Broker.

        Args:
            client: ClaudeClient instance (if None, creates default)
            retry_policy: RetryPolicy config (if None, uses default)
            circuit_breaker: CircuitBreaker instance (if None, uses service-specific)
        """
        self.client = client or ClaudeClient()
        self._openai_client: Any = None  # Lazy-loaded
        self.retry_policy = retry_policy or RetryPolicy()
        # Use service-specific circuit breakers instead of single instance
        self._circuit_breaker_override = circuit_breaker

    def _get_circuit_breaker(self, provider: str) -> CircuitBreaker:
        """Get circuit breaker for provider."""
        if self._circuit_breaker_override:
            return self._circuit_breaker_override
        return get_service_circuit_breaker(provider)

    def _get_openai_client(self) -> Any:
        """Lazy-load OpenAI client."""
        if self._openai_client is None:
            from bo1.llm.openai_client import OpenAIClient

            self._openai_client = OpenAIClient()
        return self._openai_client

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Backward compatibility: return Anthropic circuit breaker."""
        return self._get_circuit_breaker("anthropic")

    async def call(self, request: PromptRequest) -> LLMResponse:
        """Execute an LLM call with retry/rate-limit handling and caching.

        Args:
            request: Structured prompt request

        Returns:
            LLMResponse with comprehensive metrics

        Raises:
            APIError: If all retries exhausted or non-retryable error
        """
        # Check cache first (fast path)
        from bo1.llm.cache import get_llm_cache

        cache = get_llm_cache()
        cached_response = await cache.get(request)
        if cached_response:
            logger.info(
                f"[{request.request_id}] Cache hit: "
                f"model={cached_response.model}, phase={request.phase}"
            )
            return cached_response

        start_time = time.time()
        retry_count = 0
        last_error: Exception | None = None

        # Determine active provider (handles fallback)
        settings = get_settings()
        provider = get_active_llm_provider(
            primary=settings.llm_primary_provider,
            fallback="openai" if settings.llm_primary_provider == "anthropic" else "anthropic",
            fallback_enabled=settings.llm_fallback_enabled,
        )

        # Resolve model tier/alias to full ID for the active provider
        model_id = resolve_tier_to_model(request.model, provider=provider)

        logger.info(
            f"[{request.request_id}] Starting LLM call: "
            f"provider={provider}, model={model_id}, phase={request.phase}, agent={request.agent_type}"
        )

        # Get cost tracking context from thread-local storage
        cost_ctx = get_cost_context()

        # Get circuit breaker for the active provider
        circuit_breaker = self._get_circuit_breaker(provider)

        for attempt in range(self.retry_policy.max_retries + 1):
            try:
                # Track cost with context manager (wraps the entire API call)
                with CostTracker.track_call(
                    provider=provider,
                    operation_type="completion",
                    model_name=model_id,
                    session_id=cost_ctx.get("session_id"),
                    user_id=cost_ctx.get("user_id"),
                    node_name=cost_ctx.get("node_name"),
                    phase=cost_ctx.get("phase") or request.phase,
                    persona_name=cost_ctx.get("persona_name"),
                    round_number=cost_ctx.get("round_number"),
                    sub_problem_index=cost_ctx.get("sub_problem_index"),
                    metadata={"prompt_name": cost_ctx.get("prompt_name", request.agent_type)},
                ) as cost_record:
                    # Make the LLM call with circuit breaker protection
                    async def _make_api_call() -> tuple[str, TokenUsage]:
                        if provider == "openai":
                            openai_client = self._get_openai_client()
                            # OpenAI client has its own TokenUsage class (compatible)
                            return await openai_client.call(  # type: ignore[no-any-return]
                                model=model_id,
                                messages=[{"role": "user", "content": request.user_message}],
                                system=request.system,
                                cache_system=request.cache_system,
                                temperature=request.temperature,
                                max_tokens=request.max_tokens,
                                prefill=request.prefill,
                            )
                        else:
                            return await self.client.call(
                                model=model_id,
                                messages=[{"role": "user", "content": request.user_message}],
                                system=request.system,
                                cache_system=request.cache_system,
                                temperature=request.temperature,
                                max_tokens=request.max_tokens,
                                prefill=request.prefill,
                            )

                    response_text, token_usage = await circuit_breaker.call(_make_api_call)

                    # Populate cost record with token usage from response
                    cost_record.input_tokens = token_usage.input_tokens
                    cost_record.output_tokens = token_usage.output_tokens
                    cost_record.cache_creation_tokens = token_usage.cache_creation_tokens
                    cost_record.cache_read_tokens = token_usage.cache_read_tokens
                    # Cost is automatically calculated and logged on context exit

                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)

                # Build LLMResponse
                llm_response = LLMResponse(
                    content=response_text,
                    model=model_id,
                    token_usage=token_usage,
                    duration_ms=duration_ms,
                    retry_count=retry_count,
                    request_id=request.request_id,
                    phase=request.phase,
                    agent_type=request.agent_type,
                )

                # Log structured metrics
                log_llm_call(
                    logger,
                    model=model_id,
                    prompt_tokens=token_usage.input_tokens,
                    completion_tokens=token_usage.output_tokens,
                    cost=llm_response.cost_total,
                    duration_ms=duration_ms,
                    phase=request.phase or "unknown",
                    agent=request.agent_type or "unknown",
                    request_id=request.request_id,
                    retry_count=retry_count,
                )

                # Track Prometheus metrics
                record_llm_request(model=model_id, provider=provider, success=True)
                # Convert cost to cents (cost_total is in dollars)
                cost_cents = llm_response.cost_total * 100 if llm_response.cost_total else 0
                record_llm_cost(model=model_id, provider=provider, cost_cents=cost_cents)

                # Cache the response for future use
                await cache.set(request, llm_response)

                return llm_response

            except RateLimitError as e:
                last_error = e
                retry_count += 1

                # Check if we have retries left
                if attempt >= self.retry_policy.max_retries:
                    logger.error(
                        f"[{request.request_id}] Rate limit exceeded, all retries exhausted: {e}"
                    )
                    record_llm_request(model=model_id, provider=provider, success=False)
                    raise

                # Extract Retry-After header if present
                retry_after = self._extract_retry_after(e)
                if retry_after:
                    delay = retry_after
                    logger.warning(
                        f"[{request.request_id}] Rate limited (429), "
                        f"respecting Retry-After: {delay:.1f}s"
                    )
                else:
                    # Use exponential backoff with jitter
                    delay = self.retry_policy.calculate_delay(attempt)
                    logger.warning(
                        f"[{request.request_id}] Rate limited (429), "
                        f"retry {retry_count}/{self.retry_policy.max_retries} "
                        f"after {delay:.1f}s"
                    )

                await asyncio.sleep(delay)

            except APIError as e:
                # Check if error is retryable (5xx errors)
                if self._is_retryable(e) and attempt < self.retry_policy.max_retries:
                    last_error = e
                    retry_count += 1
                    delay = self.retry_policy.calculate_delay(attempt)

                    logger.warning(
                        f"[{request.request_id}] API error (retryable), "
                        f"retry {retry_count}/{self.retry_policy.max_retries} "
                        f"after {delay:.1f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    # Non-retryable error or exhausted retries
                    logger.error(f"[{request.request_id}] API error (non-retryable): {e}")
                    record_llm_request(model=model_id, provider=provider, success=False)
                    raise

            except CircuitBreakerOpenError as e:
                # Circuit breaker is open - API is experiencing issues
                logger.error(
                    f"[{request.request_id}] Circuit breaker OPEN - "
                    f"API unavailable, skipping retry: {e}"
                )
                record_llm_request(model=model_id, provider=provider, success=False)
                # Re-raise as RuntimeError to avoid retry loop
                raise RuntimeError(
                    "Service temporarily unavailable due to repeated failures. Please try again later."
                ) from e

            except Exception as e:
                # Unexpected error, don't retry
                logger.error(f"[{request.request_id}] Unexpected error: {e}")
                record_llm_request(model=model_id, provider=provider, success=False)
                raise

        # Should never reach here, but just in case
        logger.error(f"[{request.request_id}] All retries exhausted")
        record_llm_request(model=model_id, provider=provider, success=False)
        raise last_error or RuntimeError("All retries exhausted with no error captured")

    def _extract_retry_after(self, error: RateLimitError) -> float | None:
        """Extract Retry-After value from rate limit error.

        Args:
            error: RateLimitError from Anthropic API

        Returns:
            Delay in seconds, or None if not present
        """
        # Try to extract from error response headers
        # This is a best-effort approach since the error structure may vary
        try:
            if hasattr(error, "response") and hasattr(error.response, "headers"):
                retry_after = error.response.headers.get("retry-after")
                if retry_after:
                    return float(retry_after)
        except (AttributeError, ValueError, TypeError):
            pass

        return None

    def _is_retryable(self, error: APIError) -> bool:
        """Check if an API error is retryable.

        Args:
            error: APIError from Anthropic API

        Returns:
            True if error is retryable (5xx), False otherwise
        """
        # Retry on 5xx server errors
        if hasattr(error, "status_code"):
            status_code: int = error.status_code
            return 500 <= status_code < 600

        # If we can't determine status code, don't retry
        return False


def get_model_for_phase(phase: str, round_number: int = 0) -> str:
    """Select appropriate model tier for task based on phase and round number.

    Uses 'fast' tier for supporting tasks and early rounds to reduce cost and latency,
    while using 'core' tier for critical synthesis and later rounds.

    Args:
        phase: The deliberation phase
        round_number: The current round number (for contribution phase)

    Returns:
        Model tier ('fast' or 'core') - provider-agnostic

    Examples:
        >>> get_model_for_phase("convergence_check")
        'fast'
        >>> get_model_for_phase("contribution", round_number=1)
        'fast'
        >>> get_model_for_phase("contribution", round_number=3)
        'core'
        >>> get_model_for_phase("synthesis")
        'core'
    """
    # Fast phases use 'fast' tier (cheaper model)
    if phase in ["convergence_check", "drift_check", "format_validation"]:
        return "fast"

    # Early exploration rounds can use 'fast' tier (rounds 1-2)
    if phase == "contribution" and round_number <= 2:
        return "fast"

    # Everything else uses 'core' tier (critical synthesis, later rounds, voting)
    return "core"


class RequestTracker:
    """Track and log LLM requests for observability.

    This class provides a simple way to track all requests made during
    a deliberation session for debugging and analysis.

    Examples:
        >>> tracker = RequestTracker(session_id="demo-123")
        >>> tracker.log_request(request, response)
        >>> print(tracker.summary())
    """

    def __init__(self, session_id: str) -> None:
        """Initialize request tracker.

        Args:
            session_id: Deliberation session identifier
        """
        self.session_id = session_id
        self.requests: list[tuple[PromptRequest, LLMResponse]] = []

    def log_request(self, request: PromptRequest, response: LLMResponse) -> None:
        """Log a completed request.

        Args:
            request: The prompt request
            response: The LLM response
        """
        self.requests.append((request, response))
        logger.debug(
            f"[{self.session_id}] Logged request {request.request_id}: {response.summary()}"
        )

    def get_total_cost(self) -> float:
        """Get total cost across all requests.

        Returns:
            Total cost in USD
        """
        return sum(resp.cost_total for _, resp in self.requests)

    def get_total_tokens(self) -> int:
        """Get total tokens across all requests.

        Returns:
            Total token count
        """
        return sum(resp.total_tokens for _, resp in self.requests)

    def summary(self) -> dict[str, Any]:
        """Generate summary statistics.

        Returns:
            Dictionary with summary metrics
        """
        return {
            "session_id": self.session_id,
            "request_count": len(self.requests),
            "total_cost": self.get_total_cost(),
            "total_tokens": self.get_total_tokens(),
            "total_retries": sum(resp.retry_count for _, resp in self.requests),
        }
