"""Tests for clarification JSONB validation."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.api.context.models import (
    ClarificationsStorage,
    ClarificationStorageEntry,
    InsightCategory,
)
from backend.api.context.services import (
    normalize_clarification_for_storage,
    validate_clarification_entry,
    validate_clarifications_storage,
)
from backend.services.insight_parser import is_valid_insight_response


class TestClarificationStorageEntry:
    """Tests for ClarificationStorageEntry model."""

    def test_valid_new_format_passes(self):
        """Verify valid new format entry validates correctly."""
        data = {
            "answer": "Our MRR is $25,000",
            "answered_at": "2025-01-15T10:30:00Z",
            "session_id": "abc123",
            "source": "meeting",
            "category": "revenue",
            "confidence_score": 0.85,
            "summary": "MRR is $25K",
        }
        entry = ClarificationStorageEntry.model_validate(data)
        assert entry.answer == "Our MRR is $25,000"
        assert entry.source == "meeting"
        assert entry.category == InsightCategory.REVENUE
        assert entry.confidence_score == 0.85

    def test_minimal_entry_passes(self):
        """Verify minimal entry with only answer passes."""
        entry = ClarificationStorageEntry.model_validate({"answer": "Yes"})
        assert entry.answer == "Yes"
        assert entry.source == "meeting"  # default

    def test_missing_answer_raises_error(self):
        """Verify missing answer raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClarificationStorageEntry.model_validate({"source": "meeting"})
        assert "answer" in str(exc_info.value)

    def test_empty_answer_raises_error(self):
        """Verify empty answer raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClarificationStorageEntry.model_validate({"answer": ""})
        assert "answer" in str(exc_info.value).lower()

    def test_invalid_source_raises_error(self):
        """Verify invalid source value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClarificationStorageEntry.model_validate({"answer": "test", "source": "unknown"})
        assert "source" in str(exc_info.value).lower()

    def test_confidence_score_bounds(self):
        """Verify confidence_score must be between 0 and 1."""
        # Valid bounds
        entry = ClarificationStorageEntry.model_validate(
            {"answer": "test", "confidence_score": 0.0}
        )
        assert entry.confidence_score == 0.0

        entry = ClarificationStorageEntry.model_validate(
            {"answer": "test", "confidence_score": 1.0}
        )
        assert entry.confidence_score == 1.0

        # Invalid: > 1
        with pytest.raises(ValidationError):
            ClarificationStorageEntry.model_validate({"answer": "test", "confidence_score": 1.5})

        # Invalid: < 0
        with pytest.raises(ValidationError):
            ClarificationStorageEntry.model_validate({"answer": "test", "confidence_score": -0.1})

    def test_metric_nested_validation(self):
        """Verify metric field validates nested structure."""
        data = {
            "answer": "Revenue is $50K MRR",
            "metric": {
                "value": 50000,
                "unit": "USD",
                "metric_type": "MRR",
                "period": "monthly",
                "raw_text": "$50K MRR",
            },
        }
        entry = ClarificationStorageEntry.model_validate(data)
        assert entry.metric is not None
        assert entry.metric.value == 50000
        assert entry.metric.unit == "USD"


class TestClarificationsStorage:
    """Tests for ClarificationsStorage root model."""

    def test_empty_dict_passes(self):
        """Verify empty dict validates."""
        storage = ClarificationsStorage.model_validate({})
        assert storage.root == {}

    def test_valid_multiple_entries(self):
        """Verify multiple valid entries pass."""
        data = {
            "What is your MRR?": {
                "answer": "$25,000",
                "source": "meeting",
            },
            "How many customers?": {
                "answer": "150 active customers",
                "source": "manual",
            },
        }
        storage = ClarificationsStorage.model_validate(data)
        assert len(storage.root) == 2
        assert storage.root["What is your MRR?"].answer == "$25,000"

    def test_invalid_entry_raises_error(self):
        """Verify invalid entry in collection raises error."""
        data = {
            "Valid question": {"answer": "valid"},
            "Invalid question": {"source": "meeting"},  # missing answer
        }
        with pytest.raises(ValidationError):
            ClarificationsStorage.model_validate(data)


class TestValidateClarificationEntry:
    """Tests for validate_clarification_entry helper."""

    def test_valid_dict_passes(self):
        """Verify valid dict validates."""
        result = validate_clarification_entry(
            "What is your MRR?", {"answer": "$25,000", "source": "meeting"}
        )
        assert result.answer == "$25,000"

    def test_legacy_string_format_converts(self):
        """Verify legacy string format is converted to dict."""
        result = validate_clarification_entry("What is your MRR?", "$25,000")
        assert result.answer == "$25,000"
        assert result.source == "migration"

    def test_invalid_dict_raises_error(self):
        """Verify invalid dict raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_clarification_entry("Question?", {"not_answer": "value"})


class TestValidateClarificationsStorage:
    """Tests for validate_clarifications_storage helper."""

    def test_empty_dict_passes(self):
        """Verify empty dict passes."""
        result = validate_clarifications_storage({})
        assert result.root == {}

    def test_none_returns_empty(self):
        """Verify None input returns empty storage."""
        result = validate_clarifications_storage(None)
        assert result.root == {}

    def test_legacy_string_entries_convert(self):
        """Verify legacy string entries are converted."""
        raw = {
            "Question 1": "Answer 1",
            "Question 2": {"answer": "Answer 2", "source": "meeting"},
        }
        result = validate_clarifications_storage(raw)
        assert result.root["Question 1"].answer == "Answer 1"
        assert result.root["Question 1"].source == "migration"
        assert result.root["Question 2"].answer == "Answer 2"
        assert result.root["Question 2"].source == "meeting"

    def test_invalid_type_raises_error(self):
        """Verify invalid entry type raises error."""
        raw = {
            "Question": 12345,  # Invalid: not str or dict
        }
        with pytest.raises(ValueError, match="expected dict or str"):
            validate_clarifications_storage(raw)


class TestNormalizeClarificationForStorage:
    """Tests for normalize_clarification_for_storage helper."""

    def test_returns_serializable_dict(self):
        """Verify output is JSON-serializable dict."""
        entry = {
            "answer": "Test answer",
            "answered_at": datetime.now(UTC).isoformat(),
            "source": "meeting",
        }
        result = normalize_clarification_for_storage(entry)
        assert isinstance(result, dict)
        assert result["answer"] == "Test answer"
        assert result["source"] == "meeting"

    def test_excludes_none_values(self):
        """Verify None values are excluded from output."""
        entry = {"answer": "Test", "category": None, "summary": None}
        result = normalize_clarification_for_storage(entry)
        assert "category" not in result
        assert "summary" not in result

    def test_invalid_entry_raises_error(self):
        """Verify invalid entry raises ValidationError."""
        with pytest.raises(ValidationError):
            normalize_clarification_for_storage({"not_answer": "value"})


class TestInsightResponseFilteringIntegration:
    """Integration tests for filtering null/empty insight responses before storage."""

    def test_valid_insight_passes_filter_and_validates(self):
        """Verify valid insight passes filter and can be normalized for storage."""
        answer = "Our MRR is $25,000"
        # Step 1: Filter check
        assert is_valid_insight_response(answer) is True
        # Step 2: Normalize for storage
        entry = {
            "answer": answer,
            "answered_at": datetime.now(UTC).isoformat(),
            "source": "meeting",
        }
        result = normalize_clarification_for_storage(entry)
        assert result["answer"] == answer

    def test_invalid_insight_is_filtered_out(self):
        """Verify invalid insight responses are filtered before storage attempt."""
        invalid_responses = [
            "",
            "   ",
            "none",
            "None",
            "n/a",
            "N/A",
            "not applicable",
            "no",
            "-",
            "...",
            "null",
            "unknown",
        ]
        for response in invalid_responses:
            # These should be filtered BEFORE attempting storage
            assert is_valid_insight_response(response) is False, f"'{response}' should be invalid"

    def test_none_in_context_passes_and_stores(self):
        """Verify 'none' in a meaningful context is accepted and stored."""
        answer = "None of the above apply because we're a B2B SaaS company"
        # Filter check passes
        assert is_valid_insight_response(answer) is True
        # Normalization succeeds
        entry = {
            "answer": answer,
            "answered_at": datetime.now(UTC).isoformat(),
            "source": "meeting",
        }
        result = normalize_clarification_for_storage(entry)
        assert result["answer"] == answer

    def test_workflow_filters_then_stores(self):
        """Simulate the full workflow: filter invalid, store valid."""
        answers_to_process = {
            "What is your revenue?": "$50,000 MRR",
            "How many competitors?": "none",  # Invalid - should be filtered
            "What is your team size?": "5 people",
            "Any constraints?": "n/a",  # Invalid - should be filtered
        }

        stored_clarifications = {}
        for question, answer in answers_to_process.items():
            if is_valid_insight_response(answer):
                entry = {
                    "answer": answer,
                    "answered_at": datetime.now(UTC).isoformat(),
                    "source": "meeting",
                }
                stored_clarifications[question] = normalize_clarification_for_storage(entry)

        # Only valid answers should be stored
        assert len(stored_clarifications) == 2
        assert "What is your revenue?" in stored_clarifications
        assert "What is your team size?" in stored_clarifications
        assert "How many competitors?" not in stored_clarifications
        assert "Any constraints?" not in stored_clarifications
