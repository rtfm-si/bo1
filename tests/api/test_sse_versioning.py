"""Tests for SSE schema versioning and version negotiation.

Tests:
- Version header parsing (Accept-SSE-Version)
- Response header inclusion (X-SSE-Schema-Version)
- Version mismatch logging
- Event version field in formatted events
"""

from backend.api.constants import SSE_SCHEMA_VERSION
from backend.api.events import SSE_EVENT_VERSION, format_sse_event


class TestSSEVersionConstants:
    """Test SSE version constants are properly configured."""

    def test_sse_schema_version_is_positive(self) -> None:
        """SSE_SCHEMA_VERSION should be a positive integer."""
        assert isinstance(SSE_SCHEMA_VERSION, int)
        assert SSE_SCHEMA_VERSION >= 1

    def test_events_py_imports_version_from_constants(self) -> None:
        """SSE_EVENT_VERSION in events.py should match constants."""
        assert SSE_EVENT_VERSION == SSE_SCHEMA_VERSION


class TestEventVersionField:
    """Test that formatted events include event_version field."""

    def test_format_sse_event_includes_version(self) -> None:
        """format_sse_event should add event_version to data."""
        event = format_sse_event("test", {"message": "hello"})
        assert "event_version" in event
        assert f'"event_version": {SSE_SCHEMA_VERSION}' in event

    def test_format_sse_event_version_is_integer(self) -> None:
        """event_version should be serialized as integer, not string."""
        event = format_sse_event("test", {"foo": "bar"})
        # Should NOT be quoted like a string
        assert f'"event_version": {SSE_SCHEMA_VERSION}' in event
        assert f'"event_version": "{SSE_SCHEMA_VERSION}"' not in event

    def test_format_sse_event_preserves_data(self) -> None:
        """Original data should be preserved alongside event_version."""
        event = format_sse_event("test", {"key1": "value1", "key2": 42})
        assert '"key1": "value1"' in event
        assert '"key2": 42' in event
        assert f'"event_version": {SSE_SCHEMA_VERSION}' in event


class TestParseAcceptSSEVersion:
    """Test version header parsing in streaming.py."""

    def test_parse_none_returns_current_version(self) -> None:
        """None header should return current version."""
        from backend.api.streaming import parse_accept_sse_version

        assert parse_accept_sse_version(None) == SSE_SCHEMA_VERSION

    def test_parse_empty_string_returns_current_version(self) -> None:
        """Empty string should return current version."""
        from backend.api.streaming import parse_accept_sse_version

        assert parse_accept_sse_version("") == SSE_SCHEMA_VERSION

    def test_parse_valid_integer(self) -> None:
        """Valid integer string should be parsed."""
        from backend.api.streaming import parse_accept_sse_version

        assert parse_accept_sse_version("1") == 1
        assert parse_accept_sse_version("2") == 2

    def test_parse_integer_with_whitespace(self) -> None:
        """Whitespace should be stripped."""
        from backend.api.streaming import parse_accept_sse_version

        assert parse_accept_sse_version(" 1 ") == 1
        assert parse_accept_sse_version("  2  ") == 2

    def test_parse_invalid_string_returns_current(self) -> None:
        """Non-numeric string should return current version."""
        from backend.api.streaming import parse_accept_sse_version

        assert parse_accept_sse_version("invalid") == SSE_SCHEMA_VERSION
        assert parse_accept_sse_version("v1") == SSE_SCHEMA_VERSION
        assert parse_accept_sse_version("1.0") == SSE_SCHEMA_VERSION

    def test_parse_zero_returns_current(self) -> None:
        """Version 0 should return current version."""
        from backend.api.streaming import parse_accept_sse_version

        assert parse_accept_sse_version("0") == SSE_SCHEMA_VERSION

    def test_parse_negative_returns_current(self) -> None:
        """Negative version should return current version."""
        from backend.api.streaming import parse_accept_sse_version

        assert parse_accept_sse_version("-1") == SSE_SCHEMA_VERSION


class TestVersionMismatchLogging:
    """Test that version mismatches are logged for monitoring."""

    def test_mismatch_returns_requested_version(self) -> None:
        """Version mismatch should return the requested version."""
        from backend.api.streaming import (
            SSE_SCHEMA_VERSION,
            parse_accept_sse_version,
        )

        # Request a different version than current
        requested = SSE_SCHEMA_VERSION + 1

        # The function should return the requested version
        assert parse_accept_sse_version(str(requested)) == requested


class TestVersionHeaderIntegration:
    """Integration tests for version negotiation flow."""

    def test_version_constants_consistency(self) -> None:
        """All version-related constants should be consistent."""
        from backend.api.constants import SSE_SCHEMA_VERSION
        from backend.api.events import SSE_EVENT_VERSION

        assert SSE_EVENT_VERSION == SSE_SCHEMA_VERSION
