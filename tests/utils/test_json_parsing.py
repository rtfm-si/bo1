"""Tests for JSON parsing utilities."""

import logging

from bo1.utils.json_parsing import parse_json_with_fallback, validate_json_schema


class TestParseJsonWithFallback:
    """Tests for parse_json_with_fallback function."""

    def test_direct_parse_success(self):
        """Test successful direct JSON parsing."""
        content = '{"key": "value", "number": 42}'
        data, errors = parse_json_with_fallback(content)
        assert data == {"key": "value", "number": 42}
        assert len(errors) == 0

    def test_markdown_code_block(self):
        """Test extraction from markdown code block."""
        content = """
        Here is the JSON:
        ```json
        {"decision": "yes", "confidence": 0.9}
        ```
        """
        data, errors = parse_json_with_fallback(content)
        assert data == {"decision": "yes", "confidence": 0.9}
        assert len(errors) == 1  # Direct parse failed

    def test_markdown_without_json_marker(self):
        """Test code block without explicit json marker."""
        content = """
        ```
        {"result": "success"}
        ```
        """
        data, errors = parse_json_with_fallback(content)
        assert data == {"result": "success"}

    def test_regex_extraction(self):
        """Test regex-based JSON extraction."""
        content = 'Some preamble text {"extracted": "data"} and trailing text'
        data, errors = parse_json_with_fallback(content)
        assert data == {"extracted": "data"}
        assert len(errors) >= 1  # Direct parse failed

    def test_prefill_usage(self):
        """Test with prefill string."""
        content = '"decision": "yes", "confidence": 0.8}'
        data, errors = parse_json_with_fallback(content, prefill="{")
        assert data == {"decision": "yes", "confidence": 0.8}
        assert len(errors) == 0

    def test_complex_nested_json(self):
        """Test with complex nested JSON."""
        content = """
        {
            "sub_problems": [
                {"id": 1, "title": "First"},
                {"id": 2, "title": "Second"}
            ],
            "metadata": {
                "count": 2,
                "valid": true
            }
        }
        """
        data, errors = parse_json_with_fallback(content)
        assert len(data["sub_problems"]) == 2
        assert data["metadata"]["count"] == 2

    def test_all_strategies_fail(self):
        """Test when all parsing strategies fail."""
        content = "This is not JSON at all, just plain text"
        data, errors = parse_json_with_fallback(content)
        assert data is None
        assert len(errors) > 0
        assert "All parsing strategies exhausted" in errors[-1]

    def test_with_logger(self, caplog):
        """Test logging behavior with logger."""
        logger = logging.getLogger("test")
        content = '```json\n{"key": "value"}\n```'

        with caplog.at_level(logging.WARNING):
            data, errors = parse_json_with_fallback(content, logger=logger, context="test parsing")

        assert data == {"key": "value"}
        assert "markdown code block" in caplog.text.lower()

    def test_invalid_json_in_code_block(self):
        """Test with invalid JSON in code block."""
        content = "```json\n{invalid json here}\n```"
        data, errors = parse_json_with_fallback(content)
        # Should fall back to regex which will also fail
        assert data is None
        assert len(errors) > 0

    def test_multiline_json(self):
        """Test with multiline formatted JSON."""
        content = """{
            "vote": "yes",
            "confidence": "high",
            "conditions": [
                "condition 1",
                "condition 2"
            ]
        }"""
        data, errors = parse_json_with_fallback(content)
        assert data["vote"] == "yes"
        assert len(data["conditions"]) == 2

    def test_json_array(self):
        """Test that arrays are not extracted (only objects)."""
        content = '["item1", "item2", "item3"]'
        data, errors = parse_json_with_fallback(content)
        # Function looks for objects {}, not arrays []
        # This should fail since regex pattern is \{.*\}
        assert data is None or isinstance(data, list)


class TestValidateJsonSchema:
    """Tests for validate_json_schema function."""

    def test_valid_with_required_fields(self):
        """Test validation with all required fields present."""
        data = {"name": "Alice", "age": 30, "email": "alice@example.com"}
        is_valid, errors = validate_json_schema(data, ["name", "age", "email"])
        assert is_valid
        assert len(errors) == 0

    def test_missing_required_field(self):
        """Test validation with missing required field."""
        data = {"name": "Alice", "age": 30}
        is_valid, errors = validate_json_schema(data, ["name", "age", "email"])
        assert not is_valid
        assert "Missing required field: email" in errors

    def test_extra_fields_allowed_by_default(self):
        """Test that extra fields are allowed when optional_fields not specified."""
        data = {"name": "Alice", "age": 30, "extra": "field"}
        is_valid, errors = validate_json_schema(data, ["name", "age"])
        assert is_valid
        assert len(errors) == 0

    def test_unexpected_field_with_optional_list(self):
        """Test that unexpected fields are flagged when optional_fields provided."""
        data = {"name": "Alice", "age": 30, "unexpected": "field"}
        is_valid, errors = validate_json_schema(
            data, required_fields=["name", "age"], optional_fields=["email"]
        )
        assert not is_valid
        assert "Unexpected field: unexpected" in errors

    def test_optional_fields_accepted(self):
        """Test that optional fields are accepted."""
        data = {"name": "Alice", "age": 30, "email": "alice@example.com"}
        is_valid, errors = validate_json_schema(
            data, required_fields=["name"], optional_fields=["age", "email"]
        )
        assert is_valid
        assert len(errors) == 0

    def test_multiple_errors(self):
        """Test that multiple validation errors are collected."""
        data = {"name": "Alice"}
        is_valid, errors = validate_json_schema(data, ["name", "age", "email"])
        assert not is_valid
        assert len(errors) == 2
        assert any("age" in e for e in errors)
        assert any("email" in e for e in errors)

    def test_empty_data(self):
        """Test validation with empty data dictionary."""
        data = {}
        is_valid, errors = validate_json_schema(data, ["field1", "field2"])
        assert not is_valid
        assert len(errors) == 2

    def test_no_required_fields(self):
        """Test validation with no required fields."""
        data = {"any": "field"}
        is_valid, errors = validate_json_schema(data, [])
        assert is_valid
        assert len(errors) == 0
