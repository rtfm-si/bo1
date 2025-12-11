"""Tests for ContributionSummary model validation."""

import pytest
from pydantic import ValidationError

from bo1.models import ContributionSummary


class TestContributionSummaryValidation:
    """Test ContributionSummary model validation."""

    def test_contribution_summary_valid(self) -> None:
        """Valid summary with all fields passes validation."""
        summary = ContributionSummary(
            concise="Expert recommends phased migration approach.",
            looking_for="Evaluating migration feasibility",
            value_added="Highlights organizational complexity",
            concerns=["Timeline risk", "Budget constraints"],
            questions=["What is the deadline?"],
        )
        assert summary.concise == "Expert recommends phased migration approach."
        assert summary.schema_valid is True
        assert summary.parse_error is False

    def test_contribution_summary_defaults(self) -> None:
        """Empty summary gets default values."""
        summary = ContributionSummary()
        assert summary.concise == ""
        assert summary.looking_for == ""
        assert summary.value_added == ""
        assert summary.concerns == []
        assert summary.questions == []
        assert summary.schema_valid is True
        assert summary.parse_error is False

    def test_contribution_summary_coerces_string_to_list(self) -> None:
        """String concerns/questions are coerced to single-item lists."""
        summary = ContributionSummary(
            concerns="Single concern",
            questions="Single question",
        )
        assert summary.concerns == ["Single concern"]
        assert summary.questions == ["Single question"]

    def test_contribution_summary_coerces_none_to_list(self) -> None:
        """None concerns/questions are coerced to empty lists."""
        summary = ContributionSummary(
            concerns=None,
            questions=None,
        )
        assert summary.concerns == []
        assert summary.questions == []

    def test_contribution_summary_truncates_long_concise(self) -> None:
        """Concise field over 500 chars raises ValidationError."""
        long_text = "x" * 501
        with pytest.raises(ValidationError) as exc_info:
            ContributionSummary(concise=long_text)
        assert "concise" in str(exc_info.value)

    def test_contribution_summary_model_dump(self) -> None:
        """model_dump returns dict with all fields."""
        summary = ContributionSummary(
            concise="Test summary",
            concerns=["Risk A"],
        )
        data = summary.model_dump()
        assert data["concise"] == "Test summary"
        assert data["concerns"] == ["Risk A"]
        assert data["schema_valid"] is True
        assert "parse_error" in data

    def test_contribution_summary_parse_error_flag(self) -> None:
        """parse_error flag can be set for fallback summaries."""
        summary = ContributionSummary(
            concise="Fallback",
            parse_error=True,
            schema_valid=False,
        )
        assert summary.parse_error is True
        assert summary.schema_valid is False
