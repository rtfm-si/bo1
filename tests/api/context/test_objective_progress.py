"""Tests for strategic objective progress tracking."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from backend.api.context.models import (
    ObjectiveProgress,
    ObjectiveProgressListResponse,
    ObjectiveProgressResponse,
    ObjectiveProgressUpdate,
)


class TestObjectiveProgressModel:
    """Tests for ObjectiveProgress Pydantic model."""

    def test_valid_progress(self):
        """Verify valid progress data is accepted."""
        progress = ObjectiveProgress(
            current="5K",
            target="10K",
            unit="MRR",
            updated_at=datetime.now(),
        )
        assert progress.current == "5K"
        assert progress.target == "10K"
        assert progress.unit == "MRR"

    def test_progress_without_unit(self):
        """Verify unit is optional."""
        progress = ObjectiveProgress(
            current="50%",
            target="80%",
            unit=None,
            updated_at=datetime.now(),
        )
        assert progress.unit is None

    def test_current_max_length(self):
        """Verify current value max length is enforced."""
        with pytest.raises(ValidationError):
            ObjectiveProgress(
                current="x" * 51,  # Exceeds 50 char limit
                target="10K",
                updated_at=datetime.now(),
            )

    def test_target_max_length(self):
        """Verify target value max length is enforced."""
        with pytest.raises(ValidationError):
            ObjectiveProgress(
                current="5K",
                target="x" * 51,  # Exceeds 50 char limit
                updated_at=datetime.now(),
            )

    def test_unit_max_length(self):
        """Verify unit max length is enforced."""
        with pytest.raises(ValidationError):
            ObjectiveProgress(
                current="5K",
                target="10K",
                unit="x" * 21,  # Exceeds 20 char limit
                updated_at=datetime.now(),
            )


class TestObjectiveProgressUpdateModel:
    """Tests for ObjectiveProgressUpdate request model."""

    def test_valid_update(self):
        """Verify valid update data is accepted."""
        update = ObjectiveProgressUpdate(
            current="7K",
            target="10K",
            unit="MRR",
        )
        assert update.current == "7K"
        assert update.target == "10K"

    def test_update_requires_current(self):
        """Verify current is required."""
        with pytest.raises(ValidationError):
            ObjectiveProgressUpdate(
                target="10K",
            )

    def test_update_requires_target(self):
        """Verify target is required."""
        with pytest.raises(ValidationError):
            ObjectiveProgressUpdate(
                current="5K",
            )

    def test_current_min_length(self):
        """Verify current value min length is enforced."""
        with pytest.raises(ValidationError):
            ObjectiveProgressUpdate(
                current="",  # Empty string
                target="10K",
            )

    def test_target_min_length(self):
        """Verify target value min length is enforced."""
        with pytest.raises(ValidationError):
            ObjectiveProgressUpdate(
                current="5K",
                target="",  # Empty string
            )


class TestObjectiveProgressResponseModel:
    """Tests for ObjectiveProgressResponse model."""

    def test_response_with_progress(self):
        """Verify response with progress data."""
        response = ObjectiveProgressResponse(
            objective_index=0,
            objective_text="Increase conversion rate",
            progress=ObjectiveProgress(
                current="5%",
                target="10%",
                unit="%",
                updated_at=datetime.now(),
            ),
        )
        assert response.objective_index == 0
        assert response.progress is not None
        assert response.progress.current == "5%"

    def test_response_without_progress(self):
        """Verify response without progress (null)."""
        response = ObjectiveProgressResponse(
            objective_index=1,
            objective_text="Reduce churn",
            progress=None,
        )
        assert response.progress is None


class TestObjectiveProgressListResponseModel:
    """Tests for ObjectiveProgressListResponse model."""

    def test_list_response_empty(self):
        """Verify empty list response."""
        response = ObjectiveProgressListResponse(
            objectives=[],
            count=0,
        )
        assert len(response.objectives) == 0
        assert response.count == 0

    def test_list_response_with_objectives(self):
        """Verify list response with multiple objectives."""
        response = ObjectiveProgressListResponse(
            objectives=[
                ObjectiveProgressResponse(
                    objective_index=0,
                    objective_text="Increase revenue",
                    progress=ObjectiveProgress(
                        current="5K",
                        target="10K",
                        unit="MRR",
                        updated_at=datetime.now(),
                    ),
                ),
                ObjectiveProgressResponse(
                    objective_index=1,
                    objective_text="Reduce churn",
                    progress=None,
                ),
            ],
            count=1,  # Only 1 has progress set
        )
        assert len(response.objectives) == 2
        assert response.count == 1


class TestObjectiveProgressRepository:
    """Tests for strategic_objectives_progress in user_repository."""

    def test_progress_field_in_context_fields(self):
        """Verify strategic_objectives_progress is in CONTEXT_FIELDS."""
        from bo1.state.repositories.user_repository import UserRepository

        assert "strategic_objectives_progress" in UserRepository.CONTEXT_FIELDS
