"""Tests for data analyst prompts."""

from bo1.prompts.data_analyst import (
    build_analyst_prompt,
    format_clarifications_context,
)


class TestFormatClarificationsContext:
    """Test clarification context formatting."""

    def test_empty_clarifications(self):
        """Test empty clarifications returns empty string."""
        result = format_clarifications_context([])
        assert result == ""

    def test_single_clarification(self):
        """Test single clarification formatting."""
        clarifications = [
            {
                "question": "What time period?",
                "answer": "Last quarter",
                "timestamp": "2025-01-01T00:00:00Z",
            }
        ]
        result = format_clarifications_context(clarifications)

        assert "<prior_clarifications>" in result
        assert "</prior_clarifications>" in result
        assert "<question>What time period?</question>" in result
        assert "<answer>Last quarter</answer>" in result

    def test_multiple_clarifications(self):
        """Test multiple clarifications formatting."""
        clarifications = [
            {"question": "Q1?", "answer": "A1", "timestamp": "t1"},
            {"question": "Q2?", "answer": "A2", "timestamp": "t2"},
        ]
        result = format_clarifications_context(clarifications)

        assert 'clarification id="1"' in result
        assert 'clarification id="2"' in result
        assert "<question>Q1?</question>" in result
        assert "<question>Q2?</question>" in result

    def test_max_clarifications_limit(self):
        """Test that only last 10 clarifications are included."""
        clarifications = [
            {"question": f"Q{i}?", "answer": f"A{i}", "timestamp": f"t{i}"} for i in range(15)
        ]
        result = format_clarifications_context(clarifications)

        # Should only include last 10 (Q5-Q14)
        assert "Q0?" not in result
        assert "Q5?" in result
        assert "Q14?" in result


class TestBuildAnalystPrompt:
    """Test prompt building with clarifications."""

    def test_prompt_without_clarifications(self):
        """Test prompt builds without clarifications."""
        prompt = build_analyst_prompt(
            question="What is the total?",
            dataset_context="<dataset>...</dataset>",
        )

        assert "<dataset>" in prompt
        assert "<question>What is the total?</question>" in prompt
        assert "<prior_clarifications>" not in prompt

    def test_prompt_with_clarifications(self):
        """Test prompt includes clarifications context."""
        clarifications_ctx = "<prior_clarifications>...</prior_clarifications>"
        prompt = build_analyst_prompt(
            question="What is the total?",
            dataset_context="<dataset>...</dataset>",
            clarifications_context=clarifications_ctx,
        )

        assert "<prior_clarifications>" in prompt
        # Clarifications should appear before question
        clr_pos = prompt.find("<prior_clarifications>")
        q_pos = prompt.find("<question>")
        assert clr_pos < q_pos

    def test_prompt_with_history_and_clarifications(self):
        """Test prompt with both history and clarifications."""
        prompt = build_analyst_prompt(
            question="Follow up",
            dataset_context="<dataset>data</dataset>",
            conversation_history="<conversation_history>history</conversation_history>",
            clarifications_context="<prior_clarifications>prior</prior_clarifications>",
        )

        # Check order: dataset, clarifications, history, question
        ds_pos = prompt.find("<dataset>")
        clr_pos = prompt.find("<prior_clarifications>")
        hist_pos = prompt.find("<conversation_history>")
        q_pos = prompt.find("<question>")

        assert ds_pos < clr_pos < hist_pos < q_pos
