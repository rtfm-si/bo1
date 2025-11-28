"""Claude LLM client with prompt caching and token tracking.

This module provides a high-level interface to Claude via the Anthropic SDK,
with support for prompt caching, token usage tracking, and cost calculation.
"""

import logging
from typing import Any

from anthropic import RateLimitError
from anthropic.types import MessageParam, TextBlockParam
from pydantic import BaseModel, Field

from bo1.config import calculate_cost, get_model_for_role, resolve_model_alias

logger = logging.getLogger(__name__)


class TokenUsage(BaseModel):
    """Token usage statistics for a single LLM call."""

    input_tokens: int = Field(default=0, description="Regular input tokens")
    output_tokens: int = Field(default=0, description="Output tokens generated")
    cache_creation_tokens: int = Field(default=0, description="Tokens written to cache")
    cache_read_tokens: int = Field(default=0, description="Tokens read from cache")

    @property
    def total_input_tokens(self) -> int:
        """Total input tokens (regular + cache creation)."""
        return self.input_tokens + self.cache_creation_tokens

    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output + cache)."""
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_tokens
            + self.cache_read_tokens
        )

    @property
    def cache_hit_rate(self) -> float:
        """Percentage of input tokens that were cache hits (0-1)."""
        total_input = self.total_input_tokens + self.cache_read_tokens
        if total_input == 0:
            return 0.0
        return self.cache_read_tokens / total_input

    def calculate_cost(self, model_id: str) -> float:
        """Calculate cost for this usage.

        Args:
            model_id: Model identifier (alias or full ID)

        Returns:
            Total cost in USD
        """
        return calculate_cost(
            model_id=model_id,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cache_creation_tokens=self.cache_creation_tokens,
            cache_read_tokens=self.cache_read_tokens,
        )


class ClaudeClient:
    """High-level Claude client with caching and token tracking.

    This class provides:
    - Prompt caching support with cache_control markers
    - Detailed token usage tracking
    - Automatic retries with exponential backoff
    - Cost calculation
    - Role-based model selection

    Examples:
        >>> client = ClaudeClient()
        >>> response, usage = await client.call(
        ...     model="sonnet",
        ...     system="You are a helpful assistant.",
        ...     messages=[{"role": "user", "content": "Hello!"}],
        ...     cache_system=True
        ... )
    """

    def __init__(self, api_key: str | None = None, max_retries: int = 3) -> None:
        """Initialize the Claude client.

        Args:
            api_key: Anthropic API key (if None, uses ANTHROPIC_API_KEY from env)
            max_retries: Maximum number of retry attempts for rate limits
        """
        self.api_key = api_key
        self.max_retries = max_retries

    async def call(
        self,
        model: str,
        messages: list[dict[str, str]],
        system: str | None = None,
        cache_system: bool = False,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        prefill: str | None = None,
    ) -> tuple[str, TokenUsage]:
        """Make a Claude API call with optional prompt caching.

        Args:
            model: Model to use (alias like 'sonnet' or full ID)
            messages: List of message dicts with 'role' and 'content'
            system: Optional system prompt
            cache_system: If True, mark system prompt for caching
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            prefill: Optional assistant message prefill (e.g., "{" for JSON)

        Returns:
            Tuple of (response_text, token_usage)

        Raises:
            RateLimitError: If rate limit exceeded after retries
            ValueError: If API returns unexpected response format

        Examples:
            >>> client = ClaudeClient()
            >>> response, usage = await client.call(
            ...     model="sonnet",
            ...     system="You are a helpful assistant.",
            ...     messages=[{"role": "user", "content": "Hello!"}],
            ...     cache_system=True
            ... )
            >>> # For JSON responses:
            >>> response, usage = await client.call(
            ...     model="sonnet",
            ...     messages=[{"role": "user", "content": "Return JSON"}],
            ...     prefill="{"
            ... )
        """
        full_model_id = resolve_model_alias(model)

        # Use Anthropic SDK directly for caching support
        from anthropic import AsyncAnthropic

        # Initialize with beta header for prompt caching
        client_kwargs: dict[str, Any] = {
            "default_headers": {"anthropic-beta": "prompt-caching-2024-07-31"}
        }
        if self.api_key:
            client_kwargs["api_key"] = self.api_key

        anthropic_client = AsyncAnthropic(**client_kwargs)

        # Build messages in Anthropic format
        anthropic_messages: list[MessageParam] = []

        # Add conversation messages
        for msg in messages:
            # Cast role to proper literal type
            role: Any = msg["role"]  # "user" or "assistant"
            content: Any = msg["content"]
            anthropic_messages.append({"role": role, "content": content})

        # Add prefill if provided
        if prefill:
            anthropic_messages.append({"role": "assistant", "content": prefill})

        # Prepare system parameter with caching
        # Type is complex because Anthropic SDK uses Union with Omit
        # NOTE: Newer models (Haiku 4.5+) require system to be a list of text blocks
        system_param: Any = None
        if system:
            if cache_system:
                # Use Anthropic's cache_control format
                cache_control: dict[str, str] = {"type": "ephemeral"}
                system_param = [
                    TextBlockParam(
                        type="text",
                        text=system,
                        cache_control=cache_control,  # type: ignore[typeddict-item]
                    )
                ]
            else:
                # Always use list format for compatibility with newer models
                system_param = [
                    TextBlockParam(
                        type="text",
                        text=system,
                    )
                ]

        # Make direct Anthropic API call
        # Build kwargs dynamically - only include system if it's not None
        api_kwargs: dict[str, Any] = {
            "model": full_model_id,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_param is not None:
            api_kwargs["system"] = system_param

        try:
            response = await anthropic_client.messages.create(**api_kwargs)
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise

        # Extract response text from Anthropic SDK response
        if not hasattr(response, "content") or not response.content:
            raise ValueError(f"Unexpected response format: {response}")

        # Anthropic SDK returns content as list of content blocks
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        # Prepend prefill to response if it was used
        if prefill:
            response_text = prefill + response_text

        # Extract token usage from Anthropic SDK response
        token_usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_creation_tokens=getattr(response.usage, "cache_creation_input_tokens", 0),
            cache_read_tokens=getattr(response.usage, "cache_read_input_tokens", 0),
        )

        # Log usage stats
        cost = token_usage.calculate_cost(full_model_id)
        cache_rate = token_usage.cache_hit_rate * 100

        logger.info(
            f"Claude API call: {full_model_id} | "
            f"Input: {token_usage.total_input_tokens} | "
            f"Output: {token_usage.output_tokens} | "
            f"Cache read: {token_usage.cache_read_tokens} ({cache_rate:.1f}%) | "
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
        """Make a Claude API call using role-based model selection.

        This is a convenience method that automatically selects the
        appropriate model based on the agent role (PERSONA, FACILITATOR, etc.).

        Args:
            role: Agent role (PERSONA, FACILITATOR, SUMMARIZER, etc.)
            messages: List of message dicts with 'role' and 'content'
            system: Optional system prompt
            cache_system: If True, mark system prompt for caching
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Tuple of (response_text, token_usage)

        Examples:
            >>> client = ClaudeClient()
            >>> response, usage = await client.call_for_role(
            ...     role="PERSONA",
            ...     system="You are Maria Chen, a strategic advisor...",
            ...     messages=[{"role": "user", "content": "What do you think?"}],
            ...     cache_system=True
            ... )
        """
        model_id = get_model_for_role(role)
        return await self.call(
            model=model_id,
            messages=messages,
            system=system,
            cache_system=cache_system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
