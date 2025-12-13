"""Tests for mention parser service."""

from backend.services.mention_parser import (
    MentionType,
    format_mention,
    parse_mentions,
)


class TestParseMentions:
    """Tests for parse_mentions function."""

    def test_parse_single_meeting_mention(self):
        """Parse a single @meeting mention."""
        result = parse_mentions("Tell me about @meeting:12345678-1234-1234-1234-123456789abc")

        assert len(result.mentions) == 1
        assert result.mentions[0].type == MentionType.MEETING
        assert result.mentions[0].id == "12345678-1234-1234-1234-123456789abc"
        assert result.clean_text == "Tell me about"

    def test_parse_single_action_mention(self):
        """Parse a single @action mention."""
        result = parse_mentions(
            "What's the status of @action:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee?"
        )

        assert len(result.mentions) == 1
        assert result.mentions[0].type == MentionType.ACTION
        assert result.mentions[0].id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        assert "status of" in result.clean_text

    def test_parse_single_dataset_mention(self):
        """Parse a single @dataset mention."""
        result = parse_mentions("Analyze @dataset:11111111-2222-3333-4444-555555555555")

        assert len(result.mentions) == 1
        assert result.mentions[0].type == MentionType.DATASET
        assert result.mentions[0].id == "11111111-2222-3333-4444-555555555555"
        assert result.clean_text == "Analyze"

    def test_parse_multiple_mentions(self):
        """Parse multiple mentions of different types."""
        msg = (
            "Compare @meeting:11111111-1111-1111-1111-111111111111 "
            "with @action:22222222-2222-2222-2222-222222222222 "
            "and @dataset:33333333-3333-3333-3333-333333333333"
        )
        result = parse_mentions(msg)

        assert len(result.mentions) == 3
        assert result.mentions[0].type == MentionType.MEETING
        assert result.mentions[1].type == MentionType.ACTION
        assert result.mentions[2].type == MentionType.DATASET
        assert result.clean_text == "Compare with and"

    def test_parse_duplicate_mentions_deduped(self):
        """Duplicate mentions are deduplicated."""
        msg = (
            "@meeting:11111111-1111-1111-1111-111111111111 "
            "@meeting:11111111-1111-1111-1111-111111111111"
        )
        result = parse_mentions(msg)

        assert len(result.mentions) == 1

    def test_parse_no_mentions(self):
        """No mentions returns empty list."""
        result = parse_mentions("Just a regular message with no mentions")

        assert len(result.mentions) == 0
        assert result.clean_text == "Just a regular message with no mentions"

    def test_parse_invalid_uuid_ignored(self):
        """Invalid UUIDs are ignored."""
        result = parse_mentions("Invalid @meeting:not-a-uuid mention")

        assert len(result.mentions) == 0
        assert "Invalid" in result.clean_text

    def test_parse_invalid_type_ignored(self):
        """Invalid mention types are ignored."""
        result = parse_mentions("Invalid @user:11111111-1111-1111-1111-111111111111 mention")

        assert len(result.mentions) == 0

    def test_parse_case_insensitive_uuid(self):
        """UUID parsing is case-insensitive."""
        result = parse_mentions("@meeting:AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")

        assert len(result.mentions) == 1
        # UUID should be normalized to lowercase
        assert result.mentions[0].id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    def test_parse_clean_text_collapses_whitespace(self):
        """Clean text collapses multiple spaces."""
        result = parse_mentions("Before   @meeting:11111111-1111-1111-1111-111111111111   after")

        assert "  " not in result.clean_text
        assert result.clean_text == "Before after"

    def test_parse_mention_at_start(self):
        """Mention at start of message."""
        result = parse_mentions("@action:11111111-1111-1111-1111-111111111111 is blocked")

        assert len(result.mentions) == 1
        assert result.clean_text == "is blocked"

    def test_parse_mention_at_end(self):
        """Mention at end of message."""
        result = parse_mentions("Tell me about @meeting:11111111-1111-1111-1111-111111111111")

        assert len(result.mentions) == 1
        assert result.clean_text == "Tell me about"

    def test_mention_raw_text_preserved(self):
        """Raw mention text is preserved for reference."""
        result = parse_mentions("@meeting:11111111-1111-1111-1111-111111111111")

        assert result.mentions[0].raw_text == "@meeting:11111111-1111-1111-1111-111111111111"


class TestFormatMention:
    """Tests for format_mention function."""

    def test_format_meeting_mention(self):
        """Format a meeting mention."""
        result = format_mention(MentionType.MEETING, "12345678-1234-1234-1234-123456789abc")
        assert result == "@meeting:12345678-1234-1234-1234-123456789abc"

    def test_format_action_mention(self):
        """Format an action mention."""
        result = format_mention(MentionType.ACTION, "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        assert result == "@action:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    def test_format_dataset_mention(self):
        """Format a dataset mention."""
        result = format_mention(MentionType.DATASET, "11111111-2222-3333-4444-555555555555")
        assert result == "@dataset:11111111-2222-3333-4444-555555555555"
