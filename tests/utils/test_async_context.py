"""Tests for async context propagation utilities."""

import asyncio
from contextvars import ContextVar

import pytest

from bo1.utils.async_context import create_task_with_context, preserve_context
from bo1.utils.logging import get_correlation_id, set_correlation_id


class TestCreateTaskWithContext:
    """Tests for create_task_with_context function."""

    @pytest.mark.asyncio
    async def test_context_preserved_in_task(self) -> None:
        """Correlation ID should be visible in background task."""
        set_correlation_id("test-correlation-123")
        result_id: str | None = None

        async def background_work() -> None:
            nonlocal result_id
            result_id = get_correlation_id()

        task = create_task_with_context(background_work())
        await task

        assert result_id == "test-correlation-123"

    @pytest.mark.asyncio
    async def test_context_isolated_between_tasks(self) -> None:
        """Different tasks should have their own context copies."""
        results: dict[str, str | None] = {}

        async def capture_id(key: str) -> None:
            results[key] = get_correlation_id()

        # Set context for first task
        set_correlation_id("id-1")
        task1 = create_task_with_context(capture_id("task1"))

        # Change context for second task
        set_correlation_id("id-2")
        task2 = create_task_with_context(capture_id("task2"))

        await asyncio.gather(task1, task2)

        # Each task should have its own copy of context at creation time
        assert results["task1"] == "id-1"
        assert results["task2"] == "id-2"

    @pytest.mark.asyncio
    async def test_nested_context_preservation(self) -> None:
        """Context should propagate through nested task creation."""
        set_correlation_id("parent-correlation")
        nested_id: str | None = None

        async def outer() -> None:
            nonlocal nested_id

            async def inner() -> None:
                nonlocal nested_id
                nested_id = get_correlation_id()

            inner_task = create_task_with_context(inner())
            await inner_task

        task = create_task_with_context(outer())
        await task

        assert nested_id == "parent-correlation"

    @pytest.mark.asyncio
    async def test_standard_create_task_loses_context(self) -> None:
        """Standard asyncio.create_task should NOT preserve context (regression test)."""
        set_correlation_id("should-be-lost")
        result_id: str | None = "placeholder"

        async def background_work() -> None:
            nonlocal result_id
            result_id = get_correlation_id()

        # Clear context before creating task (simulating context switch)
        set_correlation_id(None)

        # Standard create_task should see None
        task = asyncio.create_task(background_work())
        await task

        assert result_id is None

    @pytest.mark.asyncio
    async def test_custom_contextvar_preserved(self) -> None:
        """Custom ContextVars beyond correlation_id should also be preserved."""
        custom_var: ContextVar[str | None] = ContextVar("custom_var", default=None)
        custom_var.set("custom-value")
        result: str | None = None

        async def check_custom() -> None:
            nonlocal result
            result = custom_var.get()

        task = create_task_with_context(check_custom())
        await task

        assert result == "custom-value"

    @pytest.mark.asyncio
    async def test_task_name_passed_through(self) -> None:
        """Task name should be passed to the underlying asyncio.Task."""

        async def dummy() -> None:
            pass

        task = create_task_with_context(dummy(), name="my-named-task")
        assert task.get_name() == "my-named-task"
        await task

    @pytest.mark.asyncio
    async def test_return_value_propagated(self) -> None:
        """Return value from coroutine should be accessible."""
        set_correlation_id("test-id")

        async def return_value() -> str:
            return f"result-{get_correlation_id()}"

        task = create_task_with_context(return_value())
        result = await task

        assert result == "result-test-id"


class TestPreserveContextDecorator:
    """Tests for @preserve_context decorator."""

    @pytest.mark.asyncio
    async def test_decorator_preserves_context(self) -> None:
        """Decorated function should see context from call site."""
        captured_id: str | None = None

        @preserve_context
        async def decorated_func() -> None:
            nonlocal captured_id
            captured_id = get_correlation_id()

        set_correlation_id("decorator-test-id")
        await decorated_func()

        assert captured_id == "decorator-test-id"

    @pytest.mark.asyncio
    async def test_decorator_with_args(self) -> None:
        """Decorated function should receive arguments correctly."""
        captured: dict[str, str | None] = {}

        @preserve_context
        async def with_args(key: str, value: str) -> None:
            captured["key"] = key
            captured["value"] = value
            captured["corr_id"] = get_correlation_id()

        set_correlation_id("args-test")
        await with_args("my-key", "my-value")

        assert captured == {"key": "my-key", "value": "my-value", "corr_id": "args-test"}

    @pytest.mark.asyncio
    async def test_decorator_with_return(self) -> None:
        """Decorated function should return values correctly."""

        @preserve_context
        async def returns_value() -> str:
            return f"id={get_correlation_id()}"

        set_correlation_id("return-test")
        result = await returns_value()

        assert result == "id=return-test"
