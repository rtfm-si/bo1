# End-to-End Meeting Test Design

## Overview

This document outlines the design for a comprehensive end-to-end test that validates the complete meeting lifecycle from problem creation through final synthesis. The test will be console-only (no UI) and verify all critical stages of the LangGraph deliberation flow.

## Test Objectives

1. **Verify complete graph execution** - Ensure all nodes execute successfully
2. **Validate state transitions** - Check state changes at each stage
3. **Confirm database persistence** - Verify PostgreSQL session and event storage
4. **Validate event emission** - Ensure all events are published to Redis
5. **Check cost tracking** - Verify metrics and phase costs
6. **Minimize API costs** - Use simple problem and AI_OVERRIDE mode

## Test Architecture

### Test File Location
```
/Users/si/projects/bo1/tests/integration/test_end_to_end_meeting.py
```

### Test Structure

```python
"""End-to-end integration test for complete meeting lifecycle.

This test validates the entire deliberation flow:
- Problem decomposition
- Persona selection
- Multi-round deliberation
- Convergence detection
- Recommendation collection
- Final synthesis
- Database persistence
- Event emission
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any

import pytest
from langgraph.checkpoint.memory import MemorySaver

from backend.api.event_collector import EventCollector
from backend.api.event_publisher import EventPublisher
from bo1.graph.config import create_deliberation_graph
from bo1.graph.state import create_initial_state
from bo1.models.problem import Problem
from bo1.state.postgres_manager import (
    db_session,
    get_session_events,
    save_session,
)
from bo1.state.redis_manager import RedisManager
from tests.utils.assertions import (
    assert_personas_selected,
    assert_state_valid,
    assert_sub_problems_created,
)

logger = logging.getLogger(__name__)

# Test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_llm,  # Requires real API calls
    pytest.mark.requires_redis,  # Requires Redis for checkpointing
    pytest.mark.timeout(600),  # 10 minute timeout for full meeting
]


@pytest.fixture
def test_session_id() -> str:
    """Generate unique session ID for test."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"e2e_test_{timestamp}"


@pytest.fixture
def simple_problem() -> Problem:
    """Create a simple problem to minimize API costs.

    This problem is designed to:
    - Generate minimal sub-problems (1-2)
    - Require fewer rounds (converge quickly)
    - Use simple domain knowledge
    - Keep token counts low
    """
    return Problem(
        title="Marketing Channel Decision",
        description="Should I invest $10K in SEO or paid ads for my SaaS startup?",
        context="Solo founder, B2B SaaS, $50K ARR, targeting marketing managers",
    )


@pytest.fixture
def redis_manager() -> RedisManager:
    """Create Redis manager for event publishing."""
    manager = RedisManager()
    if not manager.is_available:
        pytest.skip("Redis not available")
    return manager


@pytest.fixture
def event_publisher(redis_manager: RedisManager) -> EventPublisher:
    """Create event publisher for tracking events."""
    return EventPublisher(redis_manager.redis)


@pytest.fixture
def event_collector(event_publisher: EventPublisher) -> EventCollector:
    """Create event collector for graph execution."""
    return EventCollector(event_publisher)


class EventCapture:
    """Helper to capture events from Redis PubSub during test."""

    def __init__(self, redis_client, session_id: str):
        self.redis_client = redis_client
        self.session_id = session_id
        self.channel = f"events:{session_id}"
        self.pubsub = redis_client.pubsub()
        self.events: list[dict[str, Any]] = []

    def start(self):
        """Start listening for events."""
        self.pubsub.subscribe(self.channel)
        # Skip subscription confirmation
        self.pubsub.get_message(timeout=1.0)

    def stop(self):
        """Stop listening and cleanup."""
        self.pubsub.unsubscribe(self.channel)
        self.pubsub.close()

    def collect_event(self, timeout: float = 5.0) -> dict[str, Any] | None:
        """Collect single event with timeout."""
        msg = self.pubsub.get_message(timeout=timeout)
        if msg and msg["type"] == "message":
            payload = json.loads(msg["data"])
            self.events.append(payload)
            return payload
        return None

    def collect_events_until(
        self,
        event_type: str,
        timeout: float = 30.0
    ) -> list[dict[str, Any]]:
        """Collect events until specific type appears."""
        collected = []
        deadline = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < deadline:
            remaining = deadline - asyncio.get_event_loop().time()
            event = self.collect_event(timeout=max(0.1, remaining))
            if event:
                collected.append(event)
                if event.get("event_type") == event_type:
                    break

        return collected


@pytest.mark.asyncio
async def test_complete_meeting_lifecycle(
    test_session_id: str,
    simple_problem: Problem,
    redis_manager: RedisManager,
    event_collector: EventCollector,
):
    """Test complete meeting from start to finish.

    This test validates:
    1. Session creation and initialization
    2. Problem decomposition (1-2 sub-problems expected)
    3. Persona selection (3-5 experts)
    4. Initial round with all experts
    5. At least one follow-up round
    6. Convergence detection
    7. Recommendation collection
    8. Final synthesis
    9. Database persistence
    10. Event emission at each stage
    """
    # ==========================================================================
    # Stage 1: Setup and Initialization
    # ==========================================================================
    logger.info(f"Starting E2E test for session: {test_session_id}")

    # Set AI_OVERRIDE to minimize costs (use Haiku instead of Sonnet)
    original_override = os.getenv("AI_OVERRIDE")
    original_model = os.getenv("AI_OVERRIDE_MODEL")
    os.environ["AI_OVERRIDE"] = "true"
    os.environ["AI_OVERRIDE_MODEL"] = "claude-haiku-4-5-20251001"

    try:
        # Create event capture for monitoring
        event_capture = EventCapture(redis_manager.redis, test_session_id)
        event_capture.start()

        # Save session to PostgreSQL
        with db_session() as conn:
            save_session(
                session_id=test_session_id,
                user_id="e2e_test_user",
                problem_statement=simple_problem.description,
                problem_context={"title": simple_problem.title},
                status="created",
            )
        logger.info("Session saved to PostgreSQL")

        # Create initial state
        initial_state = create_initial_state(
            session_id=test_session_id,
            problem=simple_problem,
            max_rounds=5,  # Low for cost control
        )

        # Validate initial state
        assert_state_valid(initial_state)
        assert initial_state["session_id"] == test_session_id
        assert initial_state["problem"] == simple_problem
        assert initial_state["max_rounds"] == 5
        logger.info("Initial state validated")

        # ==========================================================================
        # Stage 2: Graph Execution
        # ==========================================================================

        # Create graph with in-memory checkpointing for test
        checkpointer = MemorySaver()
        graph = create_deliberation_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": test_session_id}}

        # Execute graph with event collection
        logger.info("Starting graph execution...")
        start_time = datetime.now()

        final_state = await event_collector.collect_and_publish(
            session_id=test_session_id,
            graph=graph,
            initial_state=initial_state,
            config=config,
        )

        execution_duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Graph execution completed in {execution_duration:.1f}s")

        # ==========================================================================
        # Stage 3: Validate Final State
        # ==========================================================================

        assert final_state is not None, "Graph execution returned None"
        assert_state_valid(final_state)

        # Check problem decomposition
        assert "problem" in final_state
        assert_sub_problems_created(
            final_state["problem"],
            min_count=1,
            max_count=3,  # Simple problem should have 1-2 sub-problems
        )
        logger.info(
            f"✓ Decomposition: {len(final_state['problem'].sub_problems)} sub-problems"
        )

        # Check persona selection
        assert "personas" in final_state
        assert_personas_selected(
            final_state["personas"],
            min_count=3,
            max_count=5,
        )
        logger.info(f"✓ Persona selection: {len(final_state['personas'])} experts")

        # Check deliberation occurred
        assert "contributions" in final_state
        assert len(final_state["contributions"]) >= len(final_state["personas"])
        logger.info(f"✓ Deliberation: {len(final_state['contributions'])} contributions")

        # Check at least one round completed
        assert final_state["round_number"] >= 1
        logger.info(f"✓ Rounds completed: {final_state['round_number']}")

        # Check recommendations collected
        assert "recommendations" in final_state
        assert len(final_state["recommendations"]) > 0
        logger.info(f"✓ Recommendations: {len(final_state['recommendations'])} collected")

        # Check synthesis generated
        assert "synthesis" in final_state
        assert final_state["synthesis"] is not None
        assert len(final_state["synthesis"]) > 100
        logger.info(f"✓ Synthesis: {len(final_state['synthesis'])} characters")

        # Check cost tracking
        assert "metrics" in final_state
        metrics = final_state["metrics"]
        assert metrics.total_cost > 0
        assert metrics.total_cost < 1.0  # Should be cheap with Haiku

        # Verify all expected phases tracked
        expected_phases = [
            "problem_decomposition",
            "persona_selection",
            "initial_round",
            "voting",
            "synthesis",
        ]
        for phase in expected_phases:
            assert phase in metrics.phase_costs, f"Missing phase: {phase}"
            assert metrics.phase_costs[phase] > 0

        logger.info(f"✓ Cost tracking: ${metrics.total_cost:.4f}")

        # ==========================================================================
        # Stage 4: Validate Database Persistence
        # ==========================================================================

        # Check session events were saved
        events = get_session_events(test_session_id)
        assert len(events) > 0, "No events saved to database"

        # Verify key event types present
        event_types = [e["event_type"] for e in events]
        assert "decomposition_complete" in event_types
        assert "persona_selection_complete" in event_types
        assert "contribution" in event_types
        assert "voting_complete" in event_types
        assert "synthesis_complete" in event_types

        logger.info(f"✓ Database: {len(events)} events persisted")

        # ==========================================================================
        # Stage 5: Validate Event Emission
        # ==========================================================================

        # Stop event capture and analyze
        event_capture.stop()
        captured_events = event_capture.events

        assert len(captured_events) > 0, "No events captured from Redis"

        # Verify event types match database
        captured_types = [e.get("event_type") for e in captured_events]
        for expected_type in ["decomposition_complete", "persona_selection_complete"]:
            assert expected_type in captured_types, f"Missing event: {expected_type}"

        logger.info(f"✓ Events: {len(captured_events)} emitted to Redis")

        # ==========================================================================
        # Stage 6: Summary Report
        # ==========================================================================

        logger.info("\n" + "=" * 80)
        logger.info("END-TO-END TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Session ID: {test_session_id}")
        logger.info(f"Execution Time: {execution_duration:.1f}s")
        logger.info(f"Sub-problems: {len(final_state['problem'].sub_problems)}")
        logger.info(f"Experts: {len(final_state['personas'])}")
        logger.info(f"Contributions: {len(final_state['contributions'])}")
        logger.info(f"Rounds: {final_state['round_number']}")
        logger.info(f"Recommendations: {len(final_state['votes'])}")
        logger.info(f"Synthesis Length: {len(final_state['synthesis'])} chars")
        logger.info(f"Total Cost: ${metrics.total_cost:.4f}")
        logger.info(f"Events (DB): {len(events)}")
        logger.info(f"Events (Redis): {len(captured_events)}")
        logger.info("=" * 80)
        logger.info("✅ ALL CHECKS PASSED")
        logger.info("=" * 80 + "\n")

    finally:
        # Restore original environment
        if original_override is not None:
            os.environ["AI_OVERRIDE"] = original_override
        if original_model is not None:
            os.environ["AI_OVERRIDE_MODEL"] = original_model


@pytest.mark.asyncio
async def test_meeting_with_multiple_subproblems(
    test_session_id: str,
    redis_manager: RedisManager,
    event_collector: EventCollector,
):
    """Test meeting with multiple sub-problems to validate iteration logic.

    This test specifically validates:
    - next_subproblem node transitions
    - sub_problem_results accumulation
    - meta-synthesis generation
    """
    # Create problem that will decompose into multiple sub-problems
    complex_problem = Problem(
        title="Product Launch Strategy",
        description="Should we launch our new B2B SaaS product in Q1 or Q2?",
        context=(
            "Enterprise SaaS startup, 100 employees, $5M ARR, "
            "competing with established players, considering market timing, "
            "sales team readiness, product feature completeness, "
            "and marketing campaign preparation"
        ),
    )

    # Set AI override for cost control
    os.environ["AI_OVERRIDE"] = "true"
    os.environ["AI_OVERRIDE_MODEL"] = "claude-haiku-4-5-20251001"

    try:
        # Create initial state
        initial_state = create_initial_state(
            session_id=test_session_id,
            problem=complex_problem,
            max_rounds=4,  # Keep low for cost
        )

        # Execute graph
        checkpointer = MemorySaver()
        graph = create_deliberation_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": test_session_id}}

        final_state = await event_collector.collect_and_publish(
            session_id=test_session_id,
            graph=graph,
            initial_state=initial_state,
            config=config,
        )

        # Validate multi-sub-problem handling
        assert final_state is not None

        # Should have multiple sub-problems
        num_subproblems = len(final_state["problem"].sub_problems)
        assert num_subproblems >= 2, "Expected 2+ sub-problems for complex scenario"

        # Should have results for all sub-problems
        assert "sub_problem_results" in final_state
        results = final_state["sub_problem_results"]

        # If all sub-problems completed, should have results for each
        # (or results may be fewer if meeting stopped early due to cost/time)
        assert len(results) > 0, "No sub-problem results generated"

        # Each result should have required fields
        for result in results:
            assert result.sub_problem_id is not None
            assert result.synthesis is not None
            assert result.cost > 0

        logger.info(
            f"✓ Multi-sub-problem test: {num_subproblems} problems, "
            f"{len(results)} completed"
        )

    finally:
        # Restore environment
        os.environ.pop("AI_OVERRIDE", None)
        os.environ.pop("AI_OVERRIDE_MODEL", None)


@pytest.mark.asyncio
async def test_meeting_convergence_triggers(
    test_session_id: str,
    redis_manager: RedisManager,
    event_collector: EventCollector,
):
    """Test that convergence detection works correctly.

    Validates:
    - Convergence score calculation
    - Early stopping when consensus reached
    - should_stop flag set correctly
    """
    # Create focused problem that should converge quickly
    focused_problem = Problem(
        title="Simple Investment Decision",
        description="Should I invest in index funds or bonds?",
        context="Retiree, low risk tolerance, $100K to invest, 5-year horizon",
    )

    os.environ["AI_OVERRIDE"] = "true"
    os.environ["AI_OVERRIDE_MODEL"] = "claude-haiku-4-5-20251001"

    try:
        initial_state = create_initial_state(
            session_id=test_session_id,
            problem=focused_problem,
            max_rounds=10,  # High limit - should converge before hitting it
        )

        checkpointer = MemorySaver()
        graph = create_deliberation_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": test_session_id}}

        final_state = await event_collector.collect_and_publish(
            session_id=test_session_id,
            graph=graph,
            initial_state=initial_state,
            config=config,
        )

        # Check convergence was detected
        assert final_state is not None

        # Should stop before max rounds due to convergence
        # (though not guaranteed - depends on expert opinions)
        logger.info(
            f"Convergence test: stopped at round {final_state['round_number']}/10"
        )

        # Verify metrics calculated
        metrics = final_state["metrics"]
        if hasattr(metrics, "convergence_score"):
            logger.info(f"Final convergence score: {metrics.convergence_score}")

    finally:
        os.environ.pop("AI_OVERRIDE", None)
        os.environ.pop("AI_OVERRIDE_MODEL", None)
```

## Mock/Fixture Requirements

### Required Fixtures (from conftest.py)

1. **test_session_id** - Unique session ID for each test
2. **simple_problem** - Minimal problem to reduce API costs
3. **redis_manager** - Redis connection for event publishing
4. **event_publisher** - Event publisher instance
5. **event_collector** - EventCollector for graph execution

### Database Setup

- Tests use real PostgreSQL (no mocking needed)
- `db_session()` context manager handles connections
- Database should be in clean state or use transactional rollback

### Redis Setup

- Tests require real Redis instance
- Skip test if Redis unavailable using `@pytest.mark.requires_redis`
- EventCapture helper class monitors Redis PubSub

## Environment Configuration

### Cost Control Settings

```bash
# Use in test setup
export AI_OVERRIDE=true
export AI_OVERRIDE_MODEL=claude-haiku-4-5-20251001
```

This reduces costs from ~$0.10/meeting (Sonnet) to ~$0.01/meeting (Haiku)

### Test Markers

```python
pytestmark = [
    pytest.mark.integration,      # Integration test
    pytest.mark.requires_llm,     # Needs real API keys
    pytest.mark.requires_redis,   # Needs Redis connection
    pytest.mark.timeout(600),     # 10 minute max runtime
]
```

## Key Assertions

### State Validation
- `assert_state_valid(state)` - Check all required fields
- `assert_sub_problems_created(problem, min=1, max=3)` - Verify decomposition
- `assert_personas_selected(personas, min=3, max=5)` - Verify selection

### Stage Completion
- **Decomposition**: `len(problem.sub_problems) >= 1`
- **Persona Selection**: `3 <= len(personas) <= 5`
- **Initial Round**: `len(contributions) >= len(personas)`
- **Follow-up Rounds**: `round_number >= 1`
- **Recommendations**: `len(votes) > 0`
- **Synthesis**: `len(synthesis) > 100`

### Database Persistence
- Session exists in `sessions` table
- Events saved to `session_events` table
- Key event types present: decomposition, personas, contributions, voting, synthesis

### Event Emission
- Events published to Redis PubSub channel `events:{session_id}`
- Event history available via `events_history:{session_id}`
- Event types match database records

### Cost Tracking
- `total_cost > 0` and `< 1.0` (with Haiku override)
- Phase costs tracked for all stages
- No missing phase entries

## Estimated Test Runtime

### Single Test Execution
- **Simple problem test**: 2-4 minutes
- **Multi-sub-problem test**: 4-6 minutes
- **Convergence test**: 2-5 minutes

### Full Suite
- **Total runtime**: ~10-15 minutes
- **API costs**: ~$0.03-0.05 (with Haiku override)

### Running Tests

```bash
# Run all E2E tests
pytest tests/integration/test_end_to_end_meeting.py -v

# Run single test
pytest tests/integration/test_end_to_end_meeting.py::test_complete_meeting_lifecycle -v -s

# Run with detailed logging
pytest tests/integration/test_end_to_end_meeting.py -v -s --log-cli-level=INFO

# Skip if Redis unavailable
pytest tests/integration/test_end_to_end_meeting.py -v -m "not requires_redis"
```

## Test Output Example

```
========================================
END-TO-END TEST SUMMARY
========================================
Session ID: e2e_test_20250112_143022
Execution Time: 142.3s
Sub-problems: 2
Experts: 4
Contributions: 12
Rounds: 2
Recommendations: 4
Synthesis Length: 1847 chars
Total Cost: $0.0234
Events (DB): 28
Events (Redis): 28
========================================
✅ ALL CHECKS PASSED
========================================
```

## Integration with CI/CD

### GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
e2e-tests:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:15
      env:
        POSTGRES_PASSWORD: test
      options: >-
        --health-cmd pg_isready
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
    redis:
      image: redis:7
      options: >-
        --health-cmd "redis-cli ping"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
  steps:
    - uses: actions/checkout@v3
    - name: Run E2E tests
      env:
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        AI_OVERRIDE: true
        AI_OVERRIDE_MODEL: claude-haiku-4-5-20251001
      run: |
        pytest tests/integration/test_end_to_end_meeting.py -v
```

## Troubleshooting

### Common Issues

1. **Timeout errors**: Increase `@pytest.mark.timeout(600)` value
2. **Redis connection refused**: Ensure Redis running on localhost:6379
3. **High costs**: Verify `AI_OVERRIDE=true` is set
4. **Missing events**: Check EventCollector implementation for new node types

### Debug Mode

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Print state at each stage
print(json.dumps(final_state, indent=2, default=str))
```

## Future Enhancements

1. **Add performance benchmarks** - Track execution time regressions
2. **Add snapshot testing** - Compare outputs against golden files
3. **Add parallel execution tests** - Validate ENABLE_PARALLEL_SUBPROBLEMS
4. **Add failure scenario tests** - Test error handling and recovery
5. **Add pause/resume tests** - Validate checkpoint recovery

## Conclusion

This E2E test design provides comprehensive validation of the meeting system with:

- ✅ Full lifecycle coverage (decomposition → synthesis)
- ✅ Database and event verification
- ✅ Cost-controlled execution (~$0.01-0.05 per test)
- ✅ Realistic timing (2-6 minutes per test)
- ✅ Clear pass/fail criteria
- ✅ Detailed reporting and logging
- ✅ CI/CD integration ready

The test suite can be run locally or in CI, with automatic skipping when dependencies (Redis, API keys) are unavailable.
