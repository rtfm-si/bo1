"""Integration tests for correlation ID propagation through async boundaries."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from bo1.utils.async_context import create_task_with_context
from bo1.utils.logging import get_correlation_id, set_correlation_id


class TestCorrelationIdPropagation:
    """Tests verifying correlation ID flows through the request lifecycle."""

    @pytest.mark.asyncio
    async def test_correlation_flows_to_background_notification(self) -> None:
        """Correlation ID should propagate to fire-and-forget notification tasks."""
        captured_ids: list[str | None] = []

        async def mock_notify(*args, **kwargs) -> None:
            captured_ids.append(get_correlation_id())

        set_correlation_id("req-notify-test")

        # Simulate fire-and-forget pattern used in event_collector
        task = create_task_with_context(mock_notify())
        await task

        assert captured_ids == ["req-notify-test"]

    @pytest.mark.asyncio
    async def test_correlation_in_nested_background_tasks(self) -> None:
        """Correlation ID should propagate through multiple task levels."""
        captured_ids: list[str | None] = []

        async def level_2() -> None:
            captured_ids.append(("level_2", get_correlation_id()))

        async def level_1() -> None:
            captured_ids.append(("level_1", get_correlation_id()))
            inner_task = create_task_with_context(level_2())
            await inner_task

        set_correlation_id("nested-task-id")
        task = create_task_with_context(level_1())
        await task

        assert captured_ids == [("level_1", "nested-task-id"), ("level_2", "nested-task-id")]

    @pytest.mark.asyncio
    async def test_parallel_tasks_maintain_own_correlation(self) -> None:
        """Concurrent tasks should maintain their own correlation context."""
        results: dict[str, str | None] = {}
        barrier = asyncio.Barrier(2)

        async def worker(name: str) -> None:
            await barrier.wait()  # Ensure concurrent execution
            results[name] = get_correlation_id()

        # Create tasks with different correlation IDs
        set_correlation_id("worker-A-id")
        task_a = create_task_with_context(worker("A"))

        set_correlation_id("worker-B-id")
        task_b = create_task_with_context(worker("B"))

        await asyncio.gather(task_a, task_b)

        # Each worker should see its own correlation ID
        assert results["A"] == "worker-A-id"
        assert results["B"] == "worker-B-id"

    @pytest.mark.asyncio
    async def test_session_manager_preserves_context(self) -> None:
        """SessionManager.start_session should preserve correlation ID in execution task."""
        from bo1.graph.execution import SessionManager

        captured_correlation: str | None = None

        async def mock_execution() -> dict:
            nonlocal captured_correlation
            captured_correlation = get_correlation_id()
            return {"status": "completed"}

        # Create minimal session manager
        redis_manager = MagicMock()
        redis_manager.get_session_metadata.return_value = {}
        manager = SessionManager(redis_manager=redis_manager)

        # Patch _load_session_metadata to return valid data
        with patch.object(manager, "_load_session_metadata", return_value={"user_id": "user-1"}):
            with patch.object(manager, "_update_session_status"):
                set_correlation_id("session-mgr-correlation")
                task = await manager.start_session(
                    session_id="test-session",
                    user_id="user-1",
                    coro=mock_execution(),
                )
                await task

        assert captured_correlation == "session-mgr-correlation"

    @pytest.mark.asyncio
    async def test_middleware_sets_correlation_id(self) -> None:
        """CorrelationIdMiddleware should set correlation_id in contextvars."""
        from starlette.requests import Request

        from backend.api.middleware.correlation_id import CorrelationIdMiddleware

        captured_id: str | None = None

        async def capture_handler(request: Request) -> None:
            nonlocal captured_id
            captured_id = get_correlation_id()
            from starlette.responses import JSONResponse

            return JSONResponse({"status": "ok"})

        # Create minimal ASGI app with middleware
        from starlette.applications import Starlette
        from starlette.routing import Route

        app = Starlette(routes=[Route("/test", capture_handler)])
        app = CorrelationIdMiddleware(app)

        # Test with provided header
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [(b"x-request-id", b"provided-correlation-123")],
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        response_started = False

        async def send(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True

        await app(scope, receive, send)

        assert captured_id == "provided-correlation-123"
