"""Tests for ISS-002 fix: Graph execution preserves paused status for clarification.

Validates:
- Graph execution does not mark session as "completed" when paused for clarification
- pending_clarification in state prevents completion
- stop_reason="clarification_needed" prevents completion
"""

from unittest.mock import MagicMock

import pytest


class TestClarificationPausePreservation:
    """Test that graph execution preserves paused status for clarification sessions."""

    @pytest.fixture
    def mock_redis_manager(self):
        """Create mock Redis manager."""
        manager = MagicMock()
        manager.is_available = True
        manager.redis = MagicMock()
        manager.load_metadata.return_value = {"status": "running", "user_id": "user123"}
        manager.save_metadata.return_value = True
        return manager

    @pytest.fixture
    def session_manager(self, mock_redis_manager):
        """Create SessionManager with mocked dependencies."""
        from bo1.graph.execution import SessionManager

        manager = SessionManager(
            redis_manager=mock_redis_manager,
            admin_user_ids=set(),
            max_concurrent_sessions=10,
        )
        return manager

    @pytest.mark.asyncio
    async def test_pending_clarification_prevents_completed_status(
        self, session_manager, mock_redis_manager
    ):
        """When pending_clarification is set, session should NOT be marked completed."""

        # Mock the graph coroutine to return state with pending_clarification
        async def mock_graph_execution():
            return {
                "pending_clarification": {
                    "questions": ["What is your budget?"],
                    "phase": "pre_deliberation",
                    "reason": "Need budget info",
                },
                "stop_reason": "clarification_needed",
            }

        # Track status updates
        status_updates = []

        def track_update(session_id, status, **kwargs):
            status_updates.append({"session_id": session_id, "status": status, **kwargs})

        session_manager._update_session_status = MagicMock(side_effect=track_update)

        # Start session
        task = await session_manager.start_session(
            session_id="bo1_test_clarification",
            user_id="user123",
            coro=mock_graph_execution(),
        )

        # Wait for task to complete
        await task

        # Verify _update_session_status was NOT called with "completed"
        completed_calls = [u for u in status_updates if u["status"] == "completed"]
        assert len(completed_calls) == 0, (
            f"Session should NOT be marked completed when pending_clarification is set. "
            f"Status updates: {status_updates}"
        )

    @pytest.mark.asyncio
    async def test_stop_reason_clarification_needed_prevents_completed_status(
        self, session_manager, mock_redis_manager
    ):
        """When stop_reason=clarification_needed, session should NOT be marked completed."""

        # Mock the graph coroutine
        async def mock_graph_execution():
            return {
                "stop_reason": "clarification_needed",
                "current_phase": "identify_gaps",
            }

        status_updates = []

        def track_update(session_id, status, **kwargs):
            status_updates.append({"session_id": session_id, "status": status, **kwargs})

        session_manager._update_session_status = MagicMock(side_effect=track_update)

        task = await session_manager.start_session(
            session_id="bo1_test_stop_reason",
            user_id="user123",
            coro=mock_graph_execution(),
        )

        await task

        completed_calls = [u for u in status_updates if u["status"] == "completed"]
        assert len(completed_calls) == 0, (
            f"Session should NOT be marked completed when stop_reason=clarification_needed. "
            f"Status updates: {status_updates}"
        )

    @pytest.mark.asyncio
    async def test_successful_completion_marks_completed(self, session_manager, mock_redis_manager):
        """When synthesis is present and no clarification, session SHOULD be marked completed."""

        async def mock_graph_execution():
            return {
                "synthesis": "Final recommendation: Do X because Y.",
                "stop_reason": None,
                "current_phase": "synthesis",
            }

        status_updates = []

        def track_update(session_id, status, **kwargs):
            status_updates.append({"session_id": session_id, "status": status, **kwargs})

        session_manager._update_session_status = MagicMock(side_effect=track_update)

        task = await session_manager.start_session(
            session_id="bo1_test_completion",
            user_id="user123",
            coro=mock_graph_execution(),
        )

        await task

        completed_calls = [u for u in status_updates if u["status"] == "completed"]
        assert len(completed_calls) == 1, (
            f"Session SHOULD be marked completed when synthesis is present. "
            f"Status updates: {status_updates}"
        )

    @pytest.mark.asyncio
    async def test_sub_problem_results_without_clarification_marks_completed(
        self, session_manager, mock_redis_manager
    ):
        """When sub_problem_results is present without clarification, session SHOULD be completed."""

        async def mock_graph_execution():
            return {
                "sub_problem_results": [{"index": 0, "synthesis": "Sub-problem solved."}],
                "stop_reason": None,
            }

        status_updates = []

        def track_update(session_id, status, **kwargs):
            status_updates.append({"session_id": session_id, "status": status, **kwargs})

        session_manager._update_session_status = MagicMock(side_effect=track_update)

        task = await session_manager.start_session(
            session_id="bo1_test_subproblem",
            user_id="user123",
            coro=mock_graph_execution(),
        )

        await task

        completed_calls = [u for u in status_updates if u["status"] == "completed"]
        assert len(completed_calls) == 1, (
            f"Session SHOULD be marked completed with sub_problem_results. "
            f"Status updates: {status_updates}"
        )
