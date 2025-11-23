"""Tests for standardized logging utilities."""

import logging
from io import StringIO

import pytest

from bo1.utils.logging import (
    get_logger,
    log_cache_operation,
    log_error_with_context,
    log_llm_call,
    log_with_context,
)


@pytest.fixture
def capture_logs():
    """Capture log output to a string buffer."""
    log_buffer = StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setFormatter(logging.Formatter("%(levelname)s - %(name)s - %(message)s"))

    yield log_buffer, handler

    handler.close()


def test_get_logger_creates_configured_logger():
    """Test that get_logger returns a properly configured logger."""
    logger = get_logger("test.module")

    assert logger.name == "test.module"
    assert logger.level == logging.INFO
    assert len(logger.handlers) > 0


def test_get_logger_custom_level():
    """Test that get_logger respects custom log level."""
    logger = get_logger("test.module.debug", level=logging.DEBUG)

    assert logger.level == logging.DEBUG


def test_log_with_context_no_context(capture_logs):
    """Test log_with_context with no additional context."""
    log_buffer, handler = capture_logs
    logger = logging.getLogger("test.context")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    log_with_context(logger, logging.INFO, "Simple message")

    output = log_buffer.getvalue()
    assert "Simple message" in output
    assert "|" not in output  # No context separator


def test_log_with_context_with_fields(capture_logs):
    """Test log_with_context with structured fields."""
    log_buffer, handler = capture_logs
    logger = logging.getLogger("test.context.fields")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    log_with_context(
        logger, logging.INFO, "Session started", session_id="abc123", user_id="user456"
    )

    output = log_buffer.getvalue()
    assert "Session started" in output
    assert "session_id=abc123" in output
    assert "user_id=user456" in output
    assert "|" in output


def test_log_llm_call(capture_logs):
    """Test LLM call logging with metrics."""
    log_buffer, handler = capture_logs
    logger = logging.getLogger("test.llm")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    log_llm_call(
        logger,
        model="claude-sonnet-4.5",
        prompt_tokens=1500,
        completion_tokens=300,
        cost=0.0045,
        duration_ms=2340.5,
        agent="selector",
        phase="selection",
    )

    output = log_buffer.getvalue()
    assert "LLM call complete" in output
    assert "model=claude-sonnet-4.5" in output
    assert "prompt_tokens=1500" in output
    assert "completion_tokens=300" in output
    assert "cost=$0.0045" in output
    assert "duration_ms=2340.5" in output
    assert "agent=selector" in output
    assert "phase=selection" in output


def test_log_cache_operation_hit(capture_logs):
    """Test cache operation logging for cache hit."""
    log_buffer, handler = capture_logs
    logger = logging.getLogger("test.cache")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    log_cache_operation(
        logger, operation="get", cache_type="persona", hit=True, key="persona_selector_abc123"
    )

    output = log_buffer.getvalue()
    assert "Cache HIT" in output
    assert "operation=get" in output
    assert "cache_type=persona" in output
    assert "key=persona_selector_abc123" in output


def test_log_cache_operation_miss(capture_logs):
    """Test cache operation logging for cache miss."""
    log_buffer, handler = capture_logs
    logger = logging.getLogger("test.cache.miss")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    log_cache_operation(logger, operation="get", cache_type="research", hit=False)

    output = log_buffer.getvalue()
    assert "Cache MISS" in output
    assert "operation=get" in output
    assert "cache_type=research" in output


def test_log_error_with_context(capture_logs):
    """Test error logging with structured context."""
    log_buffer, handler = capture_logs
    logger = logging.getLogger("test.error")
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)

    error = ValueError("Invalid input")
    log_error_with_context(
        logger, error, "Failed to process session", session_id="abc123", user_id="user456"
    )

    output = log_buffer.getvalue()
    assert "Failed to process session" in output
    assert "error_type=ValueError" in output
    assert "error=Invalid input" in output
    assert "session_id=abc123" in output
    assert "user_id=user456" in output
