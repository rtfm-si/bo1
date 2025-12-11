"""Tests for ContributionSummarizer service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic import APIError, RateLimitError

from backend.api.contribution_summarizer import (
    SUMMARIZATION_CONCURRENCY_LIMIT,
    ContributionSummarizer,
)


@pytest.fixture
def mock_anthropic_client():
    """Create mock Anthropic client."""
    return MagicMock()


@pytest.fixture
def summarizer(mock_anthropic_client):
    """Create summarizer with mock client."""
    return ContributionSummarizer(mock_anthropic_client)


# ============================================================================
# Basic Summarization Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_success(summarizer):
    """Test successful summarization returns validated dict."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text='"concise": "Test summary", "looking_for": "Analysis", '
            '"value_added": "Insight", "concerns": [], "questions": []}'
        )
    ]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.stop_reason = "end_turn"

    summarizer.client.messages.create = AsyncMock(return_value=mock_response)

    with patch("backend.api.contribution_summarizer.get_cost_context", return_value={}):
        with patch("backend.api.contribution_summarizer.CostTracker.track_call"):
            result = await summarizer.summarize("Test content", "Expert A")

    assert result is not None
    assert result["concise"] == "Test summary"
    assert result.get("schema_valid", True)  # Valid schema


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_returns_fallback_on_parse_error(summarizer):
    """Test unparseable response returns fallback summary."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json at all")]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.stop_reason = "end_turn"

    summarizer.client.messages.create = AsyncMock(return_value=mock_response)

    with patch("backend.api.contribution_summarizer.get_cost_context", return_value={}):
        with patch("backend.api.contribution_summarizer.CostTracker.track_call"):
            result = await summarizer.summarize("Test content", "Expert A")

    assert result is not None
    assert result.get("parse_error") is True


# ============================================================================
# Retry Logic Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_retries_on_api_error(summarizer):
    """Test _call_llm retries on transient API errors."""
    call_count = 0

    async def mock_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise APIError(
                message="Server error",
                request=MagicMock(),
                body={"error": {"message": "Server error"}},
            )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='"concise": "Test summary"}')]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.stop_reason = "end_turn"
        return mock_response

    summarizer.client.messages.create = AsyncMock(side_effect=mock_create)

    with patch("backend.api.contribution_summarizer.get_cost_context", return_value={}):
        with patch("backend.api.contribution_summarizer.CostTracker.track_call"):
            result = await summarizer.summarize("Test content", "Expert A")

    assert call_count == 3
    assert result is not None
    assert "concise" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_falls_back_after_retries_exhausted(summarizer):
    """Test summarization falls back after all retries exhausted."""

    async def mock_create(*args, **kwargs):
        raise APIError(
            message="Persistent error",
            request=MagicMock(),
            body={"error": {"message": "Persistent error"}},
        )

    summarizer.client.messages.create = AsyncMock(side_effect=mock_create)

    with patch("backend.api.contribution_summarizer.get_cost_context", return_value={}):
        with patch("backend.api.contribution_summarizer.CostTracker.track_call"):
            result = await summarizer.summarize("Test content", "Expert A")

    assert result is not None
    assert result.get("parse_error") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_retries_on_rate_limit(summarizer):
    """Test retry on RateLimitError."""
    call_count = 0

    async def mock_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429),
                body={"error": {"message": "Rate limited"}},
            )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='"concise": "OK"}')]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.stop_reason = "end_turn"
        return mock_response

    summarizer.client.messages.create = AsyncMock(side_effect=mock_create)

    with patch("backend.api.contribution_summarizer.get_cost_context", return_value={}):
        with patch("backend.api.contribution_summarizer.CostTracker.track_call"):
            result = await summarizer.summarize("Test content", "Expert A")

    assert call_count == 2
    assert result is not None


# ============================================================================
# Batch Summarization Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_summarize_parallel(summarizer):
    """Test batch_summarize runs summaries in parallel."""

    async def mock_summarize(content, name):
        return {"concise": f"Summary for {name}", "looking_for": "", "value_added": ""}

    with patch.object(summarizer, "summarize", side_effect=mock_summarize):
        items = [
            ("Content 1", "Expert A"),
            ("Content 2", "Expert B"),
            ("Content 3", "Expert C"),
        ]
        results = await summarizer.batch_summarize(items)

    assert len(results) == 3
    assert results[0]["concise"] == "Summary for Expert A"
    assert results[1]["concise"] == "Summary for Expert B"
    assert results[2]["concise"] == "Summary for Expert C"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_summarize_handles_partial_failures(summarizer):
    """Test batch summarization handles individual failures gracefully."""
    call_count = 0

    async def mock_summarize(content, name):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise ValueError("Simulated LLM failure")
        return {"concise": f"Summary for {name}"}

    with patch.object(summarizer, "summarize", side_effect=mock_summarize):
        items = [
            ("Content 1", "Expert A"),
            ("Content 2", "Expert B"),
            ("Content 3", "Expert C"),
        ]
        results = await summarizer.batch_summarize(items)

    assert len(results) == 3
    assert results[0]["concise"] == "Summary for Expert A"
    assert results[1].get("parse_error") is True  # Fallback
    assert results[2]["concise"] == "Summary for Expert C"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_summarize_empty_list(summarizer):
    """Test batch summarization handles empty input."""
    results = await summarizer.batch_summarize([])
    assert results == []


@pytest.mark.unit
def test_concurrency_limit_constant():
    """Verify concurrency limit is set correctly."""
    assert SUMMARIZATION_CONCURRENCY_LIMIT == 5


# ============================================================================
# Schema Validation Tests
# ============================================================================


@pytest.mark.unit
def test_validate_schema_valid_input(summarizer):
    """Test validate_schema with valid input."""
    summary = {
        "concise": "Test summary",
        "looking_for": "Analysis",
        "value_added": "Insight",
        "concerns": ["Concern 1"],
        "questions": ["Question 1"],
    }
    result = summarizer.validate_schema(summary)
    assert result["concise"] == "Test summary"
    assert result.get("schema_valid", True)


@pytest.mark.unit
def test_validate_schema_invalid_input_falls_back(summarizer):
    """Test validate_schema returns safe dict on invalid input."""
    # Missing required fields, has wrong types
    summary = {
        "concise": "x" * 1000,  # Too long
        "concerns": "not a list",
    }
    result = summarizer.validate_schema(summary)
    assert result is not None
    assert result.get("schema_valid") is False
    assert len(result["concise"]) <= 500  # Truncated


@pytest.mark.unit
def test_validate_schema_coerces_string_concerns(summarizer):
    """Test schema validation coerces string concerns to list."""
    summary = {
        "concise": "Test",
        "looking_for": "Analysis",
        "value_added": "Insight",
        "concerns": "Single concern",  # String instead of list
        "questions": [],
    }
    result = summarizer.validate_schema(summary)
    # The Pydantic model coerces string to list
    assert isinstance(result["concerns"], list)


# ============================================================================
# Fallback Summary Tests
# ============================================================================


@pytest.mark.unit
def test_create_fallback_extracts_first_sentence(summarizer):
    """Test fallback extracts first sentence."""
    content = "This is the first sentence. This is the second."
    result = summarizer.create_fallback("Expert A", content)

    assert "This is the first sentence" in result["concise"]
    assert result["parse_error"] is True
    assert result["schema_valid"] is False


@pytest.mark.unit
def test_create_fallback_handles_empty_content(summarizer):
    """Test fallback handles empty content."""
    result = summarizer.create_fallback("Expert A", "")

    assert "Analysis by Expert A" in result["concise"]
    assert result["parse_error"] is True


@pytest.mark.unit
def test_create_fallback_truncates_long_sentence(summarizer):
    """Test fallback truncates very long first sentence."""
    content = "x" * 200 + ". Second sentence."
    result = summarizer.create_fallback("Expert A", content)

    # First sentence truncated to 100 chars
    assert len(result["concise"]) <= 104  # 100 + "..."


# ============================================================================
# JSON Extraction Tests
# ============================================================================


@pytest.mark.unit
def test_extract_first_json_object_simple(summarizer):
    """Test extraction of simple JSON object."""
    text = '{"key": "value"}'
    result = summarizer._extract_first_json_object(text)
    assert result == {"key": "value"}


@pytest.mark.unit
def test_extract_first_json_object_with_trailing_text(summarizer):
    """Test extraction ignores trailing text."""
    text = '{"key": "value"} some trailing text'
    result = summarizer._extract_first_json_object(text)
    assert result == {"key": "value"}


@pytest.mark.unit
def test_extract_first_json_object_nested(summarizer):
    """Test extraction of nested JSON."""
    text = '{"outer": {"inner": "value"}}'
    result = summarizer._extract_first_json_object(text)
    assert result == {"outer": {"inner": "value"}}


@pytest.mark.unit
def test_extract_first_json_object_no_json(summarizer):
    """Test returns None when no JSON found."""
    text = "no json here"
    result = summarizer._extract_first_json_object(text)
    assert result is None


@pytest.mark.unit
def test_extract_first_json_object_invalid_json(summarizer):
    """Test returns None for invalid JSON."""
    text = '{"key": "missing end brace"'
    result = summarizer._extract_first_json_object(text)
    assert result is None


# ============================================================================
# Truncation Detection Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_detects_truncation(summarizer):
    """Test truncation detection via stop_reason."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='"concise": "Test", "looking_for": "')]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 500
    mock_response.stop_reason = "max_tokens"  # Truncation

    summarizer.client.messages.create = AsyncMock(return_value=mock_response)

    with patch("backend.api.contribution_summarizer.get_cost_context", return_value={}):
        with patch("backend.api.contribution_summarizer.CostTracker.track_call"):
            result = await summarizer.summarize("Test content", "Expert A")

    # Should fall back due to incomplete JSON
    assert result is not None
    assert result.get("parse_error") is True
