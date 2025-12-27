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

from bo1.config import TokenBudgets, get_settings, resolve_tier_to_model
from bo1.constants import LLMConfig, OutputLengthConfig
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
from bo1.llm.response_parser import ValidationConfig, XMLValidator
from bo1.logging import ErrorCode, log_error
from bo1.utils.logging import get_logger, log_llm_call

# Import metrics for tracking LLM calls
try:
    from backend.api.middleware.metrics import (
        record_llm_cost,
        record_llm_rate_limit_exceeded,
        record_llm_request,
        record_output_length_warning,
        record_provider_fallback,
        record_xml_retry_success,
        record_xml_validation_failure,
    )

    _metrics_available = True
except ImportError:
    # Metrics may not be available in all contexts (e.g., console-only mode)
    _metrics_available = False

    def record_llm_cost(model: str, provider: str, cost_cents: float) -> None:  # noqa: D103
        """No-op when metrics unavailable."""

    def record_llm_request(model: str, provider: str, success: bool = True) -> None:  # noqa: D103
        """No-op when metrics unavailable."""

    def record_xml_validation_failure(agent_type: str, tag: str) -> None:  # noqa: D103
        """No-op when metrics unavailable."""

    def record_xml_retry_success(agent_type: str) -> None:  # noqa: D103
        """No-op when metrics unavailable."""

    def record_output_length_warning(warning_type: str, model: str) -> None:  # noqa: D103
        """No-op when metrics unavailable."""

    def record_provider_fallback(from_provider: str, to_provider: str, reason: str) -> None:  # noqa: D103
        """No-op when metrics unavailable."""

    def record_llm_rate_limit_exceeded(limit_type: str, session_id: str) -> None:  # noqa: D103
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
    max_tokens: int = Field(default=TokenBudgets.DEFAULT, description="Maximum output tokens")

    # Metadata for tracking
    phase: str | None = Field(default=None, description="Deliberation phase")
    agent_type: str | None = Field(default=None, description="Agent making the request")
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique request ID"
    )
    prompt_type: str | None = Field(
        default=None,
        description="Prompt type for per-prompt-type cache analysis. Valid values: "
        "persona_contribution, facilitator_decision, synthesis, decomposition, "
        "context_collection, clarification, research_summary, task_extraction, embedding, search",
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

    async def call(self, request: PromptRequest, *, _used_fallback: bool = False) -> LLMResponse:
        """Execute an LLM call with retry/rate-limit handling and caching.

        Args:
            request: Structured prompt request
            _used_fallback: Internal flag to prevent infinite fallback loops

        Returns:
            LLMResponse with comprehensive metrics

        Raises:
            APIError: If all retries exhausted or non-retryable error
            RuntimeError: If circuit breaker open and fallback unavailable/disabled
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

        # Apply session-level rate limiting (non-blocking, graceful degradation)
        from bo1.llm.rate_limiter import get_session_rate_limiter

        rate_limiter = get_session_rate_limiter()
        cost_ctx = get_cost_context()
        session_id = cost_ctx.get("session_id")
        round_number = cost_ctx.get("round_number", 0)

        if session_id:
            # Check round limit (log warning, emit metric, but don't block)
            if not rate_limiter.check_session_round_limit(session_id, round_number):
                record_llm_rate_limit_exceeded("round", session_id)
                # Continue anyway - graceful degradation

            # Check call rate limit (await if needed)
            allowed, wait_seconds = rate_limiter.check_call_rate(session_id)
            if not allowed:
                record_llm_rate_limit_exceeded("call_rate", session_id)
                if wait_seconds > 0:
                    logger.info(f"[{request.request_id}] Rate limited, waiting {wait_seconds:.1f}s")
                    await asyncio.sleep(wait_seconds)
                    # Record the call after waiting
                    rate_limiter.record_call(session_id)

            # Periodic cleanup of stale sessions
            rate_limiter.maybe_cleanup()

        retry_count = 0
        last_error: Exception | None = None

        # Determine active provider (handles fallback)
        settings = get_settings()
        provider = get_active_llm_provider(
            primary=settings.llm_primary_provider,
            fallback="openai" if settings.llm_primary_provider == "anthropic" else "anthropic",
            fallback_enabled=settings.llm_fallback_enabled,
        )

        # Determine fallback provider
        fallback_provider = (
            "openai" if settings.llm_primary_provider == "anthropic" else "anthropic"
        )

        # Resolve model tier/alias to full ID for the active provider
        model_id = resolve_tier_to_model(request.model, provider=provider)

        logger.info(
            f"[{request.request_id}] Starting LLM call: "
            f"provider={provider}, model={model_id}, phase={request.phase}, agent={request.agent_type}"
        )

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
                    prompt_type=cost_ctx.get("prompt_type") or request.prompt_type,
                    feature=cost_ctx.get("feature"),
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

                # Calculate output ratio for logging
                output_ratio = (
                    token_usage.output_tokens / request.max_tokens
                    if request.max_tokens > 0
                    else 0.0
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
                    output_ratio=f"{output_ratio:.2%}",
                    max_tokens=request.max_tokens,
                )

                # Track Prometheus metrics
                record_llm_request(model=model_id, provider=provider, success=True)
                # Convert cost to cents (cost_total is in dollars)
                cost_cents = llm_response.cost_total * 100 if llm_response.cost_total else 0
                record_llm_cost(model=model_id, provider=provider, cost_cents=cost_cents)

                # Validate output length (non-blocking, warnings only)
                warning_type = self._validate_output_length(
                    response=llm_response,
                    max_tokens=request.max_tokens,
                    request_id=request.request_id,
                    model=model_id,
                    phase=request.phase,
                )
                if warning_type:
                    record_output_length_warning(warning_type, model_id)

                # Cache the response for future use
                await cache.set(request, llm_response)

                return llm_response

            except RateLimitError as e:
                last_error = e
                retry_count += 1

                # Check if we have retries left
                if attempt >= self.retry_policy.max_retries:
                    log_error(
                        logger,
                        ErrorCode.LLM_RATE_LIMIT,
                        f"[{request.request_id}] Rate limit exceeded, all retries exhausted: {e}",
                        request_id=request.request_id,
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
                    log_error(
                        logger,
                        ErrorCode.LLM_API_ERROR,
                        f"[{request.request_id}] API error (non-retryable): {e}",
                        request_id=request.request_id,
                    )
                    record_llm_request(model=model_id, provider=provider, success=False)
                    raise

            except CircuitBreakerOpenError as e:
                # Circuit breaker is open - API is experiencing issues
                log_error(
                    logger,
                    ErrorCode.LLM_CIRCUIT_OPEN,
                    f"[{request.request_id}] Circuit breaker OPEN for {provider}: {e}",
                    request_id=request.request_id,
                    provider=provider,
                )
                record_llm_request(model=model_id, provider=provider, success=False)

                # Attempt fallback if enabled and not already tried
                if settings.llm_fallback_enabled and not _used_fallback:
                    # Check if fallback provider's circuit breaker is closed
                    fallback_cb = self._get_circuit_breaker(fallback_provider)
                    if fallback_cb.state.name.lower() != "open":
                        logger.warning(
                            f"[{request.request_id}] Provider fallback: "
                            f"{provider} → {fallback_provider} (reason: circuit_breaker_open)"
                        )
                        record_provider_fallback(
                            from_provider=provider,
                            to_provider=fallback_provider,
                            reason="circuit_breaker_open",
                        )
                        # Retry with fallback provider (recursive call with flag)
                        return await self._call_with_provider(
                            request=request,
                            provider=fallback_provider,
                            start_time=start_time,
                            cost_ctx=cost_ctx,
                            cache=cache,
                            _used_fallback=True,
                        )
                    else:
                        log_error(
                            logger,
                            ErrorCode.LLM_CIRCUIT_OPEN,
                            f"[{request.request_id}] Both providers unavailable: "
                            f"{provider} and {fallback_provider} circuits open",
                            request_id=request.request_id,
                        )

                # Re-raise as RuntimeError - no fallback available
                raise RuntimeError(
                    "Service temporarily unavailable due to repeated failures. Please try again later."
                ) from e

            except Exception as e:
                # Unexpected error, don't retry
                log_error(
                    logger,
                    ErrorCode.LLM_API_ERROR,
                    f"[{request.request_id}] Unexpected error: {e}",
                    request_id=request.request_id,
                )
                record_llm_request(model=model_id, provider=provider, success=False)
                raise

        # Should never reach here, but just in case
        log_error(
            logger,
            ErrorCode.LLM_RETRIES_EXHAUSTED,
            f"[{request.request_id}] All retries exhausted",
            request_id=request.request_id,
        )
        record_llm_request(model=model_id, provider=provider, success=False)
        raise last_error or RuntimeError("All retries exhausted with no error captured")

    async def _call_with_provider(
        self,
        request: PromptRequest,
        provider: str,
        start_time: float,
        cost_ctx: dict[str, Any],
        cache: Any,
        _used_fallback: bool = False,
    ) -> LLMResponse:
        """Execute LLM call with a specific provider (used for fallback).

        Args:
            request: Structured prompt request
            provider: Provider to use ("anthropic" or "openai")
            start_time: Original request start time for duration tracking
            cost_ctx: Cost tracking context
            cache: LLM cache instance
            _used_fallback: Flag indicating this is a fallback call

        Returns:
            LLMResponse from the fallback provider
        """
        # Resolve model for fallback provider
        model_id = resolve_tier_to_model(request.model, provider=provider)

        logger.info(
            f"[{request.request_id}] Fallback LLM call: "
            f"provider={provider}, model={model_id}, phase={request.phase}"
        )

        # Get circuit breaker for fallback provider
        circuit_breaker = self._get_circuit_breaker(provider)

        # Single attempt for fallback (no retry loop - already exhausted retries)
        with CostTracker.track_call(
            provider=provider,
            operation_type="completion",
            model_name=model_id,
            session_id=cost_ctx.get("session_id"),
            user_id=cost_ctx.get("user_id"),
            node_name=cost_ctx.get("node_name"),
            phase=cost_ctx.get("phase") or request.phase,
            prompt_type=cost_ctx.get("prompt_type") or request.prompt_type,
            persona_name=cost_ctx.get("persona_name"),
            round_number=cost_ctx.get("round_number"),
            sub_problem_index=cost_ctx.get("sub_problem_index"),
            metadata={"prompt_name": cost_ctx.get("prompt_name", request.agent_type)},
        ) as cost_record:
            # Make the LLM call with circuit breaker protection
            async def _make_api_call() -> tuple[str, TokenUsage]:
                if provider == "openai":
                    openai_client = self._get_openai_client()
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

            # Populate cost record
            cost_record.input_tokens = token_usage.input_tokens
            cost_record.output_tokens = token_usage.output_tokens
            cost_record.cache_creation_tokens = token_usage.cache_creation_tokens
            cost_record.cache_read_tokens = token_usage.cache_read_tokens

        # Calculate duration from original start
        duration_ms = int((time.time() - start_time) * 1000)

        # Build LLMResponse
        llm_response = LLMResponse(
            content=response_text,
            model=model_id,
            token_usage=token_usage,
            duration_ms=duration_ms,
            retry_count=0,  # Fallback is not a retry
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
            retry_count=0,
            output_ratio=f"{token_usage.output_tokens / request.max_tokens:.2%}"
            if request.max_tokens > 0
            else "0.00%",
            max_tokens=request.max_tokens,
        )

        # Track Prometheus metrics
        record_llm_request(model=model_id, provider=provider, success=True)
        cost_cents = llm_response.cost_total * 100 if llm_response.cost_total else 0
        record_llm_cost(model=model_id, provider=provider, cost_cents=cost_cents)

        # Cache the response
        await cache.set(request, llm_response)

        return llm_response

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

    def _validate_output_length(
        self,
        response: LLMResponse,
        max_tokens: int,
        request_id: str,
        model: str,
        phase: str | None,
    ) -> str | None:
        """Validate output length and return warning type if applicable.

        Args:
            response: LLM response to validate
            max_tokens: Maximum tokens requested for this call
            request_id: Request identifier for logging
            model: Model name used for this call
            phase: Deliberation phase for context

        Returns:
            Warning type ("verbose" or "truncated") or None if normal
        """
        if not OutputLengthConfig.is_enabled():
            return None

        if max_tokens <= 0:
            return None

        output_tokens = response.token_usage.output_tokens
        ratio = output_tokens / max_tokens

        warning_type: str | None = None

        if ratio < OutputLengthConfig.VERBOSE_THRESHOLD:
            warning_type = "verbose"
            logger.warning(
                f"[{request_id}] Output length warning: response uses only "
                f"{ratio:.1%} of max_tokens ({output_tokens}/{max_tokens}), "
                f"model={model}, phase={phase or 'unknown'}"
            )
        elif ratio > OutputLengthConfig.TRUNCATION_THRESHOLD:
            warning_type = "truncated"
            logger.warning(
                f"[{request_id}] Output length warning: response uses "
                f"{ratio:.1%} of max_tokens ({output_tokens}/{max_tokens}), "
                f"possible truncation, model={model}, phase={phase or 'unknown'}"
            )

        return warning_type

    async def call_with_validation(
        self,
        request: PromptRequest,
        validation: ValidationConfig,
    ) -> LLMResponse:
        """Execute LLM call with XML validation and automatic retry on failure.

        Validates response against required XML tags. On failure, appends
        feedback message and retries up to `validation.max_retries` times.
        Tracks validation failures and retry success in Prometheus metrics.

        Args:
            request: Structured prompt request
            validation: Validation config with required_tags, max_retries, strict

        Returns:
            LLMResponse with accumulated tokens from all attempts

        Raises:
            XMLValidationError: If strict=True and validation fails after retries

        Example:
            >>> broker = PromptBroker()
            >>> request = PromptRequest(system="...", user_message="...", prefill="<thinking>")
            >>> validation = ValidationConfig(required_tags=["recommendation", "reasoning"])
            >>> response = await broker.call_with_validation(request, validation)
        """
        from bo1.llm.response_parser import XMLValidationError

        # Track total tokens across attempts for accurate cost accounting
        total_input_tokens = 0
        total_output_tokens = 0
        total_cache_creation = 0
        total_cache_read = 0
        validation_retries = 0

        # Store original user message for retry modification
        original_user_message = request.user_message
        agent_type = request.agent_type or "unknown"

        for attempt in range(validation.max_retries + 1):
            # Make the LLM call
            response = await self.call(request)

            # Accumulate tokens
            total_input_tokens += response.token_usage.input_tokens
            total_output_tokens += response.token_usage.output_tokens
            total_cache_creation += response.token_usage.cache_creation_tokens
            total_cache_read += response.token_usage.cache_read_tokens

            # Reconstruct full content if prefill was used
            content = response.content
            if request.prefill:
                content = request.prefill + content

            # Validate XML structure
            is_valid, errors = XMLValidator.validate(content, validation.required_tags)

            if is_valid:
                # Success! Log if this was a retry success
                if validation_retries > 0:
                    logger.info(
                        f"[{request.request_id}] XML validation succeeded on retry "
                        f"(attempt {attempt + 1}), agent={agent_type}"
                    )
                    record_xml_retry_success(agent_type)

                # Return response with accumulated token counts
                response.token_usage.input_tokens = total_input_tokens
                response.token_usage.output_tokens = total_output_tokens
                response.token_usage.cache_creation_tokens = total_cache_creation
                response.token_usage.cache_read_tokens = total_cache_read
                return response

            # Validation failed
            validation_retries += 1

            # Record metrics for each missing/malformed tag
            for error in errors:
                # Extract tag from error message (format: "Missing required tag: <tagname>")
                if "Missing required tag:" in error:
                    tag = error.split("<")[1].split(">")[0] if "<" in error else "unknown"
                else:
                    tag = "structure"
                record_xml_validation_failure(agent_type, tag)

            logger.warning(
                f"[{request.request_id}] XML validation failed (attempt {attempt + 1}/"
                f"{validation.max_retries + 1}): {errors}"
            )

            # Check if we have retries left
            if attempt >= validation.max_retries:
                # Exhausted retries
                if validation.strict:
                    raise XMLValidationError(
                        f"XML validation failed after {validation.max_retries + 1} attempts: {errors}",
                        tag=validation.required_tags[0] if validation.required_tags else None,
                        details=str(errors),
                    )
                # Non-strict: return last response with warning
                logger.warning(
                    f"[{request.request_id}] Returning response despite validation failure "
                    f"(non-strict mode), errors={errors}"
                )
                response.token_usage.input_tokens = total_input_tokens
                response.token_usage.output_tokens = total_output_tokens
                response.token_usage.cache_creation_tokens = total_cache_creation
                response.token_usage.cache_read_tokens = total_cache_read
                return response

            # Build feedback message for retry
            feedback = XMLValidator.get_validation_feedback(errors)

            # Modify request with feedback appended to user message
            request = PromptRequest(
                system=request.system,
                user_message=f"{original_user_message}\n\n---\n\n{feedback}",
                model=request.model,
                prefill=request.prefill,
                cache_system=request.cache_system,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                phase=request.phase,
                agent_type=request.agent_type,
            )

            logger.info(
                f"[{request.request_id}] Retrying with validation feedback, "
                f"attempt {attempt + 2}/{validation.max_retries + 1}"
            )

        # Should not reach here
        raise RuntimeError("Validation loop exited unexpectedly")


def get_model_for_phase(phase: str, round_number: int = 0, session_id: str | None = None) -> str:
    """Select appropriate model tier for task based on phase, round, and A/B test group.

    Uses 'fast' tier for supporting tasks and early rounds to reduce cost and latency,
    while using 'core' tier for critical synthesis and later rounds.

    When A/B testing is enabled (HAIKU_AB_TEST_ENABLED=true), sessions are assigned
    to test/control groups based on session_id hash:
    - Control group: Uses HAIKU_ROUND_LIMIT (default: 3) for fast tier
    - Test group: Uses HAIKU_AB_TEST_LIMIT (default: 4) for fast tier

    Args:
        phase: The deliberation phase
        round_number: The current round number (for contribution phase)
        session_id: Session identifier for A/B test group assignment (optional)

    Returns:
        Model tier ('fast' or 'core') - provider-agnostic

    Examples:
        >>> get_model_for_phase("convergence_check")
        'fast'
        >>> get_model_for_phase("contribution", round_number=1)
        'fast'
        >>> get_model_for_phase("contribution", round_number=3)
        'fast'  # rounds 1-3 use fast tier by default
        >>> get_model_for_phase("contribution", round_number=4)
        'core'
        >>> get_model_for_phase("synthesis")
        'core'
        >>> # With A/B test enabled:
        >>> get_model_for_phase("contribution", round_number=4, session_id="test-session")
        'fast'  # if session_id hashes to test group (extends to round 4)
    """
    from bo1.constants import ModelSelectionConfig

    # Fast phases use 'fast' tier (cheaper model)
    if phase in ["convergence_check", "drift_check", "format_validation"]:
        return "fast"

    # Contribution phase: check round limit with A/B test support
    if phase == "contribution":
        # Determine round limit based on A/B test group
        ab_group = ModelSelectionConfig.get_ab_group(session_id)

        if ab_group == "test":
            haiku_limit = ModelSelectionConfig.get_ab_test_limit()
        else:
            haiku_limit = ModelSelectionConfig.get_haiku_round_limit()

        # Record model selection metrics
        tier = "fast" if round_number <= haiku_limit else "core"

        # Emit metric for analysis
        try:
            from backend.api.middleware.metrics import record_model_tier_selected

            record_model_tier_selected(tier=tier, round_number=round_number, ab_group=ab_group)
        except ImportError:
            pass  # Metrics not available in all contexts

        # Log for analysis (structured logging)
        if session_id:
            logger.debug(
                "model_selection",
                extra={
                    "session_id": session_id[:8] if session_id else None,
                    "phase": phase,
                    "round": round_number,
                    "ab_group": ab_group,
                    "haiku_limit": haiku_limit,
                    "tier": tier,
                },
            )

        return tier

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
