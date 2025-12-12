"""Tests for data analyst prompts."""

from bo1.prompts.data_analyst import (
    build_analyst_prompt,
    format_business_context,
    format_clarifications_context,
)


class TestFormatBusinessContext:
    """Test business context formatting."""

    def test_none_context(self):
        """Test None context returns empty string."""
        result = format_business_context(None)
        assert result == ""

    def test_empty_context(self):
        """Test empty dict returns empty string."""
        result = format_business_context({})
        assert result == ""

    def test_goals_only(self):
        """Test context with only goals."""
        context = {"goals": "Increase revenue by 20%"}
        result = format_business_context(context)

        assert "<business_context>" in result
        assert "</business_context>" in result
        assert "<goals>Increase revenue by 20%</goals>" in result

    def test_full_context(self):
        """Test context with all fields."""
        context = {
            "goals": "Market expansion",
            "industry": "SaaS",
            "competitors": "Acme Corp, Widget Inc",
            "constraints": "Limited budget",
            "metrics": "MRR, churn rate",
        }
        result = format_business_context(context)

        assert "<business_context>" in result
        assert "<goals>Market expansion</goals>" in result
        assert "<industry>SaaS</industry>" in result
        assert "<competitors>Acme Corp, Widget Inc</competitors>" in result
        assert "<constraints>Limited budget</constraints>" in result
        assert "<key_metrics>MRR, churn rate</key_metrics>" in result

    def test_partial_context(self):
        """Test context with some fields missing."""
        context = {"industry": "Retail", "goals": "Reduce costs"}
        result = format_business_context(context)

        assert "<industry>Retail</industry>" in result
        assert "<goals>Reduce costs</goals>" in result
        assert "<constraints>" not in result
        assert "<competitors>" not in result


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

    def test_prompt_with_business_context(self):
        """Test prompt includes business context."""
        prompt = build_analyst_prompt(
            question="Which product should I focus on?",
            dataset_context="<dataset>...</dataset>",
            business_context="<business_context><goals>Grow revenue</goals></business_context>",
        )

        assert "<business_context>" in prompt
        assert "<goals>Grow revenue</goals>" in prompt
        # Business context should appear after dataset but before question
        ds_pos = prompt.find("<dataset>")
        biz_pos = prompt.find("<business_context>")
        q_pos = prompt.find("<question>")
        assert ds_pos < biz_pos < q_pos

    def test_prompt_with_all_context(self):
        """Test prompt with all context types."""
        prompt = build_analyst_prompt(
            question="Analysis",
            dataset_context="<dataset>data</dataset>",
            conversation_history="<conversation_history>history</conversation_history>",
            clarifications_context="<prior_clarifications>prior</prior_clarifications>",
            business_context="<business_context>business</business_context>",
        )

        # Check order: dataset, business, clarifications, history, question
        ds_pos = prompt.find("<dataset>")
        biz_pos = prompt.find("<business_context>")
        clr_pos = prompt.find("<prior_clarifications>")
        hist_pos = prompt.find("<conversation_history>")
        q_pos = prompt.find("<question>")

        assert ds_pos < biz_pos < clr_pos < hist_pos < q_pos
