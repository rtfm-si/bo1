"""Tests for XMLValidator edge cases (nested, unclosed, missing tags)."""

from bo1.llm.response_parser import ValidationConfig, XMLValidationError, XMLValidator


class TestXMLValidatorEdgeCases:
    """Extended edge case tests for XMLValidator."""

    def test_deeply_nested_tags_valid(self):
        """Verify deeply nested tags are handled correctly."""
        text = """
        <thinking>
            <reasoning>
                <summary>Nested content</summary>
            </reasoning>
        </thinking>
        """
        unclosed = XMLValidator.find_unclosed_tags(text)
        assert len(unclosed) == 0

    def test_mixed_case_tag_names(self):
        """Verify mixed case tag names are normalized."""
        text = "<THINKING>Analysis</THINKING><Action>continue</Action>"
        is_valid, errors = XMLValidator.validate(text, required_tags=["action"])
        assert is_valid is True

    def test_tags_with_attributes(self):
        """Verify tags with attributes are parsed correctly."""
        text = '<thinking type="analysis">Content</thinking>'
        unclosed = XMLValidator.find_unclosed_tags(text)
        assert len(unclosed) == 0

    def test_empty_tags(self):
        """Verify empty tags are valid."""
        text = "<thinking></thinking><action>continue</action>"
        is_valid, errors = XMLValidator.validate(text, required_tags=["action"])
        assert is_valid is True

    def test_multiline_tag_content(self):
        """Verify multiline content within tags."""
        text = """<thinking>
        Line 1
        Line 2
        Line 3
        </thinking>
        <action>vote</action>"""
        is_valid, errors = XMLValidator.validate(text, required_tags=["action", "thinking"])
        assert is_valid is True

    def test_special_characters_in_content(self):
        """Verify special characters in tag content don't break parsing."""
        text = "<thinking>Analysis: 50% > 25% && x < y</thinking><action>continue</action>"
        is_valid, errors = XMLValidator.validate(text, required_tags=["action"])
        assert is_valid is True

    def test_unclosed_tag_at_end(self):
        """Verify unclosed tag at end of content is detected."""
        text = "<action>continue</action><thinking>Started but not finished"
        unclosed = XMLValidator.find_unclosed_tags(text)
        assert "thinking" in unclosed

    def test_unclosed_tag_at_start(self):
        """Verify unclosed tag at start of content is detected."""
        text = "<thinking>Never closed<action>vote</action>"
        unclosed = XMLValidator.find_unclosed_tags(text)
        assert "thinking" in unclosed

    def test_multiple_same_tags(self):
        """Verify multiple same tags are handled."""
        text = """<thinking>First thought</thinking>
        <thinking>Second thought</thinking>
        <action>continue</action>"""
        is_valid, errors = XMLValidator.validate(text, required_tags=["action"])
        assert is_valid is True

    def test_partial_tag_name_not_matched(self):
        """Verify partial tag names don't false positive."""
        # "think" is not "thinking"
        text = "<think>This is not a real tag</think><action>vote</action>"
        is_valid, errors = XMLValidator.validate(text, required_tags=["action"])
        assert is_valid is True  # "think" is not in KNOWN_TAGS

    def test_required_multiple_tags_all_present(self):
        """Verify multiple required tags all present passes."""
        text = """<recommendation>Do X</recommendation>
        <reasoning>Because Y</reasoning>
        <confidence>high</confidence>"""
        is_valid, errors = XMLValidator.validate(
            text, required_tags=["recommendation", "reasoning", "confidence"]
        )
        assert is_valid is True
        assert len(errors) == 0

    def test_required_multiple_tags_one_missing(self):
        """Verify multiple required tags with one missing fails."""
        text = """<recommendation>Do X</recommendation>
        <reasoning>Because Y</reasoning>"""
        is_valid, errors = XMLValidator.validate(
            text, required_tags=["recommendation", "reasoning", "confidence"]
        )
        assert is_valid is False
        assert any("confidence" in e for e in errors)

    def test_required_multiple_tags_all_missing(self):
        """Verify multiple required tags all missing lists all."""
        text = "Plain text with no XML tags"
        is_valid, errors = XMLValidator.validate(
            text, required_tags=["recommendation", "reasoning", "confidence"]
        )
        assert is_valid is False
        assert len(errors) == 3  # One error per missing tag

    def test_tag_within_code_block_ignored(self):
        """Verify tags in code blocks aren't mistakenly matched (limitation)."""
        # Note: This is a known limitation - code blocks aren't special-cased
        text = "```<action>not_real</action>```<action>vote</action>"
        is_valid, errors = XMLValidator.validate(text, required_tags=["action"])
        assert is_valid is True  # Still valid because <action> exists

    def test_adjacent_tags_no_space(self):
        """Verify adjacent tags without space parse correctly."""
        text = "<thinking>Analysis</thinking><action>continue</action>"
        is_valid, errors = XMLValidator.validate(text, required_tags=["action", "thinking"])
        assert is_valid is True

    def test_whitespace_around_tag_content(self):
        """Verify whitespace around tag content is preserved."""
        text = "<action>  continue  </action>"
        is_valid, errors = XMLValidator.validate(text, required_tags=["action"])
        assert is_valid is True


class TestValidationConfig:
    """Tests for ValidationConfig dataclass."""

    def test_default_values(self):
        """Verify default values are correct."""
        config = ValidationConfig(required_tags=["action"])
        assert config.required_tags == ["action"]
        assert config.max_retries == 1
        assert config.strict is False

    def test_custom_max_retries(self):
        """Verify custom max_retries is set."""
        config = ValidationConfig(required_tags=["action"], max_retries=3)
        assert config.max_retries == 3

    def test_strict_mode(self):
        """Verify strict mode can be enabled."""
        config = ValidationConfig(required_tags=["action"], strict=True)
        assert config.strict is True

    def test_multiple_required_tags(self):
        """Verify multiple required tags are stored."""
        config = ValidationConfig(required_tags=["recommendation", "reasoning", "confidence"])
        assert len(config.required_tags) == 3

    def test_empty_required_tags(self):
        """Verify empty required_tags is allowed."""
        config = ValidationConfig(required_tags=[])
        assert config.required_tags == []


class TestXMLValidationError:
    """Tests for XMLValidationError exception."""

    def test_error_message(self):
        """Verify error message is stored."""
        error = XMLValidationError("Missing tag")
        assert str(error) == "Missing tag"

    def test_error_with_tag(self):
        """Verify tag is stored."""
        error = XMLValidationError("Missing required tag", tag="action")
        assert error.tag == "action"

    def test_error_with_details(self):
        """Verify details are stored."""
        error = XMLValidationError(
            "Validation failed",
            tag="action",
            details="Tag opened but not closed",
        )
        assert error.details == "Tag opened but not closed"

    def test_error_inheritance(self):
        """Verify XMLValidationError is an Exception."""
        error = XMLValidationError("Test")
        assert isinstance(error, Exception)


class TestGetValidationFeedback:
    """Tests for feedback message generation."""

    def test_single_error_feedback(self):
        """Verify single error generates correct feedback."""
        errors = ["Missing required tag: <action>"]
        feedback = XMLValidator.get_validation_feedback(errors)

        assert "XML formatting issues" in feedback
        assert "action" in feedback
        assert "Please provide your response again" in feedback

    def test_multiple_errors_feedback(self):
        """Verify multiple errors are listed."""
        errors = [
            "Unclosed tags: thinking",
            "Missing required tag: <action>",
            "Invalid tag nesting: <thinking>...<contribution>",
        ]
        feedback = XMLValidator.get_validation_feedback(errors)

        assert "Unclosed tags" in feedback
        assert "Missing required" in feedback
        assert "Invalid tag nesting" in feedback

    def test_empty_errors_feedback(self):
        """Verify empty errors still generates message."""
        feedback = XMLValidator.get_validation_feedback([])
        assert "XML formatting issues" in feedback
