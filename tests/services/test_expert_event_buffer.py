"""Unit tests for ExpertEventBuffer class.

Tests:
- Per-expert queueing and buffer window
- Event merging logic
- Critical event bypass
- Order preservation across multiple experts
"""

import pytest

from backend.api.event_publisher import ExpertEventBuffer


@pytest.fixture
def buffer():
    """Provide a fresh ExpertEventBuffer."""
    return ExpertEventBuffer()


class TestExpertEventBufferBasics:
    """Test basic queueing and flushing."""

    @pytest.mark.asyncio
    async def test_queue_event_returns_buffered_status(self, buffer):
        """Test queue_event returns correct buffered status."""
        # First event should be buffered
        result = await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_started",
            data={"round": 1},
        )
        assert result is True, "Event should be buffered (not flushed immediately)"

    @pytest.mark.asyncio
    async def test_critical_event_bypasses_buffer(self, buffer):
        """Test that critical events bypass buffer."""
        result = await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="round_start",  # Critical event
            data={"round": 1},
        )
        assert result is False, "Critical event should bypass buffer"

    @pytest.mark.asyncio
    async def test_flush_empty_buffer_returns_empty(self, buffer):
        """Test flushing empty buffer returns no events."""
        result = await buffer.flush_expert("expert_unknown")
        assert result == [], "Flushing unknown expert should return empty list"

    @pytest.mark.asyncio
    async def test_single_event_flush(self, buffer):
        """Test flushing single event."""
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_started",
            data={"round": 1},
        )

        result = await buffer.flush_expert("expert_a")
        assert len(result) == 1, "Should have 1 event after flush"
        assert result[0]["event_type"] == "expert_started"


class TestExpertEventMerging:
    """Test event merging logic."""

    @pytest.mark.asyncio
    async def test_merge_three_adjacent_events(self, buffer):
        """Test merging expert_started → reasoning → conclusion."""
        # Queue three events that should merge
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_started",
            data={"expert_id": "expert_a", "round": 1, "phase": "thinking"},
        )
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_reasoning",
            data={"expert_id": "expert_a", "round": 1, "reasoning": "My analysis..."},
        )
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_conclusion",
            data={"expert_id": "expert_a", "recommendation": "My recommendation..."},
        )

        result = await buffer.flush_expert("expert_a")
        assert len(result) == 1, "Three events should merge into one"
        assert result[0]["event_type"] == "expert_contribution_complete"
        assert result[0]["data"]["merged"] is True
        assert "reasoning" in result[0]["data"]
        assert "recommendation" in result[0]["data"]

    @pytest.mark.asyncio
    async def test_no_merge_without_pattern(self, buffer):
        """Test no merging if events don't match pattern."""
        # Queue two events (not 3, won't match merge pattern)
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_started",
            data={"expert_id": "expert_a", "round": 1},
        )
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_reasoning",
            data={"expert_id": "expert_a", "round": 1, "reasoning": "My analysis..."},
        )

        result = await buffer.flush_expert("expert_a")
        assert len(result) == 2, "Two events should not merge"
        assert result[0]["event_type"] == "expert_started"
        assert result[1]["event_type"] == "expert_reasoning"

    @pytest.mark.asyncio
    async def test_merge_with_remaining_events(self, buffer):
        """Test merge pattern handles remaining events after merge."""
        # Queue 4 events: merge first 3, leave 1
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_started",
            data={"expert_id": "expert_a", "round": 1},
        )
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_reasoning",
            data={"expert_id": "expert_a", "round": 1, "reasoning": "..."},
        )
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_conclusion",
            data={"expert_id": "expert_a", "recommendation": "..."},
        )
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_feedback",
            data={"expert_id": "expert_a", "feedback": "Additional info"},
        )

        result = await buffer.flush_expert("expert_a")
        assert len(result) == 2, "Should have 1 merged + 1 remaining"
        assert result[0]["event_type"] == "expert_contribution_complete"
        assert result[1]["event_type"] == "expert_feedback"


class TestPerExpertBuffering:
    """Test per-expert buffering isolation."""

    @pytest.mark.asyncio
    async def test_separate_buffers_per_expert(self, buffer):
        """Test that events from different experts are buffered separately."""
        # Queue events from two experts
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_started",
            data={"expert_id": "expert_a"},
        )
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_b",
            event_type="expert_started",
            data={"expert_id": "expert_b"},
        )

        # Flush expert_a
        result_a = await buffer.flush_expert("expert_a")
        assert len(result_a) == 1
        assert result_a[0]["data"]["expert_id"] == "expert_a"

        # Flush expert_b (should have its own event)
        result_b = await buffer.flush_expert("expert_b")
        assert len(result_b) == 1
        assert result_b[0]["data"]["expert_id"] == "expert_b"

    @pytest.mark.asyncio
    async def test_flush_all_multiple_experts(self, buffer):
        """Test flush_all for multiple experts."""
        # Queue events from three experts
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_started",
            data={"expert_id": "expert_a"},
        )
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_b",
            event_type="expert_reasoning",
            data={"expert_id": "expert_b", "reasoning": "..."},
        )
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_c",
            event_type="expert_conclusion",
            data={"expert_id": "expert_c", "recommendation": "..."},
        )

        result = await buffer.flush_all()
        assert len(result) == 3, "Should have buffered events from 3 experts"
        assert "expert_a" in result
        assert "expert_b" in result
        assert "expert_c" in result


class TestCriticalEventBypass:
    """Test critical event types bypass buffer."""

    @pytest.mark.asyncio
    async def test_round_events_bypass_buffer(self, buffer):
        """Test round start/end events bypass buffer."""
        result = await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="round_start",
            data={"round": 1},
        )
        assert result is False, "round_start should bypass buffer"

        result = await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="round_end",
            data={"round": 1},
        )
        assert result is False, "round_end should bypass buffer"

    @pytest.mark.asyncio
    async def test_synthesis_events_bypass_buffer(self, buffer):
        """Test synthesis events bypass buffer."""
        result = await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="synthesis_complete",
            data={"summary": "..."},
        )
        assert result is False, "synthesis_complete should bypass buffer"

    @pytest.mark.asyncio
    async def test_error_events_bypass_buffer(self, buffer):
        """Test error events bypass buffer."""
        result = await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="error",
            data={"message": "Something went wrong"},
        )
        assert result is False, "error events should bypass buffer"


class TestEventPreservation:
    """Test event data preservation during merging."""

    @pytest.mark.asyncio
    async def test_merged_event_contains_all_data(self, buffer):
        """Test merged event preserves data from all three events."""
        started_data = {"expert_id": "expert_a", "round": 1, "phase": "thinking"}
        reasoning_data = {
            "expert_id": "expert_a",
            "round": 1,
            "reasoning": "This is my analysis",
            "confidence_score": 0.85,
        }
        conclusion_data = {
            "expert_id": "expert_a",
            "recommendation": "My recommendation is to...",
        }

        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_started",
            data=started_data,
        )
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_reasoning",
            data=reasoning_data,
        )
        await buffer.queue_event(
            session_id="ses_123",
            expert_id="expert_a",
            event_type="expert_conclusion",
            data=conclusion_data,
        )

        result = await buffer.flush_expert("expert_a")
        merged = result[0]

        # Verify all data preserved
        assert merged["data"]["expert_id"] == "expert_a"
        assert merged["data"]["round"] == 1
        assert merged["data"]["phase"] == "thinking"
        assert merged["data"]["reasoning"] == "This is my analysis"
        assert merged["data"]["confidence_score"] == 0.85
        assert merged["data"]["recommendation"] == "My recommendation is to..."


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
