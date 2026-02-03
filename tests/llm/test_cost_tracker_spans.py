"""Tests for OpenTelemetry span creation in CostTracker."""

from unittest.mock import MagicMock, patch

import pytest


class TestCostTrackerSpans:
    """Test OpenTelemetry span creation in track_call."""

    def test_track_call_creates_span_when_enabled(self) -> None:
        """track_call should create span with correct name and attributes."""
        mock_span = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_span)
        mock_context.__exit__ = MagicMock(return_value=False)

        with (
            patch("bo1.observability.tracing.is_tracing_enabled", return_value=True),
            patch(
                "bo1.observability.tracing.span_from_context", return_value=mock_context
            ) as mock_span_ctx,
        ):
            from bo1.llm.cost_tracker import CostTracker

            with CostTracker.track_call(
                provider="anthropic",
                operation_type="completion",
                model_name="claude-sonnet-4-5-20250929",
                session_id="test-session",
                node_name="test_node",
                phase="deliberation",
                prompt_type="persona_contribution",
            ) as record:
                record.input_tokens = 100
                record.output_tokens = 50

            # Verify span was created with correct name
            mock_span_ctx.assert_called_once()
            call_args = mock_span_ctx.call_args
            assert call_args[0][0] == "llm.anthropic.completion"

            # Verify initial attributes
            attrs = call_args[0][1]
            assert attrs["llm.provider"] == "anthropic"
            assert attrs["llm.operation"] == "completion"
            assert attrs["llm.model"] == "claude-sonnet-4-5-20250929"
            assert attrs["llm.session_id"] == "test-session"
            assert attrs["llm.node_name"] == "test_node"
            assert attrs["llm.phase"] == "deliberation"
            assert attrs["llm.prompt_type"] == "persona_contribution"

    def test_track_call_sets_token_attributes_on_span(self) -> None:
        """track_call should set token counts on span after completion."""
        mock_span = MagicMock()

        with (
            patch("bo1.observability.tracing.is_tracing_enabled", return_value=True),
            patch("bo1.observability.tracing.span_from_context") as mock_span_ctx,
        ):
            # Configure the context manager to yield our mock span
            mock_span_ctx.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_span_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from bo1.llm.cost_tracker import CostTracker

            with CostTracker.track_call(
                provider="anthropic",
                operation_type="completion",
                model_name="claude-sonnet-4-5-20250929",
            ) as record:
                record.input_tokens = 150
                record.output_tokens = 75
                record.cache_read_tokens = 50

            # Verify token attributes were set
            set_attr_calls = mock_span.set_attribute.call_args_list
            attr_dict = {call[0][0]: call[0][1] for call in set_attr_calls}

            assert attr_dict.get("llm.input_tokens") == 150
            assert attr_dict.get("llm.output_tokens") == 75
            assert attr_dict.get("llm.cache_read_tokens") == 50
            assert attr_dict.get("llm.status") == "success"
            assert "llm.latency_ms" in attr_dict
            assert "llm.total_cost" in attr_dict

    def test_track_call_no_span_when_disabled(self) -> None:
        """track_call should not create span when tracing disabled."""
        with (
            patch("bo1.observability.tracing.is_tracing_enabled", return_value=False),
            patch("bo1.observability.tracing.span_from_context") as mock_span_ctx,
        ):
            # span_from_context yields None when disabled
            mock_span_ctx.return_value.__enter__ = MagicMock(return_value=None)
            mock_span_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from bo1.llm.cost_tracker import CostTracker

            with CostTracker.track_call(
                provider="anthropic",
                operation_type="completion",
            ) as record:
                record.input_tokens = 100

            # span_from_context should still be called (it handles the noop)
            mock_span_ctx.assert_called_once()

    def test_track_call_records_exception_on_span(self) -> None:
        """track_call should record exception on span when error occurs."""
        mock_span = MagicMock()

        with (
            patch("bo1.observability.tracing.is_tracing_enabled", return_value=True),
            patch("bo1.observability.tracing.span_from_context") as mock_span_ctx,
        ):
            mock_span_ctx.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_span_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from bo1.llm.cost_tracker import CostTracker

            with pytest.raises(ValueError, match="test error"):
                with CostTracker.track_call(
                    provider="anthropic",
                    operation_type="completion",
                ):
                    raise ValueError("test error")

            # Verify exception was recorded on span
            mock_span.record_exception.assert_called_once()
            exc_arg = mock_span.record_exception.call_args[0][0]
            assert isinstance(exc_arg, ValueError)
            assert str(exc_arg) == "test error"

    def test_track_call_span_name_format(self) -> None:
        """Span name should follow llm.{provider}.{operation} format."""
        with (
            patch("bo1.observability.tracing.is_tracing_enabled", return_value=True),
            patch("bo1.observability.tracing.span_from_context") as mock_span_ctx,
        ):
            mock_span_ctx.return_value.__enter__ = MagicMock(return_value=None)
            mock_span_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from bo1.llm.cost_tracker import CostTracker

            # Test different providers
            test_cases = [
                ("anthropic", "completion", "llm.anthropic.completion"),
                ("voyage", "embedding", "llm.voyage.embedding"),
                ("brave", "search", "llm.brave.search"),
                ("tavily", "search", "llm.tavily.search"),
            ]

            for provider, operation, expected_name in test_cases:
                mock_span_ctx.reset_mock()

                with CostTracker.track_call(
                    provider=provider,
                    operation_type=operation,
                ):
                    pass

                call_args = mock_span_ctx.call_args
                assert call_args[0][0] == expected_name, f"Failed for {provider}/{operation}"

    def test_track_call_optional_attributes(self) -> None:
        """Optional attributes should only be set when provided."""
        with (
            patch("bo1.observability.tracing.is_tracing_enabled", return_value=True),
            patch("bo1.observability.tracing.span_from_context") as mock_span_ctx,
        ):
            mock_span_ctx.return_value.__enter__ = MagicMock(return_value=None)
            mock_span_ctx.return_value.__exit__ = MagicMock(return_value=False)

            from bo1.llm.cost_tracker import CostTracker

            # Call with minimal arguments
            with CostTracker.track_call(
                provider="anthropic",
                operation_type="completion",
            ):
                pass

            call_args = mock_span_ctx.call_args
            attrs = call_args[0][1]

            # Required attributes should be present
            assert "llm.provider" in attrs
            assert "llm.operation" in attrs

            # Optional attributes should not be present
            assert "llm.model" not in attrs
            assert "llm.session_id" not in attrs
            assert "llm.node_name" not in attrs
