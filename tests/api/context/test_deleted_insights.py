"""Tests verifying deleted insights are excluded from all retrieval paths.

Insights (clarifications) use hard-delete: when deleted via
DELETE /api/v1/context/insights/{question_hash}, the entry is removed
from the clarifications JSONB dict entirely.

These tests verify:
1. get_insights() API returns only active insights
2. Deleted insights don't appear in meeting context
3. Context collection node excludes deleted insights
"""

import base64
from unittest.mock import patch

import pytest


class TestDeletedInsightsExcluded:
    """Test that deleted insights are properly excluded from all retrieval paths."""

    @pytest.fixture
    def mock_user(self) -> dict:
        """Create a mock authenticated user."""
        return {"user_id": "test-user-123", "sub": "test-user-123"}

    @pytest.fixture
    def sample_clarifications(self) -> dict:
        """Create sample clarifications with metadata."""
        return {
            "What is your revenue?": {
                "answer": "$100K MRR",
                "answered_at": "2025-01-15T10:00:00Z",
                "session_id": "bo1_session1",
                "category": "revenue",
                "source": "meeting",
            },
            "How many customers?": {
                "answer": "150 active customers",
                "answered_at": "2025-01-14T10:00:00Z",
                "session_id": "bo1_session2",
                "category": "customers",
                "source": "meeting",
            },
        }

    def test_get_insights_returns_only_stored_insights(
        self, mock_user: dict, sample_clarifications: dict
    ) -> None:
        """Verify get_insights() only returns insights that exist in storage."""
        from backend.api.context.routes import get_insights

        # Mock user_repository.get_context to return sample clarifications
        with patch("backend.api.context.insights_routes.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {"clarifications": sample_clarifications}

            # Call get_insights (synchronously for test)
            import asyncio

            with patch(
                "backend.api.context.insights_routes.get_current_user", return_value=mock_user
            ):
                response = asyncio.get_event_loop().run_until_complete(get_insights(mock_user))

            # Verify both insights are returned
            assert response.total_count == 2
            questions = [c.question for c in response.clarifications]
            assert "What is your revenue?" in questions
            assert "How many customers?" in questions

    def test_deleted_insight_not_returned(
        self, mock_user: dict, sample_clarifications: dict
    ) -> None:
        """Verify that after deletion, insight is no longer returned."""
        from backend.api.context.routes import get_insights

        # Simulate deletion by removing one insight from the dict
        remaining = {k: v for k, v in sample_clarifications.items() if k != "What is your revenue?"}

        with patch("backend.api.context.insights_routes.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {"clarifications": remaining}

            import asyncio

            response = asyncio.get_event_loop().run_until_complete(get_insights(mock_user))

            # Only one insight should remain
            assert response.total_count == 1
            questions = [c.question for c in response.clarifications]
            assert "What is your revenue?" not in questions
            assert "How many customers?" in questions

    def test_empty_clarifications_returns_empty_list(self, mock_user: dict) -> None:
        """Verify empty clarifications dict returns empty response."""
        from backend.api.context.routes import get_insights

        with patch("backend.api.context.insights_routes.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {"clarifications": {}}

            import asyncio

            response = asyncio.get_event_loop().run_until_complete(get_insights(mock_user))

            assert response.total_count == 0
            assert response.clarifications == []

    def test_no_context_returns_empty_list(self, mock_user: dict) -> None:
        """Verify missing context returns empty response."""
        from backend.api.context.routes import get_insights

        with patch("backend.api.context.insights_routes.user_repository") as mock_repo:
            mock_repo.get_context.return_value = None

            import asyncio

            response = asyncio.get_event_loop().run_until_complete(get_insights(mock_user))

            assert response.total_count == 0
            assert response.clarifications == []


class TestDeletedInsightsInMeetingContext:
    """Test that deleted insights don't appear in meeting context."""

    @pytest.fixture
    def sample_context_with_clarifications(self) -> dict:
        """Create sample context data with clarifications."""
        return {
            "business_model": "B2B SaaS",
            "revenue": "$100K MRR",
            "clarifications": {
                "What is your pricing model?": {
                    "answer": "Subscription-based, $50/mo per seat",
                    "answered_at": "2025-01-15T10:00:00Z",
                    "category": "revenue",
                    "source": "meeting",
                },
            },
        }

    def test_context_collection_only_includes_stored_clarifications(
        self, sample_context_with_clarifications: dict
    ) -> None:
        """Verify context_collection_node only includes clarifications that exist."""
        from bo1.graph.nodes.context import context_collection_node
        from bo1.models.problem import Problem

        # Create mock state
        problem = Problem(
            title="Test Problem",
            description="Test problem",
            context="",
            sub_problems=[],
        )

        state = {
            "session_id": "bo1_test123",
            "user_id": "test-user-123",
            "problem": problem,
        }

        with patch("bo1.graph.nodes.context.collection.user_repository") as mock_repo:
            mock_repo.get_context.return_value = sample_context_with_clarifications

            import asyncio

            result = asyncio.get_event_loop().run_until_complete(context_collection_node(state))

            # Verify the clarification is in the context
            updated_problem = result.get("problem")
            assert updated_problem is not None
            assert "What is your pricing model?" in updated_problem.context
            assert "Subscription-based" in updated_problem.context

    def test_deleted_clarification_not_in_meeting_context(self) -> None:
        """Verify that after deletion, clarification doesn't appear in meeting context."""
        from bo1.graph.nodes.context import context_collection_node
        from bo1.models.problem import Problem

        # Context with empty clarifications (simulating all deleted)
        context_data = {
            "business_model": "B2B SaaS",
            "revenue": "$100K MRR",
            "clarifications": {},  # Empty after deletion
        }

        problem = Problem(
            title="Test Problem",
            description="Test problem",
            context="",
            sub_problems=[],
        )

        state = {
            "session_id": "bo1_test123",
            "user_id": "test-user-123",
            "problem": problem,
        }

        with patch("bo1.graph.nodes.context.collection.user_repository") as mock_repo:
            mock_repo.get_context.return_value = context_data

            import asyncio

            result = asyncio.get_event_loop().run_until_complete(context_collection_node(state))

            updated_problem = result.get("problem")
            assert updated_problem is not None
            # Clarifications section should not be present with empty clarifications
            assert "User Insights" not in updated_problem.context

    def test_partial_deletion_only_removes_deleted_insight(self) -> None:
        """Verify partial deletion only removes the deleted insight."""
        from bo1.graph.nodes.context import context_collection_node
        from bo1.models.problem import Problem

        # Context with one clarification remaining (one was deleted)
        context_data = {
            "business_model": "B2B SaaS",
            "clarifications": {
                "Remaining question?": {
                    "answer": "Still here",
                    "answered_at": "2025-01-15T10:00:00Z",
                    "category": "uncategorized",
                    "source": "meeting",
                },
                # "Deleted question?" was removed
            },
        }

        problem = Problem(
            title="Test Problem",
            description="Test problem",
            context="",
            sub_problems=[],
        )

        state = {
            "session_id": "bo1_test123",
            "user_id": "test-user-123",
            "problem": problem,
        }

        with patch("bo1.graph.nodes.context.collection.user_repository") as mock_repo:
            mock_repo.get_context.return_value = context_data

            import asyncio

            result = asyncio.get_event_loop().run_until_complete(context_collection_node(state))

            updated_problem = result.get("problem")
            assert "Remaining question?" in updated_problem.context
            assert "Still here" in updated_problem.context


class TestInsightDeletionAPI:
    """Test the insight deletion API behavior."""

    @pytest.fixture
    def mock_user(self) -> dict:
        """Create a mock authenticated user."""
        return {"user_id": "test-user-123", "sub": "test-user-123"}

    def test_delete_insight_removes_from_storage(self, mock_user: dict) -> None:
        """Verify DELETE endpoint removes insight from clarifications dict."""
        from backend.api.context.routes import delete_insight

        question = "What is your revenue?"
        question_hash = base64.urlsafe_b64encode(question.encode()).decode()

        initial_clarifications = {
            question: {"answer": "$100K", "source": "meeting"},
            "Another question?": {"answer": "Answer", "source": "meeting"},
        }

        with patch("backend.api.context.insights_routes.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {"clarifications": initial_clarifications.copy()}

            import asyncio

            result = asyncio.get_event_loop().run_until_complete(
                delete_insight(question_hash, mock_user)
            )

            # Verify delete was successful
            assert result == {"status": "deleted"}

            # Verify save_context was called with updated clarifications
            mock_repo.save_context.assert_called_once()
            call_args = mock_repo.save_context.call_args
            saved_context = call_args[0][1]
            assert question not in saved_context["clarifications"]
            assert "Another question?" in saved_context["clarifications"]

    def test_delete_nonexistent_insight_returns_404(self, mock_user: dict) -> None:
        """Verify deleting non-existent insight returns 404."""
        from fastapi import HTTPException

        from backend.api.context.routes import delete_insight

        question = "Non-existent question?"
        question_hash = base64.urlsafe_b64encode(question.encode()).decode()

        with patch("backend.api.context.insights_routes.user_repository") as mock_repo:
            mock_repo.get_context.return_value = {"clarifications": {}}

            import asyncio

            with pytest.raises(HTTPException) as exc_info:
                asyncio.get_event_loop().run_until_complete(
                    delete_insight(question_hash, mock_user)
                )

            assert exc_info.value.status_code == 404
            assert "not found" in str(exc_info.value.detail).lower()
