"""Tests for checkpoint logging wrapper (P1: observability)."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logging_checkpointer_aput_logs_size_and_latency(caplog):
    """Test that aput logs checkpoint size and latency."""
    from bo1.graph.checkpointer import LoggingCheckpointerWrapper

    caplog.set_level(logging.INFO)

    # Create mock checkpointer
    mock_checkpointer = AsyncMock()
    mock_checkpointer.aput.return_value = {"success": True}

    wrapper = LoggingCheckpointerWrapper(mock_checkpointer)

    config = {"configurable": {"thread_id": "test-session-123"}}
    checkpoint = {"state": {"key": "value"}}
    metadata = {"step": 1}

    result = await wrapper.aput(config, checkpoint, metadata)

    # Verify underlying method was called
    mock_checkpointer.aput.assert_called_once_with(config, checkpoint, metadata, None)
    assert result == {"success": True}

    # Verify logging
    assert "[CHECKPOINT PUT]" in caplog.text
    assert "session=test-session-123" in caplog.text
    assert "size_bytes=" in caplog.text
    assert "latency_ms=" in caplog.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logging_checkpointer_aget_logs_found(caplog):
    """Test that aget logs when checkpoint is found."""
    from bo1.graph.checkpointer import LoggingCheckpointerWrapper

    caplog.set_level(logging.INFO)

    mock_checkpointer = AsyncMock()
    mock_checkpointer.aget.return_value = {"checkpoint": "data"}

    wrapper = LoggingCheckpointerWrapper(mock_checkpointer)
    config = {"configurable": {"thread_id": "test-session-456"}}

    result = await wrapper.aget(config)

    mock_checkpointer.aget.assert_called_once_with(config)
    assert result == {"checkpoint": "data"}

    assert "[CHECKPOINT GET]" in caplog.text
    assert "session=test-session-456" in caplog.text
    assert "found=True" in caplog.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logging_checkpointer_aget_logs_not_found(caplog):
    """Test that aget logs when checkpoint is not found."""
    from bo1.graph.checkpointer import LoggingCheckpointerWrapper

    caplog.set_level(logging.INFO)

    mock_checkpointer = AsyncMock()
    mock_checkpointer.aget.return_value = None

    wrapper = LoggingCheckpointerWrapper(mock_checkpointer)
    config = {"configurable": {"thread_id": "test-session-789"}}

    result = await wrapper.aget(config)

    assert result is None
    assert "[CHECKPOINT GET]" in caplog.text
    assert "found=False" in caplog.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logging_checkpointer_aput_logs_error(caplog):
    """Test that aput logs errors with full context."""
    from bo1.graph.checkpointer import LoggingCheckpointerWrapper

    caplog.set_level(logging.ERROR)

    mock_checkpointer = AsyncMock()
    mock_checkpointer.aput.side_effect = ConnectionError("Redis connection failed")

    wrapper = LoggingCheckpointerWrapper(mock_checkpointer)
    config = {"configurable": {"thread_id": "error-session"}}

    with pytest.raises(ConnectionError, match="Redis connection failed"):
        await wrapper.aput(config, {}, {})

    assert "[CHECKPOINT PUT ERROR]" in caplog.text
    assert "session=error-session" in caplog.text
    assert "ConnectionError" in caplog.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logging_checkpointer_aget_logs_error(caplog):
    """Test that aget logs errors with full context."""
    from bo1.graph.checkpointer import LoggingCheckpointerWrapper

    caplog.set_level(logging.ERROR)

    mock_checkpointer = AsyncMock()
    mock_checkpointer.aget.side_effect = TimeoutError("Redis timeout")

    wrapper = LoggingCheckpointerWrapper(mock_checkpointer)
    config = {"configurable": {"thread_id": "timeout-session"}}

    with pytest.raises(TimeoutError, match="Redis timeout"):
        await wrapper.aget(config)

    assert "[CHECKPOINT GET ERROR]" in caplog.text
    assert "session=timeout-session" in caplog.text
    assert "TimeoutError" in caplog.text


@pytest.mark.unit
def test_logging_checkpointer_delegates_unknown_attributes():
    """Test that wrapper delegates unknown attributes to underlying checkpointer."""
    from bo1.graph.checkpointer import LoggingCheckpointerWrapper

    mock_checkpointer = MagicMock()
    mock_checkpointer.custom_method.return_value = "custom_result"
    mock_checkpointer.custom_attr = "custom_value"

    wrapper = LoggingCheckpointerWrapper(mock_checkpointer)

    # Access custom method through delegation
    assert wrapper.custom_method() == "custom_result"
    assert wrapper.custom_attr == "custom_value"
