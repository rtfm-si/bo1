"""Standardized LLM response models for comprehensive metrics tracking.

This module provides a unified response format for all LLM interactions,
including detailed token usage, cost breakdown, performance metrics, and
aggregation capabilities.
"""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field

from bo1.llm.client import TokenUsage


class LLMResponse(BaseModel):
    """Standardized response from any LLM call with comprehensive metrics.

    This model captures everything needed for cost tracking, observability,
    and debugging across all agent types.

    Examples:
        >>> response = LLMResponse(
        ...     content="Analysis of the problem...",
        ...     model="claude-sonnet-4-20250514",
        ...     token_usage=TokenUsage(input_tokens=100, output_tokens=200),
        ...     duration_ms=1234,
        ...     retry_count=0
        ... )
        >>> print(f"Total cost: ${response.cost_total:.4f}")
        >>> print(f"Cache savings: ${response.cache_savings:.4f}")
    """

    # Core response data
    content: str = Field(description="Raw text response from LLM")
    model: str = Field(description="Model used (full ID, e.g., claude-sonnet-4-20250514)")

    # Token usage (detailed breakdown)
    token_usage: TokenUsage = Field(description="Detailed token usage statistics")

    # Performance metrics
    duration_ms: int = Field(description="Total request duration in milliseconds")
    retry_count: int = Field(default=0, description="Number of retries required")
    timestamp: datetime = Field(default_factory=datetime.now, description="When request completed")

    # Request metadata (optional)
    request_id: str | None = Field(default=None, description="Unique request identifier")
    phase: str | None = Field(
        default=None, description="Deliberation phase (e.g., 'decomposition', 'selection')"
    )
    agent_type: str | None = Field(
        default=None, description="Agent that made the call (e.g., 'DecomposerAgent')"
    )

    # Cost breakdown (computed from token_usage)
    @computed_field  # type: ignore[prop-decorator]
    @property
    def cost_input(self) -> float:
        """Cost for regular input tokens."""
        from bo1.config import MODEL_PRICING

        pricing = MODEL_PRICING.get(self.model, {})
        return (self.token_usage.input_tokens / 1_000_000) * pricing.get("input", 0.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cost_output(self) -> float:
        """Cost for output tokens."""
        from bo1.config import MODEL_PRICING

        pricing = MODEL_PRICING.get(self.model, {})
        return (self.token_usage.output_tokens / 1_000_000) * pricing.get("output", 0.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cost_cache_write(self) -> float:
        """Cost for cache creation tokens."""
        from bo1.config import MODEL_PRICING

        pricing = MODEL_PRICING.get(self.model, {})
        return (self.token_usage.cache_creation_tokens / 1_000_000) * pricing.get(
            "cache_creation", 0.0
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cost_cache_read(self) -> float:
        """Cost for cache read tokens."""
        from bo1.config import MODEL_PRICING

        pricing = MODEL_PRICING.get(self.model, {})
        return (self.token_usage.cache_read_tokens / 1_000_000) * pricing.get("cache_read", 0.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cost_total(self) -> float:
        """Total cost for this request.

        Uses centralized calculate_cost() from config module for consistency.
        """
        from bo1.config import calculate_cost

        return calculate_cost(
            model_id=self.model,
            input_tokens=self.token_usage.input_tokens,
            output_tokens=self.token_usage.output_tokens,
            cache_creation_tokens=self.token_usage.cache_creation_tokens,
            cache_read_tokens=self.token_usage.cache_read_tokens,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cache_savings(self) -> float:
        """Cost savings from cache hits.

        Calculates what we would have paid for cache_read_tokens if they were
        regular input tokens instead.
        """
        from bo1.config import MODEL_PRICING

        pricing = MODEL_PRICING.get(self.model, {})
        input_cost_per_million = pricing.get("input", 0.0)
        cache_read_cost_per_million = pricing.get("cache_read", 0.0)
        return (self.token_usage.cache_read_tokens / 1_000_000) * (
            input_cost_per_million - cache_read_cost_per_million
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output + cache operations)."""
        return self.token_usage.total_tokens

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cache_hit_rate(self) -> float:
        """Percentage of input that came from cache (0.0-1.0)."""
        return self.token_usage.cache_hit_rate

    def to_dict(self) -> dict[str, Any]:
        """Export to dictionary with all computed fields.

        Returns:
            Dictionary with all fields including computed costs
        """
        return {
            # Core data
            "content": self.content,
            "model": self.model,
            # Token breakdown
            "tokens": {
                "input": self.token_usage.input_tokens,
                "output": self.token_usage.output_tokens,
                "cache_write": self.token_usage.cache_creation_tokens,
                "cache_read": self.token_usage.cache_read_tokens,
                "total": self.total_tokens,
            },
            # Cost breakdown
            "cost": {
                "input": self.cost_input,
                "output": self.cost_output,
                "cache_write": self.cost_cache_write,
                "cache_read": self.cost_cache_read,
                "total": self.cost_total,
                "savings": self.cache_savings,
            },
            # Performance
            "performance": {
                "duration_ms": self.duration_ms,
                "retry_count": self.retry_count,
                "timestamp": self.timestamp.isoformat(),
            },
            # Metadata
            "metadata": {
                "request_id": self.request_id,
                "phase": self.phase,
                "agent_type": self.agent_type,
                "cache_hit_rate": self.cache_hit_rate,
            },
        }

    def to_json(self) -> str:
        """Export to JSON string.

        Returns:
            JSON string with all metrics
        """
        return json.dumps(self.to_dict(), indent=2)

    def summary(self) -> str:
        """Generate a one-line summary for logging.

        Returns:
            Compact summary string (e.g., "Decomposition: 1,234 tokens, $0.0123, 1.2s")
        """
        phase_str = f"{self.phase}: " if self.phase else ""
        duration_s = self.duration_ms / 1000
        retries_str = f", {self.retry_count} retries" if self.retry_count > 0 else ""
        cache_str = f", {int(self.cache_hit_rate * 100)}% cached" if self.cache_hit_rate > 0 else ""

        return (
            f"{phase_str}{self.total_tokens:,} tokens, "
            f"${self.cost_total:.4f}, {duration_s:.1f}s{retries_str}{cache_str}"
        )


class DeliberationMetrics(BaseModel):
    """Aggregated metrics for a complete deliberation session.

    Collects all LLM responses from decomposition, persona selection,
    initial round, multi-round deliberation, voting, and synthesis.

    Examples:
        >>> metrics = DeliberationMetrics(session_id="demo-123")
        >>> metrics.add_response(decomposition_response)
        >>> metrics.add_response(selection_response)
        >>> for contrib_response in contributions:
        ...     metrics.add_response(contrib_response)
        >>> print(f"Total cost: ${metrics.total_cost:.2f}")
        >>> print(f"Total tokens: {metrics.total_tokens:,}")
        >>> report = metrics.export_report()
    """

    session_id: str = Field(description="Deliberation session identifier")
    responses: list[LLMResponse] = Field(default_factory=list, description="All LLM responses")

    def add_response(self, response: LLMResponse) -> None:
        """Add a response to the metrics collection.

        Args:
            response: LLM response to add
        """
        self.responses.append(response)

    # Aggregated totals
    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_cost(self) -> float:
        """Total cost across all responses."""
        return sum(r.cost_total for r in self.responses)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_tokens(self) -> int:
        """Total tokens across all responses."""
        return sum(r.total_tokens for r in self.responses)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_input_tokens(self) -> int:
        """Total input tokens (regular + cache write)."""
        return sum(
            r.token_usage.input_tokens + r.token_usage.cache_creation_tokens for r in self.responses
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_output_tokens(self) -> int:
        """Total output tokens."""
        return sum(r.token_usage.output_tokens for r in self.responses)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_cache_read_tokens(self) -> int:
        """Total tokens read from cache."""
        return sum(r.token_usage.cache_read_tokens for r in self.responses)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_cache_savings(self) -> float:
        """Total cost savings from caching."""
        return sum(r.cache_savings for r in self.responses)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def avg_cache_hit_rate(self) -> float:
        """Average cache hit rate across all responses."""
        if not self.responses:
            return 0.0
        return sum(r.cache_hit_rate for r in self.responses) / len(self.responses)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_duration_ms(self) -> int:
        """Total time spent on LLM calls."""
        return sum(r.duration_ms for r in self.responses)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_retries(self) -> int:
        """Total number of retries across all calls."""
        return sum(r.retry_count for r in self.responses)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def call_count(self) -> int:
        """Number of LLM calls made."""
        return len(self.responses)

    # Per-phase breakdown
    def get_phase_metrics(self, phase: str) -> dict[str, Any]:
        """Get metrics for a specific phase.

        Args:
            phase: Phase name (e.g., 'decomposition', 'selection', 'deliberation')

        Returns:
            Dictionary with cost, tokens, duration for the phase
        """
        phase_responses = [r for r in self.responses if r.phase == phase]
        if not phase_responses:
            return {
                "calls": 0,
                "tokens": 0,
                "cost": 0.0,
                "duration_ms": 0,
            }

        return {
            "calls": len(phase_responses),
            "tokens": sum(r.total_tokens for r in phase_responses),
            "cost": sum(r.cost_total for r in phase_responses),
            "duration_ms": sum(r.duration_ms for r in phase_responses),
            "retries": sum(r.retry_count for r in phase_responses),
        }

    def get_all_phases(self) -> list[str]:
        """Get list of all unique phases in this deliberation.

        Returns:
            Sorted list of phase names
        """
        phases = {r.phase for r in self.responses if r.phase}
        return sorted(phases)

    def export_report(self) -> dict[str, Any]:
        """Export comprehensive metrics report.

        Returns:
            Dictionary with complete metrics breakdown
        """
        return {
            "session_id": self.session_id,
            "summary": {
                "total_cost": self.total_cost,
                "total_tokens": self.total_tokens,
                "total_calls": self.call_count,
                "total_duration_ms": self.total_duration_ms,
                "total_retries": self.total_retries,
                "cache_savings": self.total_cache_savings,
                "avg_cache_hit_rate": self.avg_cache_hit_rate,
            },
            "tokens": {
                "input": self.total_input_tokens,
                "output": self.total_output_tokens,
                "cache_read": self.total_cache_read_tokens,
                "total": self.total_tokens,
            },
            "phases": {phase: self.get_phase_metrics(phase) for phase in self.get_all_phases()},
            "responses": [r.to_dict() for r in self.responses],
        }

    def export_json(self) -> str:
        """Export report as JSON string.

        Returns:
            JSON string with complete metrics
        """
        return json.dumps(self.export_report(), indent=2)

    def export_csv_summary(self) -> str:
        """Export phase summary as CSV.

        Returns:
            CSV string with per-phase metrics
        """
        lines = ["phase,calls,tokens,cost,duration_ms,retries"]
        for phase in self.get_all_phases():
            metrics = self.get_phase_metrics(phase)
            lines.append(
                f"{phase},{metrics['calls']},{metrics['tokens']},"
                f"{metrics['cost']:.6f},{metrics['duration_ms']},{metrics['retries']}"
            )
        return "\n".join(lines)
