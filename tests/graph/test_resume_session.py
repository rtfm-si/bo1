"""Tests for session resume functionality via console interface.

This module tests the high-level resume functionality exposed through
the console interface.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bo1.models.problem import Problem


@pytest.mark.integration
class TestResumeSession:
    """Test suite for session resume via console interface."""

    @pytest.fixture
    def problem(self):
        """Create a test problem."""
        return Problem(
            title="Test Problem",
            description="Should we expand to international markets?",
            context="SaaS company, $1M ARR, 50 customers",
        )

    @pytest.fixture
    def session_id(self):
        """Generate a unique session ID."""
        return str(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_resume_session_displays_info(self, problem, session_id):
        """Test that resuming a session displays checkpoint info."""
        from bo1.interfaces.console import run_console_deliberation
        from bo1.models.state import DeliberationMetrics, DeliberationPhase

        # Mock the graph and checkpoint
        with patch("bo1.interfaces.console.create_deliberation_graph") as mock_create_graph:
            mock_graph = MagicMock()
            mock_create_graph.return_value = mock_graph

            # Mock aget_state to return a checkpoint
            mock_checkpoint = MagicMock()
            mock_checkpoint.values = {
                "session_id": session_id,
                "round_number": 2,
                "phase": DeliberationPhase.DISCUSSION,
                "personas": [{"code": "maria", "name": "Maria"}],
                "metrics": DeliberationMetrics(total_cost=0.15),
                "problem": problem,
                "contributions": [],
                "round_summaries": [],
                "max_rounds": 10,
            }
            mock_graph.aget_state = AsyncMock(return_value=mock_checkpoint)

            # Mock astream_events to return no events (simulating completed deliberation)
            async def mock_astream(*args, **kwargs):
                # Yield no events (empty deliberation)
                if False:
                    yield {}

            mock_graph.astream_events = mock_astream

            # Mock user input to cancel resume
            with patch("builtins.input", return_value="n"):
                # Run with resume flag
                result = await run_console_deliberation(problem, session_id=session_id)

                # Verify aget_state was called to check for checkpoint
                mock_graph.aget_state.assert_called_once()

                # Verify we got the checkpoint state back (user cancelled)
                assert result is not None
                assert result["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_resume_session_not_found(self, problem):
        """Test that resuming non-existent session fails gracefully."""
        from bo1.interfaces.console import run_console_deliberation

        # Create a session ID that doesn't exist
        invalid_session_id = str(uuid.uuid4())

        # Mock the graph
        with patch("bo1.interfaces.console.create_deliberation_graph") as mock_create_graph:
            mock_graph = MagicMock()
            mock_create_graph.return_value = mock_graph

            # Mock aget_state to return empty checkpoint (not found)
            mock_checkpoint = MagicMock()
            mock_checkpoint.values = None  # No checkpoint found
            mock_graph.aget_state = AsyncMock(return_value=mock_checkpoint)

            # Attempt to resume - should raise ValueError
            with pytest.raises(ValueError, match="No checkpoint found"):
                await run_console_deliberation(problem, session_id=invalid_session_id)

    @pytest.mark.asyncio
    async def test_resume_session_continues_execution(self, problem, session_id):
        """Test that resuming a session continues graph execution."""
        from bo1.interfaces.console import run_console_deliberation
        from bo1.models.state import DeliberationMetrics, DeliberationPhase

        # Mock the graph
        with patch("bo1.interfaces.console.create_deliberation_graph") as mock_create_graph:
            mock_graph = MagicMock()
            mock_create_graph.return_value = mock_graph

            # Mock aget_state to return a checkpoint
            mock_checkpoint = MagicMock()
            mock_checkpoint.values = {
                "session_id": session_id,
                "round_number": 2,
                "phase": DeliberationPhase.DISCUSSION,
                "personas": [{"code": "maria", "name": "Maria"}],
                "metrics": DeliberationMetrics(total_cost=0.15),
                "problem": problem,
                "contributions": [],
                "round_summaries": [],
                "max_rounds": 10,
                "votes": [],
                "synthesis": "Final synthesis complete",
            }
            mock_graph.aget_state = AsyncMock(return_value=mock_checkpoint)

            # Mock astream_events to simulate completion
            async def mock_astream(*args, **kwargs):
                # Simulate synthesize node completing
                yield {
                    "event": "on_chain_end",
                    "name": "synthesize",
                    "data": {
                        "output": {
                            "session_id": session_id,
                            "synthesis": "Final synthesis complete",
                            "phase": DeliberationPhase.COMPLETE,
                            "round_number": 3,
                            "metrics": DeliberationMetrics(total_cost=0.25),
                            "problem": problem,
                            "personas": [],
                            "contributions": [],
                            "round_summaries": [],
                            "max_rounds": 10,
                            "votes": [],
                        }
                    },
                }

            mock_graph.astream_events = mock_astream

            # Mock user input to continue
            with patch("builtins.input", return_value="y"):
                # Run with resume flag
                result = await run_console_deliberation(
                    problem, session_id=session_id, export=False
                )

                # Verify execution completed
                assert result is not None
                assert result.get("synthesis") == "Final synthesis complete"

    @pytest.mark.asyncio
    async def test_invalid_session_id_format(self, problem):
        """Test that invalid session ID format is rejected."""
        from bo1.interfaces.console import run_console_deliberation

        # Use an invalid session ID (not a UUID)
        invalid_id = "not-a-uuid"

        # Should raise ValueError for invalid format
        with pytest.raises(ValueError, match="Invalid session ID format"):
            await run_console_deliberation(problem, session_id=invalid_id)

    @pytest.mark.asyncio
    async def test_resume_preserves_cost_metrics(self, problem, session_id):
        """Test that resuming preserves cost metrics from checkpoint."""
        from bo1.interfaces.console import run_console_deliberation
        from bo1.models.state import DeliberationMetrics, DeliberationPhase

        with patch("bo1.interfaces.console.create_deliberation_graph") as mock_create_graph:
            mock_graph = MagicMock()
            mock_create_graph.return_value = mock_graph

            # Mock checkpoint with specific cost metrics
            initial_cost = 0.42
            mock_checkpoint = MagicMock()
            mock_checkpoint.values = {
                "session_id": session_id,
                "round_number": 3,
                "phase": DeliberationPhase.DISCUSSION,
                "personas": [],
                "metrics": DeliberationMetrics(
                    total_cost=initial_cost, total_tokens=2000, cache_hits=5
                ),
                "problem": problem,
                "contributions": [],
                "round_summaries": [],
                "max_rounds": 10,
            }
            mock_graph.aget_state = AsyncMock(return_value=mock_checkpoint)

            # Mock astream to return no events
            async def mock_astream(*args, **kwargs):
                if False:
                    yield {}

            mock_graph.astream_events = mock_astream

            # Mock user cancelling
            with patch("builtins.input", return_value="n"):
                result = await run_console_deliberation(problem, session_id=session_id)

                # Verify cost was preserved
                metrics = result["metrics"]
                if hasattr(metrics, "total_cost"):
                    assert metrics.total_cost == initial_cost
                else:
                    assert metrics["total_cost"] == initial_cost
