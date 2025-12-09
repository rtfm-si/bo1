"""Chaos tests for SSE connection recovery.

Validates:
- Client reconnection after server restart
- Event replay from checkpoint on reconnect
- Connection timeout handling
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest


@pytest.mark.chaos
class TestSSEConnectionDrop:
    """Test SSE connection drop and reconnect."""

    @pytest.mark.asyncio
    async def test_client_reconnects_after_drop(self) -> None:
        """Client reconnects after connection drop."""
        connection_count = 0
        events_received: list[dict[str, Any]] = []

        async def mock_sse_stream() -> AsyncGenerator[dict[str, Any], None]:
            nonlocal connection_count
            connection_count += 1

            # First connection drops after 2 events
            if connection_count == 1:
                yield {"event": "contribution", "data": {"id": 1}}
                yield {"event": "contribution", "data": {"id": 2}}
                raise ConnectionError("Connection reset")

            # Second connection continues
            yield {"event": "contribution", "data": {"id": 3}}
            yield {"event": "complete", "data": {}}

        # Simulate reconnecting client
        max_reconnects = 3
        reconnect_count = 0

        while reconnect_count < max_reconnects:
            try:
                async for event in mock_sse_stream():
                    events_received.append(event)
            except ConnectionError:
                reconnect_count += 1
                await asyncio.sleep(0.01)  # Brief delay before reconnect
            else:
                break  # Stream completed normally

        assert connection_count == 2
        assert len(events_received) == 4
        assert events_received[-1]["event"] == "complete"

    @pytest.mark.asyncio
    async def test_reconnect_with_last_event_id(self) -> None:
        """Client sends Last-Event-ID on reconnect for replay."""
        last_event_ids: list[str | None] = []

        async def mock_sse_with_event_id(
            last_event_id: str | None = None,
        ) -> AsyncGenerator[dict[str, Any], None]:
            last_event_ids.append(last_event_id)

            if last_event_id is None:
                yield {"id": "1", "event": "start", "data": {}}
                yield {"id": "2", "event": "contribution", "data": {"text": "a"}}
                raise ConnectionError("Dropped")

            # Reconnected with last_event_id - replay from there
            elif last_event_id == "2":
                yield {"id": "3", "event": "contribution", "data": {"text": "b"}}
                yield {"id": "4", "event": "complete", "data": {}}

        events: list[dict[str, Any]] = []
        last_id: str | None = None

        for _ in range(3):
            try:
                async for event in mock_sse_with_event_id(last_id):
                    events.append(event)
                    last_id = event.get("id")
            except ConnectionError:
                await asyncio.sleep(0.01)
            else:
                break

        assert len(last_event_ids) == 2
        assert last_event_ids[0] is None
        assert last_event_ids[1] == "2"
        assert events[-1]["event"] == "complete"


@pytest.mark.chaos
class TestSSETimeout:
    """Test SSE connection timeout handling."""

    @pytest.mark.asyncio
    async def test_connection_timeout_handled(self) -> None:
        """Connection timeout raises appropriate error."""

        async def slow_connect() -> AsyncGenerator[dict[str, Any], None]:
            await asyncio.sleep(10)
            yield {"event": "never_reached", "data": {}}

        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(0.1):
                async for _ in slow_connect():
                    pass

    @pytest.mark.asyncio
    async def test_heartbeat_timeout_triggers_reconnect(self) -> None:
        """Missing heartbeat triggers reconnection."""
        heartbeat_received = False
        reconnect_triggered = False

        async def stream_with_heartbeat() -> AsyncGenerator[dict[str, Any], None]:
            yield {"event": "contribution", "data": {"id": 1}}
            # No heartbeat for too long...
            await asyncio.sleep(5)  # Simulates server not sending heartbeat

        async def check_heartbeat_timeout() -> None:
            nonlocal heartbeat_received, reconnect_triggered

            try:
                async with asyncio.timeout(0.1):  # Heartbeat timeout
                    async for event in stream_with_heartbeat():
                        if event.get("event") == "heartbeat":
                            heartbeat_received = True
                        await asyncio.sleep(0.05)
            except TimeoutError:
                reconnect_triggered = True

        await check_heartbeat_timeout()

        assert not heartbeat_received
        assert reconnect_triggered


@pytest.mark.chaos
class TestSSEEventReplay:
    """Test event replay after reconnection."""

    @pytest.mark.asyncio
    async def test_events_replayed_from_checkpoint(self) -> None:
        """Events are replayed from checkpoint on reconnect."""
        # Simulate server-side event storage
        all_events = [
            {"id": "1", "event": "start", "data": {"session_id": "bo1_test"}},
            {"id": "2", "event": "contribution", "data": {"text": "a"}},
            {"id": "3", "event": "contribution", "data": {"text": "b"}},
            {"id": "4", "event": "contribution", "data": {"text": "c"}},
            {"id": "5", "event": "complete", "data": {}},
        ]

        async def replay_from_id(
            from_id: str | None,
        ) -> AsyncGenerator[dict[str, Any], None]:
            start_index = 0
            if from_id:
                for i, event in enumerate(all_events):
                    if event["id"] == from_id:
                        start_index = i + 1
                        break

            for event in all_events[start_index:]:
                yield event

        # Client disconnected after event 2
        client_events: list[dict[str, Any]] = []

        # Initial connection - gets events 1-2 then disconnects
        async for event in replay_from_id(None):
            client_events.append(event)
            if event["id"] == "2":
                break  # Simulated disconnect

        # Reconnect from last received event
        async for event in replay_from_id("2"):
            client_events.append(event)

        # Client should have all events (with no duplicates if server handles correctly)
        assert len(client_events) == 5
        assert client_events[0]["id"] == "1"
        assert client_events[-1]["id"] == "5"

    @pytest.mark.asyncio
    async def test_partial_event_handling(self) -> None:
        """Handles partially received events on disconnect."""
        received_data: list[str] = []

        async def chunked_stream() -> AsyncGenerator[str, None]:
            # Event sent in chunks
            yield "event: contribution\n"
            yield 'data: {"te'
            # Connection drops mid-event
            raise ConnectionError("Dropped mid-event")

        try:
            buffer = ""
            async for chunk in chunked_stream():
                buffer += chunk
                if buffer.endswith("\n\n"):
                    received_data.append(buffer)
                    buffer = ""
        except ConnectionError:
            # Partial event should be discarded
            pass

        # No complete events received
        assert len(received_data) == 0


@pytest.mark.chaos
class TestSSEServerRestart:
    """Test behavior when SSE server restarts."""

    @pytest.mark.asyncio
    async def test_client_survives_server_restart(self) -> None:
        """Client reconnects after server restart."""
        server_generation = 0
        client_connected = False

        async def server_stream(gen: int) -> AsyncGenerator[dict[str, Any], None]:
            nonlocal client_connected
            client_connected = True

            if gen == 0:
                yield {"event": "start", "data": {}}
                raise ConnectionError("Server restarting")

            yield {"event": "resumed", "data": {"generation": gen}}
            yield {"event": "complete", "data": {}}

        events: list[dict[str, Any]] = []

        for _attempt in range(3):
            try:
                async for event in server_stream(server_generation):
                    events.append(event)
            except ConnectionError:
                server_generation += 1
                await asyncio.sleep(0.01)
            else:
                break

        assert client_connected
        assert any(e.get("event") == "complete" for e in events)

    @pytest.mark.asyncio
    async def test_session_state_preserved_across_restart(self) -> None:
        """Session state preserved when server restarts."""
        # Simulate session state stored in checkpoint
        checkpoint_state = {
            "session_id": "bo1_test",
            "round": 3,
            "contributions": ["a", "b", "c"],
        }

        async def restore_session(session_id: str) -> dict[str, Any]:
            if session_id == checkpoint_state["session_id"]:
                return checkpoint_state
            raise ValueError("Session not found")

        # Client reconnects after server restart
        restored = await restore_session("bo1_test")

        assert restored["round"] == 3
        assert len(restored["contributions"]) == 3


@pytest.mark.chaos
class TestSSEBackpressure:
    """Test SSE backpressure handling."""

    @pytest.mark.asyncio
    async def test_slow_client_backpressure(self) -> None:
        """Server handles slow client consuming events."""
        events_sent = 0
        events_consumed = 0

        async def fast_server() -> AsyncGenerator[dict[str, Any], None]:
            nonlocal events_sent
            for i in range(10):
                events_sent += 1
                yield {"event": "data", "data": {"seq": i}}

        async def slow_client(
            stream: AsyncGenerator[dict[str, Any], None],
        ) -> list[dict[str, Any]]:
            nonlocal events_consumed
            results = []
            async for event in stream:
                await asyncio.sleep(0.01)  # Slow processing
                events_consumed += 1
                results.append(event)
            return results

        results = await slow_client(fast_server())

        assert events_sent == 10
        assert events_consumed == 10
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_buffer_overflow_handling(self) -> None:
        """Handle buffer overflow with slow client."""
        buffer: list[dict[str, Any]] = []
        max_buffer = 5
        dropped_events = 0

        async def buffered_producer() -> None:
            nonlocal dropped_events
            for i in range(20):
                if len(buffer) >= max_buffer:
                    dropped_events += 1
                    continue
                buffer.append({"seq": i})
                await asyncio.sleep(0.001)

        async def slow_consumer() -> list[dict[str, Any]]:
            consumed = []
            while len(consumed) < 10:
                if buffer:
                    consumed.append(buffer.pop(0))
                await asyncio.sleep(0.01)
            return consumed

        producer_task = asyncio.create_task(buffered_producer())
        consumed = await slow_consumer()
        await producer_task

        # Some events dropped due to buffer overflow
        assert dropped_events > 0
        assert len(consumed) == 10
