"""Tests for XML parsing utilities."""

from bo1.utils.xml_parsing import extract_multiple_tags, extract_xml_tag


class TestExtractXmlTag:
    """Tests for extract_xml_tag function."""

    def test_simple_extraction(self):
        """Test basic XML tag extraction."""
        text = "<thinking>Deep analysis here</thinking>"
        result = extract_xml_tag(text, "thinking")
        assert result == "Deep analysis here"

    def test_case_insensitive_default(self):
        """Test case-insensitive matching (default)."""
        text = "<VOTE>Yes</VOTE>"
        result = extract_xml_tag(text, "vote")
        assert result == "Yes"

    def test_case_sensitive_mode(self):
        """Test case-sensitive matching when specified."""
        text = "<VOTE>Yes</VOTE>"
        result = extract_xml_tag(text, "vote", case_insensitive=False)
        assert result is None

        result = extract_xml_tag(text, "VOTE", case_insensitive=False)
        assert result == "Yes"

    def test_multiline_content(self):
        """Test extraction of multiline content."""
        text = """
        <contribution>
        This is a multi-line
        contribution with
        several lines.
        </contribution>
        """
        result = extract_xml_tag(text, "contribution")
        assert "multi-line" in result
        assert "several lines" in result

    def test_nested_tags(self):
        """Test extraction with nested tags."""
        text = "<outer><inner>nested content</inner></outer>"
        result = extract_xml_tag(text, "inner")
        assert result == "nested content"

        result = extract_xml_tag(text, "outer")
        assert "<inner>" in result

    def test_missing_tag(self):
        """Test behavior when tag is not found."""
        text = "No tags here at all"
        result = extract_xml_tag(text, "missing")
        assert result is None

    def test_whitespace_stripping(self):
        """Test that whitespace is stripped from extracted content."""
        text = "<vote>   Yes   </vote>"
        result = extract_xml_tag(text, "vote")
        assert result == "Yes"

    def test_special_characters_in_content(self):
        """Test extraction with special characters."""
        text = "<decision>Yes, but with conditions: 1) A & B, 2) C > D</decision>"
        result = extract_xml_tag(text, "decision")
        assert "A & B" in result
        assert "C > D" in result

    def test_empty_tag(self):
        """Test extraction of empty tag."""
        text = "<empty></empty>"
        result = extract_xml_tag(text, "empty")
        assert result == ""

    def test_first_match_only(self):
        """Test that only the first matching tag is extracted."""
        text = "<vote>First</vote> some text <vote>Second</vote>"
        result = extract_xml_tag(text, "vote")
        assert result == "First"


class TestExtractMultipleTags:
    """Tests for extract_multiple_tags function."""

    def test_extract_multiple_tags(self):
        """Test extracting multiple different tags."""
        text = "<thinking>Analysis</thinking><contribution>My view</contribution>"
        result = extract_multiple_tags(text, ["thinking", "contribution"])
        assert result == {"thinking": "Analysis", "contribution": "My view"}

    def test_some_tags_missing(self):
        """Test extraction when some tags are missing."""
        text = "<vote>Yes</vote>"
        result = extract_multiple_tags(text, ["vote", "confidence", "conditions"])
        assert result == {"vote": "Yes", "confidence": None, "conditions": None}

    def test_empty_tag_list(self):
        """Test with empty tag list."""
        text = "<vote>Yes</vote>"
        result = extract_multiple_tags(text, [])
        assert result == {}

    def test_case_insensitive_multiple(self):
        """Test case-insensitive matching for multiple tags."""
        text = "<THINKING>Analysis</THINKING><CONTRIBUTION>View</CONTRIBUTION>"
        result = extract_multiple_tags(text, ["thinking", "contribution"])
        assert result["thinking"] == "Analysis"
        assert result["contribution"] == "View"
