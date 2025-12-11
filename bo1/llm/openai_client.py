"""OpenAI LLM client with token tracking (fallback provider).

This module provides a high-level interface to OpenAI GPT models,
mirroring the ClaudeClient interface for provider-agnostic usage.
"""

import logging
from typing import Any

from pydantic import BaseModel, Field

from bo1.config import calculate_cost, get_model_for_role, resolve_model_alias

logger = logging.getLogger(__name__)


class TokenUsage(BaseModel):
    """Token usage statistics for a single LLM call."""

    input_tokens: int = Field(default=0, description="Input tokens (prompt)")
    output_tokens: int = Field(default=0, description="Output tokens generated")
    cache_creation_tokens: int = Field(default=0, description="Tokens written to cache (OpenAI: 0)")
    cache_read_tokens: int = Field(default=0, description="Cached tokens (OpenAI prompt caching)")

    @property
    def total_input_tokens(self) -> int:
        """Total input tokens."""
        return self.input_tokens + self.cache_creation_tokens

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens + self.cache_read_tokens

    @property
    def cache_hit_rate(self) -> float:
        """Percentage of input tokens that were cache hits (0-1)."""
        total_input = self.total_input_tokens + self.cache_read_tokens
        if total_input == 0:
            return 0.0
        return self.cache_read_tokens / total_input

    def calculate_cost(self, model_id: str) -> float:
        """Calculate cost for this usage."""
        return calculate_cost(
            model_id=model_id,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cache_creation_tokens=self.cache_creation_tokens,
            cache_read_tokens=self.cache_read_tokens,
        )


class OpenAIClient:
    """High-level OpenAI client with token tracking.

    This class provides a ClaudeClient-compatible interface for OpenAI models,
    enabling provider-agnostic LLM calls.

    Examples:
        >>> client = OpenAIClient()
        >>> response, usage = await client.call(
        ...     model="gpt-5.1",
        ...     system="You are a helpful assistant.",
        ...     messages=[{"role": "user", "content": "Hello!"}],
        ... )
    """

    def __init__(self, api_key: str | None = None, max_retries: int = 3) -> None:
        """Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key (if None, uses OPENAI_API_KEY from env)
            max_retries: Maximum number of retry attempts for rate limits
        """
        self.api_key = api_key
        self.max_retries = max_retries

    async def call(
        self,
        model: str,
        messages: list[dict[str, str]],
        system: str | None = None,
        cache_system: bool = False,  # OpenAI handles caching automatically
        temperature: float = 1.0,
        max_tokens: int = 4096,
        prefill: str | None = None,
    ) -> tuple[str, TokenUsage]:
        """Make an OpenAI API call.

        Args:
            model: Model to use (alias like 'gpt-5.1' or full ID)
            messages: List of message dicts with 'role' and 'content'
            system: Optional system prompt
            cache_system: Ignored (OpenAI handles caching automatically)
            temperature: Sampling temperature (0-2 for OpenAI)
            max_tokens: Maximum tokens to generate
            prefill: Optional assistant message prefill (simulated via system prompt)

        Returns:
            Tuple of (response_text, token_usage)

        Raises:
            openai.RateLimitError: If rate limit exceeded after retries
            ValueError: If API returns unexpected response format
        """
        from openai import AsyncOpenAI, RateLimitError

        full_model_id = resolve_model_alias(model)

        # Initialize client
        client_kwargs: dict[str, Any] = {}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key

        openai_client = AsyncOpenAI(**client_kwargs)

        # Build messages in OpenAI format
        openai_messages: list[dict[str, str]] = []

        # Add system message if provided
        if system:
            openai_messages.append({"role": "system", "content": system})

        # Add conversation messages
        for msg in messages:
            openai_messages.append({"role": msg["role"], "content": msg["content"]})

        # Handle prefill by adding instruction to system or last user message
        # OpenAI doesn't support assistant prefill directly, so we simulate it
        if prefill:
            # Add instruction to start response with prefill
            instruction = f"\nIMPORTANT: Start your response with exactly: {prefill}"
            if openai_messages and openai_messages[-1]["role"] == "user":
                openai_messages[-1]["content"] += instruction
            elif system:
                openai_messages[0]["content"] += instruction

        try:
            response = await openai_client.chat.completions.create(
                model=full_model_id,
                messages=openai_messages,  # type: ignore[arg-type,unused-ignore]
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise

        # Extract response text
        if not response.choices:
            raise ValueError(f"Unexpected response format: {response}")

        response_text = response.choices[0].message.content or ""

        # Extract token usage
        usage = response.usage
        token_usage = TokenUsage(
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            cache_creation_tokens=0,  # OpenAI doesn't expose this
            cache_read_tokens=getattr(usage, "prompt_tokens_details", {}).get("cached_tokens", 0)
            if usage
            else 0,
        )

        # Log usage stats
        cost = token_usage.calculate_cost(full_model_id)

        logger.info(
            f"OpenAI API call: {full_model_id} | "
            f"Input: {token_usage.input_tokens} | "
            f"Output: {token_usage.output_tokens} | "
            f"Cost: ${cost:.6f}"
        )

        return response_text, token_usage

    async def call_for_role(
        self,
        role: str,
        messages: list[dict[str, str]],
        system: str | None = None,
        cache_system: bool = False,
        temperature: float = 1.0,
        max_tokens: int = 4096,
    ) -> tuple[str, TokenUsage]:
        """Make an OpenAI API call using role-based model selection.

        Args:
            role: Agent role (persona, facilitator, etc.)
            messages: List of message dicts with 'role' and 'content'
            system: Optional system prompt
            cache_system: Ignored (OpenAI handles caching automatically)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Tuple of (response_text, token_usage)
        """
        model_id = get_model_for_role(role, provider="openai")
        return await self.call(
            model=model_id,
            messages=messages,
            system=system,
            cache_system=cache_system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
