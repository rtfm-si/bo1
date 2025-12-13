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
    get_context_extractor,
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
