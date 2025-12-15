"""Tests for bo1/utils/metrics.py - label truncation utilities."""

from bo1.constants import MetricLabelConfig
from bo1.utils.metrics import truncate_label


class TestTruncateLabel:
    """Test truncate_label function for Prometheus cardinality control."""

    def test_truncate_label_short_input(self) -> None:
        """Short input returns unchanged."""
        assert truncate_label("short") == "short"
        assert truncate_label("abc") == "abc"

    def test_truncate_label_exact_length(self) -> None:
        """Input at exact length returns unchanged."""
        exact = "a" * MetricLabelConfig.LABEL_TRUNCATE_LENGTH
        assert truncate_label(exact) == exact

    def test_truncate_label_long_input(self) -> None:
        """Long input gets truncated to default length."""
        long_input = "abcdefghijklmnop"
        expected = long_input[: MetricLabelConfig.LABEL_TRUNCATE_LENGTH]
        assert truncate_label(long_input) == expected
        assert len(truncate_label(long_input)) == MetricLabelConfig.LABEL_TRUNCATE_LENGTH

    def test_truncate_label_empty_string(self) -> None:
        """Empty string returns 'unknown'."""
        assert truncate_label("") == "unknown"

    def test_truncate_label_none(self) -> None:
        """None returns 'unknown'."""
        assert truncate_label(None) == "unknown"

    def test_truncate_label_uuid(self) -> None:
        """UUID format truncates correctly to first 8 chars."""
        uuid = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"
        result = truncate_label(uuid)
        assert result == "3f2504e0"
        assert len(result) == 8

    def test_truncate_label_custom_length(self) -> None:
        """Custom length parameter works."""
        assert truncate_label("abcdefghij", length=4) == "abcd"
        assert truncate_label("ab", length=4) == "ab"

    def test_truncate_label_zero_length(self) -> None:
        """Zero length returns empty string."""
        assert truncate_label("test", length=0) == ""

    def test_consistency(self) -> None:
        """Same input always produces same output."""
        session_id = "bo1_12345678-1234-1234-1234-123456789012"
        result1 = truncate_label(session_id)
        result2 = truncate_label(session_id)
        assert result1 == result2 == "bo1_1234"
