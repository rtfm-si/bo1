"""Tests for PromptBroker.call_with_validation() retry logic."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.client import TokenUsage
from bo1.llm.response import LLMResponse
from bo1.llm.response_parser import ValidationConfig, XMLValidationError


def create_mock_response(
    content: str,
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> LLMResponse:
    """Create a mock LLMResponse for testing."""
    return LLMResponse(
        content=content,
        model="claude-sonnet-4-20250514",
        token_usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=0,
            cache_read_tokens=0,
        ),
        duration_ms=500,
        retry_count=0,
        timestamp=datetime.now(),
        request_id="test-request-123",
        phase="test",
        agent_type="TestAgent",
    )


class TestCallWithValidationSuccess:
    """Tests for successful validation scenarios."""

    @pytest.mark.asyncio
    async def test_valid_response_returns_immediately(self):
        """Verify valid response returns without retry."""
        broker = PromptBroker()
        request = PromptRequest(
            system="Test system",
            user_message="Test message",
            prefill="<thinking>",
            agent_type="TestAgent",
        )
        validation = ValidationConfig(required_tags=["action"])

        # Mock response with valid XML
        mock_response = create_mock_response("Analysis</thinking><action>continue</action>")

        with patch.object(broker, "call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await broker.call_with_validation(request, validation)

        assert mock_call.call_count == 1  # No retry needed
        assert result.content == mock_response.content

    @pytest.mark.asyncio
    async def test_valid_response_with_multiple_required_tags(self):
        """Verify validation passes when all required tags present."""
        broker = PromptBroker()
        request = PromptRequest(
            system="Test system",
            user_message="Test message",
            agent_type="TestAgent",
        )
        validation = ValidationConfig(required_tags=["recommendation", "reasoning", "confidence"])

        mock_response = create_mock_response(
            "<recommendation>Do X</recommendation>"
            "<reasoning>Because Y</reasoning>"
            "<confidence>high</confidence>"
        )

        with patch.object(broker, "call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await broker.call_with_validation(request, validation)

        assert mock_call.call_count == 1
        assert "recommendation" in result.content


class TestCallWithValidationRetry:
    """Tests for retry scenarios."""

    @pytest.mark.asyncio
    async def test_retry_on_missing_tag(self):
        """Verify retry occurs when required tag is missing."""
        broker = PromptBroker()
        request = PromptRequest(
            system="Test system",
            user_message="Test message",
            agent_type="TestAgent",
        )
        validation = ValidationConfig(required_tags=["action"], max_retries=1)

        # First response missing tag, second has it
        invalid_response = create_mock_response("No tags here", input_tokens=100, output_tokens=50)
        valid_response = create_mock_response(
            "<action>continue</action>", input_tokens=120, output_tokens=60
        )

        with patch.object(broker, "call", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [invalid_response, valid_response]
            result = await broker.call_with_validation(request, validation)

        assert mock_call.call_count == 2  # Initial + 1 retry
        assert "action" in result.content

    @pytest.mark.asyncio
    async def test_token_accumulation_across_retries(self):
        """Verify tokens are accumulated across retry attempts."""
        broker = PromptBroker()
        request = PromptRequest(
            system="Test system",
            user_message="Test message",
            agent_type="TestAgent",
        )
        validation = ValidationConfig(required_tags=["action"], max_retries=1)

        invalid_response = create_mock_response("Invalid", input_tokens=100, output_tokens=50)
        valid_response = create_mock_response(
            "<action>continue</action>", input_tokens=150, output_tokens=75
        )

        with patch.object(broker, "call", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [invalid_response, valid_response]
            result = await broker.call_with_validation(request, validation)

        # Tokens should be accumulated
        assert result.token_usage.input_tokens == 250  # 100 + 150
        assert result.token_usage.output_tokens == 125  # 50 + 75

    @pytest.mark.asyncio
    async def test_retry_with_prefill_reconstructed(self):
        """Verify prefill is prepended when validating content."""
        broker = PromptBroker()
        request = PromptRequest(
            system="Test system",
            user_message="Test message",
            prefill="<thinking>",
            agent_type="TestAgent",
        )
        validation = ValidationConfig(required_tags=["thinking"], max_retries=0)

        # Response content without prefill - but validation should prepend it
        mock_response = create_mock_response("Analysis</thinking>")

        with patch.object(broker, "call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            await broker.call_with_validation(request, validation)

        assert mock_call.call_count == 1  # Should pass validation with prefill


class TestCallWithValidationFailure:
    """Tests for failure scenarios."""

    @pytest.mark.asyncio
    async def test_non_strict_returns_response_after_retries_exhausted(self):
        """Verify non-strict mode returns response even if validation fails."""
        broker = PromptBroker()
        request = PromptRequest(
            system="Test system",
            user_message="Test message",
            agent_type="TestAgent",
        )
        validation = ValidationConfig(required_tags=["action"], max_retries=1, strict=False)

        invalid_response = create_mock_response("No tags here")

        with patch.object(broker, "call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = invalid_response  # Always returns invalid
            result = await broker.call_with_validation(request, validation)

        assert mock_call.call_count == 2  # Initial + 1 retry
        # Should still return the response
        assert result.content == "No tags here"

    @pytest.mark.asyncio
    async def test_strict_raises_after_retries_exhausted(self):
        """Verify strict mode raises exception when validation fails after retries."""
        broker = PromptBroker()
        request = PromptRequest(
            system="Test system",
            user_message="Test message",
            agent_type="TestAgent",
        )
        validation = ValidationConfig(required_tags=["action"], max_retries=1, strict=True)

        invalid_response = create_mock_response("No tags here")

        with patch.object(broker, "call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = invalid_response
            with pytest.raises(XMLValidationError) as exc_info:
                await broker.call_with_validation(request, validation)

        assert mock_call.call_count == 2
        assert "action" in exc_info.value.tag or "action" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_max_retries_zero_no_retry(self):
        """Verify max_retries=0 means no retries."""
        broker = PromptBroker()
        request = PromptRequest(
            system="Test system",
            user_message="Test message",
            agent_type="TestAgent",
        )
        validation = ValidationConfig(required_tags=["action"], max_retries=0, strict=False)

        invalid_response = create_mock_response("No tags")

        with patch.object(broker, "call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = invalid_response
            await broker.call_with_validation(request, validation)

        assert mock_call.call_count == 1  # Only initial call, no retry


class TestCallWithValidationMetrics:
    """Tests for metrics recording."""

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_validation_failure(self):
        """Verify metrics are recorded when validation fails."""
        broker = PromptBroker()
        request = PromptRequest(
            system="Test system",
            user_message="Test message",
            agent_type="TestAgent",
        )
        validation = ValidationConfig(required_tags=["action"], max_retries=1)

        invalid_response = create_mock_response("No tags")
        valid_response = create_mock_response("<action>vote</action>")

        with patch.object(broker, "call", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [invalid_response, valid_response]
            with patch("bo1.llm.broker.record_xml_validation_failure") as mock_failure_metric:
                with patch("bo1.llm.broker.record_xml_retry_success") as mock_success_metric:
                    await broker.call_with_validation(request, validation)

        # Should record failure on first attempt
        mock_failure_metric.assert_called()
        # Should record retry success
        mock_success_metric.assert_called_once_with("TestAgent")

    @pytest.mark.asyncio
    async def test_no_retry_success_metric_on_first_attempt_success(self):
        """Verify retry success metric not recorded if first attempt succeeds."""
        broker = PromptBroker()
        request = PromptRequest(
            system="Test system",
            user_message="Test message",
            agent_type="TestAgent",
        )
        validation = ValidationConfig(required_tags=["action"], max_retries=1)

        valid_response = create_mock_response("<action>vote</action>")

        with patch.object(broker, "call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = valid_response
            with patch("bo1.llm.broker.record_xml_retry_success") as mock_success_metric:
                await broker.call_with_validation(request, validation)

        # Should NOT record retry success since first attempt succeeded
        mock_success_metric.assert_not_called()


class TestCallWithValidationFeedback:
    """Tests for feedback message injection."""

    @pytest.mark.asyncio
    async def test_feedback_appended_to_user_message_on_retry(self):
        """Verify feedback message is appended on retry."""
        broker = PromptBroker()
        original_message = "Original user message"
        request = PromptRequest(
            system="Test system",
            user_message=original_message,
            agent_type="TestAgent",
        )
        validation = ValidationConfig(required_tags=["action"], max_retries=1)

        invalid_response = create_mock_response("No tags")
        valid_response = create_mock_response("<action>vote</action>")

        call_args_list = []

        async def capture_calls(req):
            call_args_list.append(req.user_message)
            if len(call_args_list) == 1:
                return invalid_response
            return valid_response

        with patch.object(broker, "call", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = capture_calls
            await broker.call_with_validation(request, validation)

        # First call should have original message
        assert call_args_list[0] == original_message

        # Second call should have feedback appended
        assert "XML formatting issues" in call_args_list[1]
        assert "properly closed and nested XML tags" in call_args_list[1]
