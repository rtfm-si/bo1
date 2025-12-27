"""Tests for SEO Autopilot purchase intent scoring.

Unit tests for the purchase intent scoring logic.
API integration tests require full test fixtures from conftest.
"""


class TestPurchaseIntentScoring:
    """Tests for purchase intent scoring logic."""

    def test_transactional_keywords_score_higher(self):
        """Test that transactional keywords get higher intent scores."""
        from backend.services.seo_autopilot import calculate_purchase_intent_score
        from backend.services.topic_discovery import Topic

        # High-intent topic
        high_intent = Topic(
            title="Best AI Tools to Buy in 2025",
            description="Compare and purchase top AI tools",
            keywords=["buy AI tools", "AI pricing", "AI comparison"],
            relevance_score=0.8,
            source="context",
        )

        # Low-intent topic
        low_intent = Topic(
            title="The History of AI Development",
            description="Learn about how AI evolved over time",
            keywords=["AI history", "machine learning origins"],
            relevance_score=0.8,
            source="context",
        )

        high_scored = calculate_purchase_intent_score(high_intent)
        low_scored = calculate_purchase_intent_score(low_intent)

        assert high_scored.intent_score > low_scored.intent_score
        assert len(high_scored.intent_signals) > 0

    def test_comparison_keywords_increase_score(self):
        """Test that comparison keywords increase intent score."""
        from backend.services.seo_autopilot import calculate_purchase_intent_score
        from backend.services.topic_discovery import Topic

        comparison_topic = Topic(
            title="Notion vs Obsidian: Which is Better?",
            description="Compare the best note-taking apps",
            keywords=["notion vs obsidian", "comparison", "alternative"],
            relevance_score=0.8,
            source="context",
        )

        scored = calculate_purchase_intent_score(comparison_topic)

        assert scored.intent_score > 0
        assert any("comparison" in s for s in scored.intent_signals)
