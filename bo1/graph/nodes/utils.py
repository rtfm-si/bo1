"""Shared utility functions for graph nodes.

This module contains helper functions used across multiple node modules,
including retry logic, phase determination, prompt helpers, and node timing.
"""

import asyncio
import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from anthropic import APIConnectionError, APITimeoutError

logger = logging.getLogger(__name__)

# Optional metrics import (fails gracefully in CLI)
try:
    from backend.api.metrics import metrics as _metrics
except ImportError:
    _metrics = None  # type: ignore[assignment]


def emit_node_duration(node_name: str, duration_ms: float) -> None:
    """Emit histogram metric for graph node execution duration.

    Args:
        node_name: Name of the node (e.g., "decompose_node")
        duration_ms: Execution time in milliseconds
    """
    if _metrics is not None:
        _metrics.observe(f"graph.node.{node_name}.duration_ms", duration_ms)
        _metrics.observe("graph.node.duration_ms", duration_ms)
    logger.debug(f"Node {node_name} completed in {duration_ms:.1f}ms")


@contextmanager
def node_timer(node_name: str) -> Generator[None, None, None]:
    """Context manager for timing graph node execution.

    Emits `graph.node.{node_name}.duration_ms` and `graph.node.duration_ms`
    histogram metrics on exit.

    Args:
        node_name: Name of the node being timed

    Example:
        >>> with node_timer("decompose_node"):
        ...     await do_decomposition()
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        emit_node_duration(node_name, duration_ms)


def log_with_session(
    log: logging.Logger,
    level: int,
    session_id: str | None,
    msg: str,
    request_id: str | None = None,
    **kwargs: Any,
) -> None:
    """Log message with session and request correlation IDs.

    Args:
        log: Logger instance to use
        level: Logging level (e.g., logging.INFO)
        session_id: Session ID for correlation (truncated to 8 chars)
        msg: Log message
        request_id: HTTP request ID for cross-system correlation
        **kwargs: Extra fields for structured logging
    """
    sid = (session_id or "unknown")[:8]
    rid = request_id[:8] if request_id else None
    if rid:
        formatted_msg = f"[session={sid}][request={rid}] {msg}"
    else:
        formatted_msg = f"[session={sid}] {msg}"
    log.log(level, formatted_msg, **kwargs)


async def retry_with_backoff(
    func: Any,
    *args: Any,
    max_retries: int = 3,
    initial_delay: float = 2.0,
    backoff_factor: float = 2.0,
    **kwargs: Any,
) -> Any:
    """Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Positional arguments to pass to func
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds before first retry (default: 2.0)
        backoff_factor: Multiplier for delay on each retry (default: 2.0)
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result from successful function call

    Raises:
        The last exception if all retries fail

    Example:
        >>> result = await retry_with_backoff(_deliberate_subproblem, sub_problem, problem, ...)
        # Tries up to 3 times with delays: 2s, 4s, 8s
    """
    last_exception = None
    delay = initial_delay

    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            return await func(*args, **kwargs)
        except (TimeoutError, APITimeoutError, APIConnectionError) as e:
            last_exception = e

            if attempt < max_retries:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed with {type(e).__name__}: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(
                    f"All {max_retries + 1} attempts failed for {func.__name__}. Last error: {e}"
                )
                raise
        except Exception as e:
            # Don't retry on non-timeout errors (e.g., validation errors, logic errors)
            logger.error(f"Non-retryable error in {func.__name__}: {type(e).__name__}: {e}")
            raise

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception


def phase_prompt_short(phase: str) -> str:
    """Get simplified phase prompt for retry attempts."""
    if phase == "exploration":
        return "Share your key insights and concerns."
    elif phase == "challenge":
        return "Challenge an assumption or add new evidence."
    elif phase == "convergence":
        return "Provide your recommendation and main reason."
    else:
        return "Provide your expert analysis."


def get_phase_prompt(phase: str, round_number: int) -> str:
    """Get phase-specific speaker prompts.

    From MEETING_SYSTEM_ANALYSIS.md, these prompts enforce:
    - 80-token max (prevents rambling)
    - Explicit phase objectives
    - No generic agreement without new information

    Args:
        phase: "exploration", "challenge", or "convergence"
        round_number: Current round number

    Returns:
        Speaker prompt string
    """
    if phase == "exploration":
        return (
            "EXPLORATION PHASE: Surface new perspectives, risks, and opportunities. "
            "Challenge assumptions. Identify gaps in analysis. "
            "Max 80 tokens. No agreement statements without new information."
        )

    elif phase == "challenge":
        return (
            "CHALLENGE PHASE: Directly challenge a previous point OR provide new evidence. "
            "Must either disagree with a specific claim or add novel data. "
            "Max 80 tokens. No summaries or meta-commentary."
        )

    elif phase == "convergence":
        return (
            "CONVERGENCE PHASE: Provide your strongest recommendation, key risk, and "
            "reason it outweighs alternatives. Be specific. "
            "Max 80 tokens. No further debate."
        )

    else:
        return "Provide your contribution based on your expertise."
