"""Unit tests for context extractor service.

Tests both LLM-based and fallback rule-based extraction.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.context_extractor import (
    AUTO_APPLY_CONFIDENCE_THRESHOLD,
    UPDATABLE_CONTEXT_FIELDS,
    ContextExtractor,
    ContextUpdate,
    ContextUpdateSource,
    extract_context_updates,
    filter_high_confidence_updates,
    format_competitors_for_display,
    get_context_extractor,
    merge_competitors,
)


class TestContextUpdateSource:
    """Test ContextUpdateSource enum."""

    def test_all_sources_defined(self):
        """Verify all expected sources exist."""
        expected = ["clarification", "problem_statement", "action"]
        actual = [s.value for s in ContextUpdateSource]
        assert set(expected) == set(actual)


class TestContextUpdate:
    """Test ContextUpdate dataclass."""

    def test_to_dict_minimal(self):
        """Test to_dict with minimal fields."""
        update = ContextUpdate(
            field_name="revenue",
            new_value="$50,000 MRR",
            confidence=0.9,
            source_type=ContextUpdateSource.CLARIFICATION,
            source_text="our MRR is $50,000",
        )
        result = update.to_dict()
        assert result["field_name"] == "revenue"
        assert result["new_value"] == "$50,000 MRR"
        assert result["confidence"] == 0.9
        assert result["source_type"] == "clarification"

    def test_from_dict_roundtrip(self):
        """Test from_dict reconstructs update correctly."""
        original = ContextUpdate(
            field_name="customers",
            new_value="200",
            confidence=0.85,
            source_type=ContextUpdateSource.PROBLEM_STATEMENT,
            source_text="We have 200 customers",
            extracted_at="2025-01-15T12:00:00+00:00",
        )
        data = original.to_dict()
        restored = ContextUpdate.from_dict(data)

        assert restored.field_name == original.field_name
        assert restored.new_value == original.new_value
        assert restored.confidence == original.confidence
        assert restored.source_type == original.source_type


class TestFallbackExtraction:
    """Test rule-based fallback extraction."""

    @pytest.fixture
    def extractor(self):
        return ContextExtractor()

    def test_revenue_extraction(self, extractor):
        """Test revenue extraction with dollar sign."""
        updates = extractor._fallback_extract(
            "$50,000 MRR",
            ContextUpdateSource.CLARIFICATION,
        )
        assert len(updates) >= 1
        revenue_updates = [u for u in updates if u.field_name == "revenue"]
        assert len(revenue_updates) == 1
        assert "$50,000" in str(revenue_updates[0].new_value)

    def test_revenue_k_suffix(self, extractor):
        """Test revenue with K suffix."""
        updates = extractor._fallback_extract(
            "We're at $50K monthly",
            ContextUpdateSource.CLARIFICATION,
        )
        revenue_updates = [u for u in updates if u.field_name == "revenue"]
        assert len(revenue_updates) == 1

    def test_customer_extraction(self, extractor):
        """Test customer count extraction."""
        updates = extractor._fallback_extract(
            "We have 200 active customers",
            ContextUpdateSource.CLARIFICATION,
        )
        customer_updates = [u for u in updates if u.field_name == "customers"]
        assert len(customer_updates) == 1
        assert "200" in str(customer_updates[0].new_value)

    def test_team_size_extraction(self, extractor):
        """Test team size extraction."""
        updates = extractor._fallback_extract(
            "We have 8 people on the team",
            ContextUpdateSource.ACTION_UPDATE,
        )
        team_updates = [u for u in updates if u.field_name == "team_size"]
        assert len(team_updates) == 1

    def test_growth_rate_extraction(self, extractor):
        """Test growth rate extraction."""
        updates = extractor._fallback_extract(
            "Growing at 15% MoM",
            ContextUpdateSource.PROBLEM_STATEMENT,
        )
        growth_updates = [u for u in updates if u.field_name == "growth_rate"]
        assert len(growth_updates) == 1
        assert "15%" in str(growth_updates[0].new_value)

    def test_empty_input(self, extractor):
        """Test empty input returns empty list."""
        updates = extractor._fallback_extract("", ContextUpdateSource.CLARIFICATION)
        assert updates == []

    def test_no_matches(self, extractor):
        """Test text with no extractable updates."""
        updates = extractor._fallback_extract(
            "The weather is nice today",
            ContextUpdateSource.CLARIFICATION,
        )
        assert updates == []


class TestLLMExtraction:
    """Test LLM-based extraction with mocked Claude client."""

    @pytest.fixture
    def extractor(self):
        return ContextExtractor()

    @pytest.mark.asyncio
    async def test_llm_extract_success(self, extractor):
        """Test successful LLM extraction."""
        mock_response = """[{
            "field_name": "revenue",
            "new_value": "$50,000 MRR",
            "confidence": 0.95,
            "source_text": "our MRR is $50,000"
        }]"""

        with patch.object(extractor, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call = AsyncMock(return_value=(mock_response, {}))
            mock_get_client.return_value = mock_client

            updates = await extractor._extract_with_llm(
                "Our MRR is $50,000",
                None,
                ContextUpdateSource.CLARIFICATION,
            )

            assert len(updates) == 1
            assert updates[0].field_name == "revenue"
            assert updates[0].confidence == 0.95

    @pytest.mark.asyncio
    async def test_llm_extract_empty_response(self, extractor):
        """Test LLM returning empty array."""
        mock_response = "[]"

        with patch.object(extractor, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call = AsyncMock(return_value=(mock_response, {}))
            mock_get_client.return_value = mock_client

            updates = await extractor._extract_with_llm(
                "The weather is nice",
                None,
                ContextUpdateSource.CLARIFICATION,
            )

            assert updates == []

    @pytest.mark.asyncio
    async def test_llm_extract_filters_invalid_fields(self, extractor):
        """Test that LLM results are filtered to valid fields only."""
        mock_response = """[
            {"field_name": "revenue", "new_value": "$50K", "confidence": 0.9, "source_text": "revenue"},
            {"field_name": "invalid_field", "new_value": "test", "confidence": 0.9, "source_text": "test"}
        ]"""

        with patch.object(extractor, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call = AsyncMock(return_value=(mock_response, {}))
            mock_get_client.return_value = mock_client

            updates = await extractor._extract_with_llm(
                "Revenue is $50K",
                None,
                ContextUpdateSource.CLARIFICATION,
            )

            assert len(updates) == 1
            assert updates[0].field_name == "revenue"


class TestExtractContextUpdatesFunction:
    """Test the extract_context_updates convenience function."""

    @pytest.mark.asyncio
    async def test_extract_empty_input(self):
        """Test extracting from empty input."""
        updates = await extract_context_updates("")
        assert updates == []

    @pytest.mark.asyncio
    async def test_extract_fallback_on_llm_failure(self):
        """Test fallback to rule-based extraction when LLM fails."""
        with patch(
            "backend.services.context_extractor.ContextExtractor._extract_with_llm",
            side_effect=Exception("LLM failed"),
        ):
            updates = await extract_context_updates("Our revenue is $50,000 MRR")
            # Should fallback to rule-based extraction
            revenue_updates = [u for u in updates if u.field_name == "revenue"]
            assert len(revenue_updates) >= 1


class TestFilterHighConfidenceUpdates:
    """Test the confidence filtering function."""

    def test_filter_splits_by_threshold(self):
        """Test updates are split by confidence threshold."""
        updates = [
            ContextUpdate(
                field_name="revenue",
                new_value="$50K",
                confidence=0.95,
                source_type=ContextUpdateSource.CLARIFICATION,
                source_text="revenue",
            ),
            ContextUpdate(
                field_name="customers",
                new_value="100",
                confidence=0.7,
                source_type=ContextUpdateSource.CLARIFICATION,
                source_text="customers",
            ),
            ContextUpdate(
                field_name="growth_rate",
                new_value="15%",
                confidence=0.85,
                source_type=ContextUpdateSource.CLARIFICATION,
                source_text="growth",
            ),
        ]

        high, low = filter_high_confidence_updates(updates)

        # Default threshold is 0.8
        assert len(high) == 2  # revenue (0.95) and growth (0.85)
        assert len(low) == 1  # customers (0.7)
        assert all(u.confidence >= AUTO_APPLY_CONFIDENCE_THRESHOLD for u in high)
        assert all(u.confidence < AUTO_APPLY_CONFIDENCE_THRESHOLD for u in low)

    def test_filter_custom_threshold(self):
        """Test filtering with custom threshold."""
        updates = [
            ContextUpdate(
                field_name="revenue",
                new_value="$50K",
                confidence=0.95,
                source_type=ContextUpdateSource.CLARIFICATION,
                source_text="revenue",
            ),
            ContextUpdate(
                field_name="customers",
                new_value="100",
                confidence=0.7,
                source_type=ContextUpdateSource.CLARIFICATION,
                source_text="customers",
            ),
        ]

        high, low = filter_high_confidence_updates(updates, threshold=0.9)

        assert len(high) == 1  # Only revenue (0.95)
        assert len(low) == 1  # customers (0.7)

    def test_filter_empty_list(self):
        """Test filtering empty list."""
        high, low = filter_high_confidence_updates([])
        assert high == []
        assert low == []


class TestGetContextExtractor:
    """Test singleton pattern."""

    def test_singleton(self):
        """Test that get_context_extractor returns singleton."""
        # Reset singleton for test
        import backend.services.context_extractor as module

        module._extractor = None

        extractor1 = get_context_extractor()
        extractor2 = get_context_extractor()
        assert extractor1 is extractor2


class TestUpdatableContextFields:
    """Test the list of updatable context fields."""

    def test_required_fields_present(self):
        """Test that required fields are in the list."""
        required = [
            "revenue",
            "customers",
            "growth_rate",
            "team_size",
            "business_stage",
            "industry",
            "competitors",
        ]
        for field in required:
            assert field in UPDATABLE_CONTEXT_FIELDS, (
                f"{field} missing from UPDATABLE_CONTEXT_FIELDS"
            )


class TestCompetitorFallbackExtraction:
    """Test competitor-specific fallback extraction."""

    @pytest.fixture
    def extractor(self):
        return ContextExtractor()

    def test_extract_compete_against_pattern(self, extractor):
        """Test 'compete against X and Y' pattern."""
        updates = extractor._fallback_extract(
            "We compete against Asana and Monday.com in the project management space.",
            ContextUpdateSource.CLARIFICATION,
        )
        competitor_updates = [u for u in updates if u.field_name == "competitors"]
        assert len(competitor_updates) == 1
        competitors = competitor_updates[0].new_value
        assert isinstance(competitors, list)
        names = [c["name"] for c in competitors]
        assert "Asana" in names
        assert "Monday" in names or "Monday.com" in names

    def test_extract_main_competitor_pattern(self, extractor):
        """Test 'main competitor is X' pattern."""
        updates = extractor._fallback_extract(
            "Our main competitor is Figma.",
            ContextUpdateSource.CLARIFICATION,
        )
        competitor_updates = [u for u in updates if u.field_name == "competitors"]
        assert len(competitor_updates) == 1
        competitors = competitor_updates[0].new_value
        names = [c["name"] for c in competitors]
        assert "Figma" in names

    def test_extract_competitors_like_pattern(self, extractor):
        """Test 'competitors like X, Y, Z' pattern."""
        updates = extractor._fallback_extract(
            "Our competitors include Figma, Sketch, and Adobe XD.",
            ContextUpdateSource.PROBLEM_STATEMENT,
        )
        competitor_updates = [u for u in updates if u.field_name == "competitors"]
        assert len(competitor_updates) == 1
        competitors = competitor_updates[0].new_value
        names = [c["name"] for c in competitors]
        assert len(names) >= 2  # At least Figma and Sketch

    def test_reject_generic_categories(self, extractor):
        """Test that generic categories are not extracted."""
        updates = extractor._fallback_extract(
            "We're in the project management tools space with many SaaS competitors.",
            ContextUpdateSource.CLARIFICATION,
        )
        competitor_updates = [u for u in updates if u.field_name == "competitors"]
        # Should not extract generic terms
        if competitor_updates:
            competitors = competitor_updates[0].new_value
            names = [c["name"].lower() for c in competitors]
            assert "project" not in names
            assert "management" not in names
            assert "tools" not in names
            assert "saas" not in names

    def test_competitor_confidence_scoring(self, extractor):
        """Test that competitor extractions have appropriate confidence."""
        updates = extractor._fallback_extract(
            "We compete against Asana.",
            ContextUpdateSource.CLARIFICATION,
        )
        competitor_updates = [u for u in updates if u.field_name == "competitors"]
        assert len(competitor_updates) == 1
        # Fallback should have moderate confidence (0.6-0.8)
        assert 0.5 <= competitor_updates[0].confidence <= 0.8

    def test_competitor_category_direct(self, extractor):
        """Test that extracted competitors have category field."""
        updates = extractor._fallback_extract(
            "We compete against Asana.",
            ContextUpdateSource.CLARIFICATION,
        )
        competitor_updates = [u for u in updates if u.field_name == "competitors"]
        assert len(competitor_updates) == 1
        competitors = competitor_updates[0].new_value
        assert all(c.get("category") == "direct" for c in competitors)


class TestCompetitorLLMExtraction:
    """Test LLM-based competitor extraction with mocked responses."""

    @pytest.fixture
    def extractor(self):
        return ContextExtractor()

    @pytest.mark.asyncio
    async def test_llm_extract_specific_competitors(self, extractor):
        """Test LLM extracts specific company names."""
        mock_response = """[{
            "field_name": "competitors",
            "new_value": [
                {"name": "Asana", "category": "direct", "confidence": 0.95},
                {"name": "Monday.com", "category": "direct", "confidence": 0.95}
            ],
            "confidence": 0.95,
            "source_text": "We compete against Asana and Monday.com"
        }]"""

        with patch.object(extractor, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call = AsyncMock(return_value=(mock_response, {}))
            mock_get_client.return_value = mock_client

            updates = await extractor._extract_with_llm(
                "We compete against Asana and Monday.com",
                None,
                ContextUpdateSource.CLARIFICATION,
            )

            assert len(updates) == 1
            assert updates[0].field_name == "competitors"
            competitors = updates[0].new_value
            assert isinstance(competitors, list)
            assert len(competitors) == 2

    @pytest.mark.asyncio
    async def test_llm_extract_with_categories(self, extractor):
        """Test LLM extracts direct and indirect categories."""
        mock_response = """[{
            "field_name": "competitors",
            "new_value": [
                {"name": "Figma", "category": "direct", "confidence": 0.9},
                {"name": "Canva", "category": "indirect", "confidence": 0.8}
            ],
            "confidence": 0.85,
            "source_text": "Figma is our main competitor, Canva is indirect"
        }]"""

        with patch.object(extractor, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call = AsyncMock(return_value=(mock_response, {}))
            mock_get_client.return_value = mock_client

            updates = await extractor._extract_with_llm(
                "Figma is our main competitor, we also watch Canva",
                None,
                ContextUpdateSource.CLARIFICATION,
            )

            assert len(updates) == 1
            competitors = updates[0].new_value
            direct = [c for c in competitors if c.get("category") == "direct"]
            indirect = [c for c in competitors if c.get("category") == "indirect"]
            assert len(direct) == 1
            assert len(indirect) == 1


class TestMergeCompetitors:
    """Test competitor merging and deduplication."""

    def test_merge_empty_existing(self):
        """Test merging with no existing competitors."""
        new = [{"name": "Asana", "category": "direct", "confidence": 0.9}]
        result = merge_competitors(None, new)
        assert len(result) == 1
        assert result[0]["name"] == "Asana"

    def test_merge_string_existing(self):
        """Test merging with comma-separated string existing."""
        existing = "Figma, Sketch"
        new = [{"name": "Adobe XD", "category": "direct", "confidence": 0.8}]
        result = merge_competitors(existing, new)
        assert len(result) == 3
        names = [c["name"] for c in result]
        assert "Figma" in names
        assert "Sketch" in names
        assert "Adobe XD" in names

    def test_merge_list_existing(self):
        """Test merging with list of dicts existing."""
        existing = [
            {"name": "Asana", "category": "direct", "confidence": 1.0},
            {"name": "Monday.com", "category": "direct", "confidence": 1.0},
        ]
        new = [{"name": "Clickup", "category": "direct", "confidence": 0.8}]
        result = merge_competitors(existing, new)
        assert len(result) == 3

    def test_merge_deduplicates_by_name(self):
        """Test that merging deduplicates by name (case-insensitive)."""
        existing = [{"name": "Asana", "category": "direct", "confidence": 1.0}]
        new = [
            {"name": "asana", "category": "indirect", "confidence": 0.8},  # Duplicate
            {"name": "Monday.com", "category": "direct", "confidence": 0.9},
        ]
        result = merge_competitors(existing, new)
        assert len(result) == 2
        names = [c["name"].lower() for c in result]
        assert names.count("asana") == 1

    def test_merge_preserves_existing_data(self):
        """Test that existing competitor data is preserved over new."""
        existing = [{"name": "Asana", "category": "direct", "confidence": 1.0}]
        new = [{"name": "Asana", "category": "indirect", "confidence": 0.5}]
        result = merge_competitors(existing, new)
        assert len(result) == 1
        # Should keep the existing entry
        assert result[0]["confidence"] == 1.0


class TestFormatCompetitorsForDisplay:
    """Test competitor display formatting."""

    def test_format_list_of_dicts(self):
        """Test formatting list of competitor dicts."""
        competitors = [
            {"name": "Asana", "category": "direct"},
            {"name": "Monday.com", "category": "direct"},
            {"name": "Figma", "category": "indirect"},
        ]
        result = format_competitors_for_display(competitors)
        assert result == "Asana, Monday.com, Figma"

    def test_format_string_passthrough(self):
        """Test that string input passes through."""
        result = format_competitors_for_display("Asana, Monday.com")
        assert result == "Asana, Monday.com"

    def test_format_empty(self):
        """Test formatting empty input."""
        assert format_competitors_for_display(None) == ""
        assert format_competitors_for_display([]) == ""

    def test_format_mixed_types(self):
        """Test formatting mixed list (strings and dicts)."""
        competitors = [
            {"name": "Asana", "category": "direct"},
            "Slack",  # Legacy string format
        ]
        result = format_competitors_for_display(competitors)
        assert "Asana" in result
        assert "Slack" in result


class TestActionMetricCorrelation:
    """Test action-metric correlation functionality."""

    def test_get_affected_metrics_sales(self):
        """Test that sales actions affect revenue/customer metrics."""
        from backend.services.context_extractor import get_affected_metrics_for_action

        affected = get_affected_metrics_for_action("Close sales deals with new clients")
        assert "revenue" in affected
        assert "customers" in affected

    def test_get_affected_metrics_hiring(self):
        """Test that hiring actions affect team_size."""
        from backend.services.context_extractor import get_affected_metrics_for_action

        affected = get_affected_metrics_for_action("Hire two new engineers")
        assert "team_size" in affected

    def test_get_affected_metrics_growth(self):
        """Test that growth actions affect growth_rate."""
        from backend.services.context_extractor import get_affected_metrics_for_action

        affected = get_affected_metrics_for_action("Expand into new market segment")
        assert "growth_rate" in affected or "customers" in affected

    def test_get_affected_metrics_competitor(self):
        """Test that competitor actions affect competitors field."""
        from backend.services.context_extractor import get_affected_metrics_for_action

        affected = get_affected_metrics_for_action("Analyze competitive landscape")
        assert "competitors" in affected

    def test_get_affected_metrics_no_match(self):
        """Test actions that don't match any keywords."""
        from backend.services.context_extractor import get_affected_metrics_for_action

        affected = get_affected_metrics_for_action("Update documentation")
        assert len(affected) == 0

    def test_get_affected_metrics_with_description(self):
        """Test that description is also searched."""
        from backend.services.context_extractor import get_affected_metrics_for_action

        # Title doesn't match, but description does
        affected = get_affected_metrics_for_action(
            "Complete Q4 initiative",
            action_description="Focus on customer acquisition and retention efforts",
        )
        assert "customers" in affected or "growth_rate" in affected

    def test_get_affected_metrics_multiple_keywords(self):
        """Test action matching multiple keyword categories."""
        from backend.services.context_extractor import get_affected_metrics_for_action

        affected = get_affected_metrics_for_action(
            "Sales push to acquire new customers and grow revenue"
        )
        assert "revenue" in affected
        assert "customers" in affected
        assert "growth_rate" in affected
