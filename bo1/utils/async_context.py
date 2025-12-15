"""Async context propagation utilities for correlation ID tracing.

Provides helpers to preserve contextvars (like correlation_id) across
asyncio.create_task() boundaries, which otherwise lose context.

Usage:
    from bo1.utils.async_context import create_task_with_context

    # Instead of: asyncio.create_task(my_coro())
    # Use:
    create_task_with_context(my_coro())
"""

import asyncio
from collections.abc import Coroutine
from contextvars import copy_context
from functools import wraps
from typing import Any, TypeVar

T = TypeVar("T")


def create_task_with_context(  # noqa: UP047
    coro: Coroutine[Any, Any, T],
    *,
    name: str | None = None,
) -> asyncio.Task[T]:
    """Create an asyncio.Task that preserves the current context.

    Standard asyncio.create_task() does not copy contextvars to the new task,
    causing correlation IDs and other context to be lost. This wrapper uses
    copy_context() to preserve all contextvars.

    Args:
        coro: Coroutine to schedule as a task
        name: Optional name for the task (passed to asyncio.create_task)

    Returns:
        asyncio.Task with context preserved

    Example:
        >>> from bo1.utils.logging import set_correlation_id, get_correlation_id
        >>> set_correlation_id("req-123")
        >>> async def background_work():
        ...     # This will correctly see "req-123"
        ...     print(get_correlation_id())
        >>> create_task_with_context(background_work())
    """
    ctx = copy_context()

    async def wrapped() -> T:
        return await coro

    # Run the coroutine within the copied context
    return asyncio.create_task(ctx.run(_run_in_context, wrapped), name=name)


async def _run_in_context(coro_factory: Any) -> Any:
    """Helper to run a coroutine factory within a context.

    Args:
        coro_factory: Async callable that returns a coroutine

    Returns:
        Result of the coroutine
    """
    return await coro_factory()


def preserve_context(func: Any) -> Any:
    """Decorator that preserves context across async function calls.

    Use this when you need to ensure an async function always runs with
    the context it was called with, even when awaited later.

    Args:
        func: Async function to wrap

    Returns:
        Wrapped async function that preserves context

    Example:
        >>> @preserve_context
        ... async def process_item(item):
        ...     # Will see correlation_id from call site, not execution site
        ...     log_with_context(logger, INFO, "Processing", item_id=item.id)
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        ctx = copy_context()
        return await ctx.run(_run_async_in_context, func, *args, **kwargs)

    return wrapper


async def _run_async_in_context(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Helper to run an async function within context.

    Args:
        func: Async function to call
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result of the async function
    """
    return await func(*args, **kwargs)
