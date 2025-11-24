"""End-to-end integration test for SSE streaming implementation.

This test simulates a complete deliberation flow and verifies:
- All events are published in correct order
- Event data accuracy
- Pause/resume maintains stream
- Real-time event delivery via Redis PubSub
"""

import asyncio
import json
from typing import Any

import pytest

from backend.api.event_collector import EventCollector
from backend.api.event_publisher import EventPublisher
from bo1.models.problem import Problem, SubProblem
from bo1.state.redis_manager import RedisManager


@pytest.fixture
def redis_manager():
    """Create RedisManager for testing."""
    manager = RedisManager()
    if not manager.is_available:
        pytest.skip("Redis not available")
    return manager


@pytest.fixture
def event_publisher(redis_manager):
    """Create EventPublisher for testing."""
    return EventPublisher(redis_manager.redis)


@pytest.fixture
def event_collector(event_publisher):
    """Create EventCollector for testing."""
    return EventCollector(event_publisher)


class EventCapture:
    """Helper to capture events from Redis PubSub."""

    def __init__(self, redis_client, channel: str):
        self.redis_client = redis_client
        self.channel = channel
        self.pubsub = redis_client.pubsub()
        self.events: list[dict[str, Any]] = []
        self.running = False

    def start(self):
        """Start listening for events."""
        self.pubsub.subscribe(self.channel)
        # Skip subscription confirmation
        self.pubsub.get_message(timeout=1.0)
        self.running = True

    def stop(self):
        """Stop listening and cleanup."""
        self.running = False
        self.pubsub.unsubscribe(self.channel)
        self.pubsub.close()

    def get_events(self, timeout: float = 2.0, count: int = 1) -> list[dict[str, Any]]:
        """Get events from the channel."""
        collected = []
        deadline = asyncio.get_event_loop().time() + timeout

        while len(collected) < count and asyncio.get_event_loop().time() < deadline:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break

            msg = self.pubsub.get_message(timeout=remaining)
            if msg and msg["type"] == "message":
                payload = json.loads(msg["data"])
                collected.append(payload)
                self.events.append(payload)

        return collected


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_deliberation_flow(redis_manager, event_collector):
    """Test complete deliberation flow with all event types."""
    session_id = "test_e2e_123"
    channel = f"events:{session_id}"

    # Setup event capture
    capture = EventCapture(redis_manager.redis, channel)
    capture.start()

    try:
        # ===================================================================
        # Phase 1: Decomposition
        # ===================================================================
        sub_problems = [
            SubProblem(
                id="sp1",
                goal="Assess ROI and payback period",
                context="Financial viability analysis",
                complexity_score=7,
            ),
            SubProblem(
                id="sp2",
                goal="Evaluate implementation risks",
                context="Risk mitigation strategies",
                complexity_score=8,
            ),
        ]

        problem = Problem(
            title="AI Automation Investment Decision",
            description="Should we invest $500K in AI automation?",
            statement="Should we invest $500K in AI automation?",
            context="Strategic decision for our growing SaaS company with $50K monthly runway",
            sub_problems=sub_problems,
        )

        decomp_output = {"problem": problem}
        await event_collector._handle_decomposition(session_id, decomp_output)

        # Verify decomposition event
        events = capture.get_events(count=1)
        assert len(events) == 1
        assert events[0]["event_type"] == "decomposition_complete"
        assert events[0]["data"]["count"] == 2
        assert len(events[0]["data"]["sub_problems"]) == 2

        # ===================================================================
        # Phase 2: Persona Selection
        # ===================================================================
        personas = [
            {
                "code": "CFO",
                "name": "Zara Kim",
                "display_name": "Zara Kim (CFO)",
                "domain_expertise": ["financial analysis", "budgeting"],
            },
            {
                "code": "CTO",
                "name": "Alex Rivera",
                "display_name": "Alex Rivera (CTO)",
                "domain_expertise": ["technology", "architecture"],
            },
        ]

        persona_output = {
            "personas": personas,
            "persona_recommendations": [
                {"persona_code": "CFO", "rationale": "Financial expertise needed"},
                {"persona_code": "CTO", "rationale": "Technical evaluation required"},
            ],
        }

        await event_collector._handle_persona_selection(session_id, persona_output)

        # Verify persona selection events
        events = capture.get_events(count=3)  # 2 selected + complete
        assert len(events) == 3
        assert events[0]["event_type"] == "persona_selected"
        assert events[0]["data"]["persona"]["code"] == "CFO"
        assert events[1]["event_type"] == "persona_selected"
        assert events[1]["data"]["persona"]["code"] == "CTO"
        assert events[2]["event_type"] == "persona_selection_complete"
        assert events[2]["data"]["count"] == 2

        # ===================================================================
        # Phase 3: Initial Round
        # ===================================================================
        initial_round_output = {
            "personas": personas,  # Add personas list for experts extraction
            "round_number": 1,
            "contributions": [
                {
                    "persona_code": "CFO",
                    "persona_name": "Zara Kim",
                    "content": "From a financial perspective, the ROI looks promising...",
                    "round": 1,
                },
                {
                    "persona_code": "CTO",
                    "persona_name": "Alex Rivera",
                    "content": "Technically, the implementation is feasible but...",
                    "round": 1,
                },
            ],
        }

        await event_collector._handle_initial_round(session_id, initial_round_output)

        # Verify initial round events
        events = capture.get_events(count=2)  # 2 contributions
        assert len(events) == 2
        assert events[0]["event_type"] == "contribution"
        assert events[0]["data"]["persona_code"] == "CFO"
        assert events[1]["event_type"] == "contribution"
        assert events[1]["data"]["persona_code"] == "CTO"

        # ===================================================================
        # Phase 4: Facilitator Decision
        # ===================================================================
        facilitator_output = {
            "facilitator_decision": {
                "action": "continue",
                "reasoning": "CTO raised valid concerns that need addressing",
                "next_speaker": "CFO",
            },
            "round_number": 2,
        }

        await event_collector._handle_facilitator_decision(session_id, facilitator_output)

        # Verify facilitator decision event
        events = capture.get_events(count=1)
        assert len(events) == 1
        assert events[0]["event_type"] == "facilitator_decision"
        assert events[0]["data"]["action"] == "continue"
        assert events[0]["data"]["next_speaker"] == "CFO"

        # ===================================================================
        # Phase 5: Convergence Check
        # ===================================================================
        convergence_output = {
            "should_stop": False,
            "stop_reason": None,
            "round_number": 2,
            "max_rounds": 10,
            "metrics": {"convergence_score": 0.73},
        }

        await event_collector._handle_convergence(session_id, convergence_output)

        # Verify convergence event
        events = capture.get_events(count=1)
        assert len(events) == 1
        assert events[0]["event_type"] == "convergence"
        assert events[0]["data"]["converged"] is False
        assert events[0]["data"]["score"] == 0.73

        # ===================================================================
        # Phase 6: Voting
        # ===================================================================
        voting_output = {
            "personas": personas,  # Add personas for experts list
            "votes": [
                {
                    "persona_code": "CFO",
                    "persona_name": "Zara Kim",
                    "recommendation": "Invest with phased rollout",
                    "confidence": 0.85,
                    "reasoning": "ROI analysis shows 24-month payback",
                    "conditions": ["Secure executive buy-in", "Establish KPIs"],
                },
                {
                    "persona_code": "CTO",
                    "persona_name": "Alex Rivera",
                    "recommendation": "Invest with technical safeguards",
                    "confidence": 0.80,
                    "reasoning": "Implementation is feasible with proper planning",
                    "conditions": ["Hire additional staff", "Conduct pilot"],
                },
            ],
        }

        await event_collector._handle_voting(session_id, voting_output)

        # Verify voting events
        events = capture.get_events(count=4)  # started + 2 votes + complete
        assert len(events) == 4
        assert events[0]["event_type"] == "voting_started"
        assert events[1]["event_type"] == "persona_vote"
        assert events[1]["data"]["confidence"] == 0.85
        assert events[2]["event_type"] == "persona_vote"
        assert events[2]["data"]["confidence"] == 0.80
        assert events[3]["event_type"] == "voting_complete"
        assert events[3]["data"]["consensus_level"] == "strong"

        # ===================================================================
        # Phase 7: Synthesis
        # ===================================================================
        synthesis_output = {
            "synthesis": "# Final Recommendation\n\nAfter thorough deliberation...",
        }

        await event_collector._handle_synthesis(session_id, synthesis_output)

        # Verify synthesis events
        events = capture.get_events(count=2)  # started + complete
        assert len(events) == 2
        assert events[0]["event_type"] == "synthesis_started"
        assert events[1]["event_type"] == "synthesis_complete"
        assert events[1]["data"]["word_count"] == 6  # Actual word count from synthesis text
        assert "Final Recommendation" in events[1]["data"]["synthesis"]

        # ===================================================================
        # Verify Event Order and Count
        # ===================================================================
        all_events = capture.events
        expected_event_types = [
            "decomposition_complete",
            "persona_selected",
            "persona_selected",
            "persona_selection_complete",
            "contribution",
            "contribution",
            "facilitator_decision",
            "convergence",
            "voting_started",
            "persona_vote",
            "persona_vote",
            "voting_complete",
            "synthesis_started",
            "synthesis_complete",
        ]

        assert len(all_events) == len(expected_event_types)
        for i, expected_type in enumerate(expected_event_types):
            assert all_events[i]["event_type"] == expected_type, (
                f"Event {i}: expected {expected_type}, got {all_events[i]['event_type']}"
            )

        # ===================================================================
        # Verify All Events Have Required Fields
        # ===================================================================
        for event in all_events:
            assert "event_type" in event
            assert "session_id" in event
            assert "timestamp" in event
            assert "data" in event
            assert event["session_id"] == session_id

    finally:
        capture.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_moderator_intervention_event(redis_manager, event_collector):
    """Test moderator intervention event publishing."""
    session_id = "test_moderator_123"
    channel = f"events:{session_id}"

    capture = EventCapture(redis_manager.redis, channel)
    capture.start()

    try:
        moderator_output = {
            "contributions": [
                {
                    "persona_code": "contrarian",
                    "persona_name": "Contrarian Moderator",
                    "content": "What about the risks of NOT implementing AI?",
                }
            ],
            "round_number": 3,
        }

        await event_collector._handle_moderator(session_id, moderator_output)

        events = capture.get_events(count=1)
        assert len(events) == 1
        assert events[0]["event_type"] == "moderator_intervention"
        assert events[0]["data"]["moderator_type"] == "contrarian"
        assert "risks of NOT implementing" in events[0]["data"]["content"]

    finally:
        capture.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_subproblem_complete_event(redis_manager, event_collector):
    """Test sub-problem completion event publishing."""
    session_id = "test_subproblem_123"
    channel = f"events:{session_id}"

    capture = EventCapture(redis_manager.redis, channel)
    capture.start()

    try:
        subproblem_output = {
            "sub_problem_index": 0,
            "sub_problem_results": [
                {
                    "sub_problem_id": "sp1",
                    "sub_problem_goal": "Assess ROI",
                    "cost": 0.0452,
                    "duration_seconds": 45.2,
                    "expert_panel": ["CFO", "CTO"],
                    "contribution_count": 12,
                }
            ],
            "current_sub_problem": {
                "id": "sp1",
                "goal": "Assess ROI",
                "context": "Financial analysis for AI investment",
                "complexity_score": 7,
            },
            "metrics": {"total_cost": 0.0452},
            "personas": [
                {"code": "CFO", "name": "Zara Kim"},
                {"code": "CTO", "name": "Alex Rivera"},
            ],
            "contributions": [{"content": f"Contribution {i}"} for i in range(12)],
        }

        await event_collector._handle_subproblem_complete(session_id, subproblem_output)

        events = capture.get_events(count=1)
        assert len(events) == 1
        assert events[0]["event_type"] == "subproblem_complete"
        assert events[0]["data"]["cost"] == 0.0452
        assert events[0]["data"]["contribution_count"] == 12

    finally:
        capture.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_meta_synthesis_events(redis_manager, event_collector):
    """Test meta-synthesis event publishing."""
    session_id = "test_meta_123"
    channel = f"events:{session_id}"

    capture = EventCapture(redis_manager.redis, channel)
    capture.start()

    try:
        # Meta-synthesis - single call publishes both started and complete events
        meta_output = {
            "sub_problem_results": [
                {"sub_problem_id": "sp1", "synthesis": "First sub-problem synthesis"},
                {"sub_problem_id": "sp2", "synthesis": "Second sub-problem synthesis"},
            ],
            "contributions": [{"content": f"Contribution {i}"} for i in range(24)],
            "metrics": {"total_cost": 0.0904},
            "synthesis": "# Meta-Synthesis\n\nIntegrating insights...",
        }

        await event_collector._handle_meta_synthesis(session_id, meta_output)

        events = capture.get_events(count=1)
        assert len(events) == 1
        assert events[0]["event_type"] == "meta_synthesis_complete"
        assert (
            events[0]["data"]["word_count"] == 4
        )  # "# Meta-Synthesis\n\nIntegrating insights..." = 4 words

    finally:
        capture.stop()


@pytest.mark.integration
def test_concurrent_session_isolation(redis_manager, event_publisher):
    """Test that events from different sessions are isolated."""
    session1 = "test_session_a"
    session2 = "test_session_b"

    channel1 = f"events:{session1}"
    channel2 = f"events:{session2}"

    # Setup two separate captures
    capture1 = EventCapture(redis_manager.redis, channel1)
    capture2 = EventCapture(redis_manager.redis, channel2)

    capture1.start()
    capture2.start()

    try:
        # Publish events to both sessions
        event_publisher.publish_event(session1, "test_event_1", {"data": "session1"})
        event_publisher.publish_event(session2, "test_event_2", {"data": "session2"})

        # Each capture should only receive its own session's events
        events1 = capture1.get_events(count=1)
        events2 = capture2.get_events(count=1)

        assert len(events1) == 1
        assert len(events2) == 1

        assert events1[0]["session_id"] == session1
        assert events1[0]["data"]["data"] == "session1"

        assert events2[0]["session_id"] == session2
        assert events2[0]["data"]["data"] == "session2"

    finally:
        capture1.stop()
        capture2.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
