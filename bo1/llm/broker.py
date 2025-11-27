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
from pydantic import BaseModel, Field

from bo1.config import resolve_model_alias
from bo1.llm.client import ClaudeClient
from bo1.llm.response import LLMResponse
from bo1.utils.logging import get_logger, log_llm_call

# Import metrics for tracking LLM calls
try:
    from backend.api.metrics import metrics
except ImportError:
    # Metrics may not be available in all contexts (e.g., console-only mode)
    metrics = None  # type: ignore[assignment]

logger = get_logger(__name__)


class RetryPolicy(BaseModel):
    """Configuration for retry behavior with exponential backoff.

    Examples:
        >>> policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=30.0)
        >>> delay = policy.calculate_delay(attempt=2)  # Returns ~4s with jitter
    """

    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    base_delay: float = Field(default=1.0, description="Initial delay in seconds")
    max_delay: float = Field(default=60.0, description="Maximum delay in seconds")
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
        ...     model="sonnet",
        ...     prefill=None,
        ...     cache_system=False,
        ...     phase="test",
        ...     agent_type="TestAgent"
        ... )
    """

    system: str = Field(description="System prompt")
    user_message: str = Field(description="User message content")
    model: str = Field(default="sonnet", description="Model alias or full ID")
    prefill: str | None = Field(default=None, description="Assistant prefill (e.g., '{' for JSON)")
    cache_system: bool = Field(default=False, description="Enable prompt caching for system prompt")
    temperature: float = Field(default=1.0, description="Sampling temperature")
    max_tokens: int = Field(default=4096, description="Maximum output tokens")

    # Metadata for tracking
    phase: str | None = Field(default=None, description="Deliberation phase")
    agent_type: str | None = Field(default=None, description="Agent making the request")
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique request ID"
    )


class PromptBroker:
    """Centralized broker for all LLM interactions.

    This class handles:
    - Retry logic with exponential backoff + jitter
    - Rate limit handling (429 errors, Retry-After headers)
    - Standardized LLMResponse format
    - Error handling and logging
    - Request tracking

    Examples:
        >>> broker = PromptBroker()
        >>> request = PromptRequest(
        ...     system="You are an expert.",
        ...     user_message="Analyze this problem.",
        ...     model="sonnet",
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
    ) -> None:
        """Initialize the Prompt Broker.

        Args:
            client: ClaudeClient instance (if None, creates default)
            retry_policy: RetryPolicy config (if None, uses default)
        """
        self.client = client or ClaudeClient()
        self.retry_policy = retry_policy or RetryPolicy()

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
        cached_response = await cache.get_cached_response(request)
        if cached_response:
            logger.info(
                f"[{request.request_id}] Cache hit: "
                f"model={cached_response.model}, phase={request.phase}"
            )
            # Track cache hit
            if metrics:
                metrics.increment("llm.cache.hit")
            return cached_response

        # Track cache miss
        if metrics:
            metrics.increment("llm.cache.miss")

        start_time = time.time()
        retry_count = 0
        last_error: Exception | None = None

        # Resolve model alias to full ID
        model_id = resolve_model_alias(request.model)

        logger.info(
            f"[{request.request_id}] Starting LLM call: "
            f"model={model_id}, phase={request.phase}, agent={request.agent_type}"
        )

        for attempt in range(self.retry_policy.max_retries + 1):
            try:
                # Make the LLM call
                response_text, token_usage = await self.client.call(
                    model=request.model,
                    messages=[{"role": "user", "content": request.user_message}],
                    system=request.system,
                    cache_system=request.cache_system,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    prefill=request.prefill,
                )

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

                # Track metrics
                if metrics:
                    metrics.increment("llm.api_calls")
                    metrics.observe("llm.input_tokens", token_usage.input_tokens)
                    metrics.observe("llm.output_tokens", token_usage.output_tokens)
                    metrics.observe("llm.cache_read_tokens", token_usage.cache_read_tokens)
                    metrics.observe("llm.cache_creation_tokens", token_usage.cache_creation_tokens)
                    metrics.observe("llm.cost", llm_response.cost_total)
                    metrics.observe("llm.duration_ms", duration_ms)

                # Cache the response for future use
                await cache.cache_response(request, llm_response)

                return llm_response

            except RateLimitError as e:
                last_error = e
                retry_count += 1

                # Check if we have retries left
                if attempt >= self.retry_policy.max_retries:
                    logger.error(
                        f"[{request.request_id}] Rate limit exceeded, all retries exhausted: {e}"
                    )
                    if metrics:
                        metrics.increment("llm.errors.rate_limit")
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
                    if metrics:
                        metrics.increment("llm.errors.api_error")
                    raise

            except Exception as e:
                # Unexpected error, don't retry
                logger.error(f"[{request.request_id}] Unexpected error: {e}")
                if metrics:
                    metrics.increment("llm.errors.unexpected")
                raise

        # Should never reach here, but just in case
        logger.error(f"[{request.request_id}] All retries exhausted")
        if metrics:
            metrics.increment("llm.errors.retries_exhausted")
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
    """Select appropriate model for task based on phase and round number.

    Uses Haiku for supporting tasks and early rounds to reduce cost and latency,
    while using Sonnet for critical synthesis and later rounds.

    Args:
        phase: The deliberation phase
        round_number: The current round number (for contribution phase)

    Returns:
        Model alias ('haiku' or 'sonnet')

    Examples:
        >>> get_model_for_phase("convergence_check")
        'haiku'
        >>> get_model_for_phase("contribution", round_number=1)
        'haiku'
        >>> get_model_for_phase("contribution", round_number=3)
        'sonnet'
        >>> get_model_for_phase("synthesis")
        'sonnet'
    """
    # Fast phases use Haiku (90% cost savings)
    if phase in ["convergence_check", "drift_check", "format_validation"]:
        return "haiku"

    # Early exploration rounds can use Haiku (rounds 1-2)
    if phase == "contribution" and round_number <= 2:
        return "haiku"

    # Everything else uses Sonnet (critical synthesis, later rounds, voting)
    return "sonnet"


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
