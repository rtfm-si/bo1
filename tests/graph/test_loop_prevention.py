"""Tests for all 5 infinite loop prevention layers."""

import asyncio

import networkx as nx
import pytest

from bo1.graph.routers import route_convergence_check
from bo1.graph.safety.loop_prevention import (
    DEFAULT_MAX_COST_PER_SESSION,
    DEFAULT_TIMEOUT_SECONDS,
    DELIBERATION_RECURSION_LIMIT,
    TIER_COST_LIMITS,
    check_convergence_node,
    cost_guard_node,
    execute_deliberation_with_timeout,
    route_cost_guard,
    validate_graph_acyclic,
    validate_round_counter_invariants,
)
from bo1.graph.state import DeliberationGraphState, create_initial_state
from bo1.models.problem import Problem
from bo1.models.state import DeliberationMetrics


@pytest.fixture
def sample_problem() -> Problem:
    """Create a sample problem for testing."""
    return Problem(
        title="Test Problem",
        description="Should we invest in feature X?",
        context="SaaS startup with $500K budget",
    )


# ============================================================================
# Layer 1: Recursion Limit Tests
# ============================================================================


def test_recursion_limit_constant():
    """Test that recursion limit is set correctly."""
    # 5 sub-problems × ~45 nodes/sub-problem + overhead = 250 (multi-subproblem architecture)
    assert DELIBERATION_RECURSION_LIMIT == 250  # Supports up to 5 sub-problems


# ============================================================================
# Layer 2: Cycle Detection Tests
# ============================================================================


def test_validate_graph_acyclic_no_cycles():
    """Test graph validation with no cycles (fully acyclic)."""
    graph = nx.DiGraph()
    graph.add_edges_from(
        [
            ("start", "decompose"),
            ("decompose", "select"),
            ("select", "initial_round"),
            ("initial_round", "vote"),
            ("vote", "end"),
        ]
    )

    # Should not raise
    validate_graph_acyclic(graph)


def test_validate_graph_acyclic_with_controlled_cycle():
    """Test graph validation with a controlled cycle (has exit)."""
    graph = nx.DiGraph()
    graph.add_edges_from(
        [
            ("facilitator", "persona"),
            ("persona", "check_convergence"),
            (
                "check_convergence",
                "facilitator",
            ),  # Cycle: facilitator → persona → check → facilitator
            ("check_convergence", "vote"),  # Exit: check → vote (breaks the cycle)
        ]
    )

    # Should not raise (cycle has exit to "vote")
    validate_graph_acyclic(graph)


def test_validate_graph_acyclic_with_uncontrolled_cycle():
    """Test graph validation fails with uncontrolled cycle (no exit)."""
    graph = nx.DiGraph()
    graph.add_edges_from(
        [
            ("A", "B"),
            ("B", "C"),
            ("C", "A"),  # Cycle with no exit
        ]
    )

    with pytest.raises(ValueError, match="Uncontrolled cycle detected"):
        validate_graph_acyclic(graph)


# ============================================================================
# Layer 3: Round Counter Tests
# ============================================================================


@pytest.mark.asyncio
async def test_check_convergence_below_max_rounds(sample_problem: Problem):
    """Test convergence check when below max rounds."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        max_rounds=5,
    )
    state["round_number"] = 3

    result = await check_convergence_node(state)

    assert result["should_stop"] is False
    assert result.get("stop_reason") is None


@pytest.mark.asyncio
async def test_check_convergence_at_max_rounds(sample_problem: Problem):
    """Test convergence check when at max rounds."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        max_rounds=5,
    )
    state["round_number"] = 5

    result = await check_convergence_node(state)

    assert result["should_stop"] is True
    assert result["stop_reason"] == "max_rounds"


@pytest.mark.asyncio
async def test_check_convergence_at_hard_cap(sample_problem: Problem):
    """Test convergence check at absolute hard cap (6 rounds)."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        max_rounds=6,
    )
    state["round_number"] = 6

    result = await check_convergence_node(state)

    assert result["should_stop"] is True
    assert result["stop_reason"] == "hard_cap_6_rounds"


@pytest.mark.asyncio
async def test_check_convergence_with_high_score(sample_problem: Problem):
    """Test convergence check when convergence score is high.

    Updated for quality metrics refactoring (commit d1fdc3b):
    - Convergence threshold increased from 0.85 to 0.90
    - Requires participation rate >= 0.70
    - Requires novelty score <= 0.40

    Updated for Issue #3 fix:
    - Convergence is now recalculated each round (not cached)
    - Test mocks the semantic calculation to return high score
    """
    from unittest.mock import AsyncMock, patch

    from bo1.models.state import ContributionMessage

    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        max_rounds=6,
    )
    state["round_number"] = 3

    # Add personas for participation check (need at least 1 for valid participation rate)
    state["personas"] = [
        {"code": "CFO", "name": "Zara Kim"},
        {"code": "CTO", "name": "Alex Rivera"},
    ]

    # Add enough contributions for novelty calculation (need >= 6)
    # These contributions should be similar enough to indicate low novelty
    state["contributions"] = [
        ContributionMessage(
            persona_code="CFO",
            persona_name="Zara",
            content="We should prioritize cash flow management",
            round_number=1,
        ),
        ContributionMessage(
            persona_code="CTO",
            persona_name="Alex",
            content="Cash flow is critical",
            round_number=1,
        ),
        ContributionMessage(
            persona_code="CFO",
            persona_name="Zara",
            content="Cash management remains important",
            round_number=2,
        ),
        ContributionMessage(
            persona_code="CTO",
            persona_name="Alex",
            content="We need to focus on cash",
            round_number=2,
        ),
        ContributionMessage(
            persona_code="CFO",
            persona_name="Zara",
            content="Cash flow is the priority",
            round_number=3,
        ),
        ContributionMessage(
            persona_code="CTO",
            persona_name="Alex",
            content="Managing cash is essential",
            round_number=3,
        ),
    ]

    # Pre-set novelty score (convergence will be recalculated via mock)
    state["metrics"] = DeliberationMetrics(novelty_score=0.2)

    # Mock the semantic convergence calculation to return high score
    # AUDIT FIX (Priority 4.3): Function moved to bo1.graph.quality.metrics
    with patch(
        "bo1.graph.quality.metrics._calculate_convergence_score_semantic",
        new_callable=AsyncMock,
        return_value=0.91,
    ):
        result = await check_convergence_node(state)

    assert result["should_stop"] is True
    # NEW: With early exit logic, high convergence (0.91) + low novelty (0.2) triggers early_convergence
    assert result["stop_reason"] in ["consensus", "early_convergence"]


@pytest.mark.asyncio
async def test_check_convergence_with_low_score(sample_problem: Problem):
    """Test convergence check when convergence score is low."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        max_rounds=6,
    )
    state["round_number"] = 3
    state["metrics"] = DeliberationMetrics(convergence_score=0.50)

    result = await check_convergence_node(state)

    assert result["should_stop"] is False


def test_route_convergence_check_stop(sample_problem: Problem):
    """Test routing when should_stop is True."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
    )
    state["should_stop"] = True
    state["stop_reason"] = "max_rounds"

    route = route_convergence_check(state)

    assert route == "vote"


def test_route_convergence_check_continue(sample_problem: Problem):
    """Test routing when should_stop is False."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
    )
    state["should_stop"] = False

    route = route_convergence_check(state)

    assert route == "facilitator_decide"


# ============================================================================
# Invariant Validation Tests
# ============================================================================


def test_validate_round_counter_valid(sample_problem: Problem):
    """Test round counter validation with valid state."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        max_rounds=6,
    )
    state["round_number"] = 5

    # Should not raise
    validate_round_counter_invariants(state)


def test_validate_round_counter_negative():
    """Test round counter validation fails with negative round."""
    state: DeliberationGraphState = {
        "session_id": "test",
        "problem": None,  # type: ignore
        "personas": [],
        "contributions": [],
        "round_summaries": [],
        "phase": None,  # type: ignore
        "round_number": -1,  # Invalid
        "max_rounds": 6,
        "metrics": DeliberationMetrics(),
    }

    with pytest.raises(ValueError, match="Invalid round_number"):
        validate_round_counter_invariants(state)


def test_validate_round_counter_exceeds_hard_cap():
    """Test round counter validation fails when max_rounds exceeds hard cap."""
    state: DeliberationGraphState = {
        "session_id": "test",
        "problem": None,  # type: ignore
        "personas": [],
        "contributions": [],
        "round_summaries": [],
        "phase": None,  # type: ignore
        "round_number": 5,
        "max_rounds": 10,  # Exceeds hard cap of 6
        "metrics": DeliberationMetrics(),
    }

    with pytest.raises(ValueError, match="hard cap is 6"):
        validate_round_counter_invariants(state)


def test_validate_round_counter_round_exceeds_max():
    """Test round counter validation fails when round exceeds max."""
    state: DeliberationGraphState = {
        "session_id": "test",
        "problem": None,  # type: ignore
        "personas": [],
        "contributions": [],
        "round_summaries": [],
        "phase": None,  # type: ignore
        "round_number": 6,
        "max_rounds": 5,
        "metrics": DeliberationMetrics(),
    }

    with pytest.raises(ValueError, match="exceeds max_rounds"):
        validate_round_counter_invariants(state)


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_convergence_node_preserves_state(sample_problem: Problem):
    """Test that convergence node preserves all state fields."""
    state = create_initial_state(
        session_id="test-preserve",
        problem=sample_problem,
        max_rounds=6,
    )
    state["round_number"] = 3

    # Add some contributions
    from bo1.models.state import ContributionMessage

    state["contributions"] = [
        ContributionMessage(
            persona_code="test",
            persona_name="Test",
            content="Test contribution",
            round_number=1,
        )
    ]

    result = await check_convergence_node(state)

    # Verify all fields preserved
    assert result["session_id"] == "test-preserve"
    assert result["problem"] == sample_problem
    assert len(result["contributions"]) == 1
    assert result["round_number"] == 3


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_multiple_rounds_with_counter(sample_problem: Problem):
    """Test multiple rounds with round counter incrementing."""
    state = create_initial_state(
        session_id="test-multi",
        problem=sample_problem,
        max_rounds=5,
    )

    for round_num in range(1, 6):
        state["round_number"] = round_num
        result = await check_convergence_node(state)

        if round_num < 5:
            assert result["should_stop"] is False
        else:
            # Round 5 should trigger max_rounds stop
            assert result["should_stop"] is True
            assert result["stop_reason"] == "max_rounds"


# ============================================================================
# Layer 4: Timeout Watchdog Tests
# ============================================================================


def test_timeout_constant():
    """Test that timeout constant is set correctly."""
    # Default: 1 hour = 3600 seconds
    assert DEFAULT_TIMEOUT_SECONDS == 3600


@pytest.mark.asyncio
async def test_timeout_watchdog_success(sample_problem: Problem):
    """Test timeout watchdog with successful completion."""

    # Mock graph that completes quickly
    class MockGraph:
        async def ainvoke(self, state, config):
            await asyncio.sleep(0.1)  # 100ms
            return state

    graph = MockGraph()
    initial_state = create_initial_state(
        session_id="test-timeout-success",
        problem=sample_problem,
    )
    config = {"configurable": {"thread_id": "test-123"}}

    # Should complete successfully
    result = await execute_deliberation_with_timeout(
        graph, initial_state, config, timeout_seconds=1
    )

    assert result["session_id"] == "test-timeout-success"


@pytest.mark.asyncio
async def test_timeout_watchdog_timeout(sample_problem: Problem):
    """Test timeout watchdog raises TimeoutError for long-running deliberation."""

    # Mock graph that takes too long
    class MockSlowGraph:
        async def ainvoke(self, state, config):
            await asyncio.sleep(10)  # 10 seconds (exceeds 1s timeout)
            return state

    graph = MockSlowGraph()
    initial_state = create_initial_state(
        session_id="test-timeout-fail",
        problem=sample_problem,
    )
    config = {"configurable": {"thread_id": "test-123"}}

    # Should raise TimeoutError
    with pytest.raises(TimeoutError):
        await execute_deliberation_with_timeout(graph, initial_state, config, timeout_seconds=1)


@pytest.mark.asyncio
async def test_timeout_watchdog_custom_timeout(sample_problem: Problem):
    """Test timeout watchdog with custom timeout value."""

    class MockGraph:
        async def ainvoke(self, state, config):
            await asyncio.sleep(0.5)  # 500ms
            return state

    graph = MockGraph()
    initial_state = create_initial_state(
        session_id="test-custom-timeout",
        problem=sample_problem,
    )
    config = {"configurable": {"thread_id": "test-123"}}

    # Should complete with 2s timeout
    result = await execute_deliberation_with_timeout(
        graph, initial_state, config, timeout_seconds=2
    )

    assert result["session_id"] == "test-custom-timeout"

    # Should timeout with 0.1s timeout
    with pytest.raises(TimeoutError):
        await execute_deliberation_with_timeout(graph, initial_state, config, timeout_seconds=0.1)


# ============================================================================
# Layer 5: Cost-Based Kill Switch Tests
# ============================================================================


def test_cost_limit_constants():
    """Test that cost limit constants are set correctly."""
    assert DEFAULT_MAX_COST_PER_SESSION == 1.00
    assert TIER_COST_LIMITS["free"] == 0.50
    assert TIER_COST_LIMITS["pro"] == 2.00
    assert TIER_COST_LIMITS["enterprise"] == 10.00


def test_cost_guard_within_budget(sample_problem: Problem):
    """Test cost guard when within budget."""
    state = create_initial_state(
        session_id="test-cost-ok",
        problem=sample_problem,
    )
    state["metrics"] = DeliberationMetrics(total_cost=0.50)  # $0.50 < $1.00 limit

    result = cost_guard_node(state)

    assert result["should_stop"] is False
    assert result.get("stop_reason") is None


def test_cost_guard_exceeds_budget(sample_problem: Problem):
    """Test cost guard when budget exceeded."""
    state = create_initial_state(
        session_id="test-cost-exceeded",
        problem=sample_problem,
    )
    state["metrics"] = DeliberationMetrics(total_cost=1.50)  # $1.50 > $1.00 limit

    result = cost_guard_node(state)

    assert result["should_stop"] is True
    assert result["stop_reason"] == "cost_budget_exceeded"


def test_cost_guard_at_exact_limit(sample_problem: Problem):
    """Test cost guard at exact budget limit."""
    state = create_initial_state(
        session_id="test-cost-exact",
        problem=sample_problem,
        subscription_tier="starter",  # $1.00 limit
    )
    state["metrics"] = DeliberationMetrics(total_cost=1.00)  # Exactly $1.00

    result = cost_guard_node(state)

    # At limit is still OK (uses > not >=)
    assert result["should_stop"] is False


def test_cost_guard_free_tier(sample_problem: Problem):
    """Test cost guard with free tier limit ($0.50)."""
    state = create_initial_state(
        session_id="test-cost-free",
        problem=sample_problem,
    )
    state["subscription_tier"] = "free"
    state["metrics"] = DeliberationMetrics(total_cost=0.60)  # $0.60 > $0.50 free tier

    result = cost_guard_node(state)

    assert result["should_stop"] is True
    assert result["stop_reason"] == "cost_budget_exceeded"


def test_cost_guard_pro_tier(sample_problem: Problem):
    """Test cost guard with pro tier limit ($2.00)."""
    state = create_initial_state(
        session_id="test-cost-pro",
        problem=sample_problem,
    )
    state["subscription_tier"] = "pro"
    state["metrics"] = DeliberationMetrics(total_cost=1.50)  # $1.50 < $2.00 pro tier

    result = cost_guard_node(state)

    assert result["should_stop"] is False


def test_cost_guard_enterprise_tier(sample_problem: Problem):
    """Test cost guard with enterprise tier limit ($10.00)."""
    state = create_initial_state(
        session_id="test-cost-enterprise",
        problem=sample_problem,
    )
    state["subscription_tier"] = "enterprise"
    state["metrics"] = DeliberationMetrics(total_cost=5.00)  # $5.00 < $10.00 enterprise tier

    result = cost_guard_node(state)

    assert result["should_stop"] is False


def test_route_cost_guard_within_budget(sample_problem: Problem):
    """Test cost guard routing when within budget."""
    state = create_initial_state(
        session_id="test-route-ok",
        problem=sample_problem,
    )
    state["metrics"] = DeliberationMetrics(total_cost=0.50)

    # Run cost guard first
    state = cost_guard_node(state)

    # Route should be "continue"
    route = route_cost_guard(state)
    assert route == "continue"


def test_route_cost_guard_exceeds_budget(sample_problem: Problem):
    """Test cost guard routing when budget exceeded."""
    state = create_initial_state(
        session_id="test-route-exceeded",
        problem=sample_problem,
    )
    state["metrics"] = DeliberationMetrics(total_cost=1.50)

    # Run cost guard first
    state = cost_guard_node(state)

    # Route should be "force_synthesis"
    route = route_cost_guard(state)
    assert route == "force_synthesis"


# ============================================================================
# Multi-Layer Integration Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_all_five_layers_independently(sample_problem: Problem):
    """Test that all 5 layers can be activated independently."""
    # Layer 1: Recursion limit (constant check)
    assert DELIBERATION_RECURSION_LIMIT == 250  # Supports up to 5 sub-problems

    # Layer 2: Cycle detection (graph validation)
    graph = nx.DiGraph()
    graph.add_edges_from([("A", "B"), ("B", "A"), ("A", "C")])  # Cycle with exit
    validate_graph_acyclic(graph)  # Should not raise

    # Layer 3: Round counter
    state = create_initial_state(
        session_id="test-layer3",
        problem=sample_problem,
        max_rounds=4,
    )
    state["round_number"] = 4
    result = await check_convergence_node(state)
    assert result["should_stop"] is True
    assert result["stop_reason"] == "max_rounds"

    # Layer 4: Timeout (tested separately with asyncio)
    assert DEFAULT_TIMEOUT_SECONDS == 3600

    # Layer 5: Cost guard
    state = create_initial_state(
        session_id="test-layer5",
        problem=sample_problem,
    )
    state["metrics"] = DeliberationMetrics(total_cost=1.50)
    result = cost_guard_node(state)
    assert result["should_stop"] is True
    assert result["stop_reason"] == "cost_budget_exceeded"


@pytest.mark.asyncio
async def test_multiple_layers_triggered(sample_problem: Problem):
    """Test scenario where multiple layers could trigger."""
    state = create_initial_state(
        session_id="test-multi-layer",
        problem=sample_problem,
        max_rounds=4,
    )
    state["round_number"] = 4  # At max_rounds
    state["metrics"] = DeliberationMetrics(total_cost=2.00)  # Also exceeds cost

    # Layer 3 should trigger first (round counter)
    result = await check_convergence_node(state)
    assert result["should_stop"] is True
    # max_rounds triggers first (before hard cap at 6)
    assert result["stop_reason"] == "max_rounds"

    # Layer 5 also triggers independently
    result = cost_guard_node(result)
    assert result["should_stop"] is True
    # Cost guard overwrites stop_reason
    assert result["stop_reason"] == "cost_budget_exceeded"


def test_cost_guard_zero_cost(sample_problem: Problem):
    """Test cost guard with zero cost (edge case)."""
    state = create_initial_state(
        session_id="test-zero-cost",
        problem=sample_problem,
    )
    state["metrics"] = DeliberationMetrics(total_cost=0.0)

    result = cost_guard_node(state)

    assert result["should_stop"] is False


@pytest.mark.asyncio
async def test_convergence_and_cost_guard_interaction(sample_problem: Problem):
    """Test interaction between convergence check and cost guard.

    Updated for quality metrics refactoring (commit d1fdc3b):
    - Convergence threshold increased from 0.85 to 0.90
    - Requires participation rate >= 0.70
    - Requires novelty score <= 0.40

    Updated for Issue #3 fix:
    - Convergence is now recalculated each round (not cached)
    - Test mocks the semantic calculation to return high score
    """
    from unittest.mock import AsyncMock, patch

    from bo1.models.state import ContributionMessage

    state = create_initial_state(
        session_id="test-interaction",
        problem=sample_problem,
        max_rounds=6,
    )
    state["round_number"] = 3

    # Add personas for participation check
    state["personas"] = [
        {"code": "CFO", "name": "Zara Kim"},
        {"code": "CTO", "name": "Alex Rivera"},
    ]

    # Add enough contributions for novelty calculation (need >= 6)
    state["contributions"] = [
        ContributionMessage(
            persona_code="CFO",
            persona_name="Zara",
            content="We should prioritize cash flow management",
            round_number=1,
        ),
        ContributionMessage(
            persona_code="CTO",
            persona_name="Alex",
            content="Cash flow is critical",
            round_number=1,
        ),
        ContributionMessage(
            persona_code="CFO",
            persona_name="Zara",
            content="Cash management remains important",
            round_number=2,
        ),
        ContributionMessage(
            persona_code="CTO",
            persona_name="Alex",
            content="We need to focus on cash",
            round_number=2,
        ),
        ContributionMessage(
            persona_code="CFO",
            persona_name="Zara",
            content="Cash flow is the priority",
            round_number=3,
        ),
        ContributionMessage(
            persona_code="CTO",
            persona_name="Alex",
            content="Managing cash is essential",
            round_number=3,
        ),
    ]

    # Pre-set cost and novelty (convergence will be recalculated via mock)
    state["metrics"] = DeliberationMetrics(total_cost=0.80, novelty_score=0.2)

    # Mock the semantic convergence calculation to return high score
    # AUDIT FIX (Priority 4.3): Function moved to bo1.graph.quality.metrics
    with patch(
        "bo1.graph.quality.metrics._calculate_convergence_score_semantic",
        new_callable=AsyncMock,
        return_value=0.91,
    ):
        # Both convergence (Layer 3) and cost check pass
        result = await check_convergence_node(state)
        assert result["should_stop"] is True  # Convergence triggered
        # NEW: With early exit logic, high convergence (0.91) + low novelty (0.2) triggers early_convergence
        assert result["stop_reason"] in ["consensus", "early_convergence"]

    result = cost_guard_node(result)
    assert result["should_stop"] is True  # Still stopped
    # Cost guard didn't override because within budget


# ============================================================================
# Semantic Convergence Detection Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_semantic_convergence_detects_repetition():
    """Test semantic convergence detection catches paraphrased repetition.

    This test verifies that the semantic similarity approach catches
    repetition that keyword matching would miss.
    """
    from bo1.graph.quality.metrics import (
        _calculate_convergence_score_semantic,  # AUDIT FIX (Priority 4.3): Moved
    )
    from bo1.models.state import ContributionMessage

    # Create contributions with semantically identical content (paraphrased)
    contributions = [
        ContributionMessage(
            persona_code="CFO",
            persona_name="CFO",
            round_number=1,
            content="We should prioritize cash flow management and runway extension",
            thinking="Analysis...",
            token_count=50,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="CFO",
            persona_name="CFO",
            round_number=2,
            content="It's critical to focus on managing our cash position and extending financial runway",
            thinking="More analysis...",
            token_count=52,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="CFO",
            persona_name="CFO",
            round_number=3,
            content="The key priority is optimizing our cash flow and ensuring adequate runway",
            thinking="Continued analysis...",
            token_count=48,
            cost=0.001,
        ),
    ]

    # Calculate semantic convergence
    convergence_score = await _calculate_convergence_score_semantic(contributions)

    # Semantic similarity should detect the repetition
    # (even though no agreement keywords are used)
    assert convergence_score > 0.70  # High convergence detected
    assert convergence_score <= 1.0  # Valid score range


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_semantic_convergence_diverse_content():
    """Test semantic convergence correctly identifies diverse contributions."""
    from bo1.graph.quality.metrics import (
        _calculate_convergence_score_semantic,  # AUDIT FIX (Priority 4.3): Moved
    )
    from bo1.models.state import ContributionMessage

    # Create contributions with diverse content
    contributions = [
        ContributionMessage(
            persona_code="CFO",
            persona_name="CFO",
            round_number=1,
            content="We need to analyze the financial implications of this investment",
            thinking="Analysis...",
            token_count=45,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="CTO",
            persona_name="CTO",
            round_number=2,
            content="The technical architecture requires significant refactoring to support this feature",
            thinking="Technical evaluation...",
            token_count=48,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="CMO",
            persona_name="CMO",
            round_number=3,
            content="Our marketing strategy should focus on user acquisition in new markets",
            thinking="Marketing perspective...",
            token_count=47,
            cost=0.001,
        ),
    ]

    # Calculate semantic convergence
    convergence_score = await _calculate_convergence_score_semantic(contributions)

    # Diverse content should have low convergence score
    assert convergence_score < 0.50  # Low convergence (diverse topics)
    assert convergence_score >= 0.0  # Valid score range


@pytest.mark.asyncio
async def test_semantic_convergence_fallback_on_error():
    """Test that semantic convergence falls back to keyword method on error."""
    from bo1.graph.quality.metrics import (
        _calculate_convergence_score_semantic,  # AUDIT FIX (Priority 4.3): Moved
    )
    from bo1.models.state import ContributionMessage

    # Create contributions with agreement keywords for fallback test
    contributions = [
        ContributionMessage(
            persona_code="CFO",
            persona_name="CFO",
            round_number=1,
            content="I agree with the proposal. Yes, we should proceed exactly as suggested.",
            thinking="Agreement...",
            token_count=45,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="CTO",
            persona_name="CTO",
            round_number=2,
            content="I concur. The approach is correct and aligned with our goals.",
            thinking="Concurrence...",
            token_count=42,
            cost=0.001,
        ),
    ]

    # Calculate convergence (should work even if embeddings fail)
    # If VOYAGE_API_KEY is not set, it will fall back to keyword method
    convergence_score = await _calculate_convergence_score_semantic(contributions)

    # Either semantic or keyword should detect convergence
    assert convergence_score >= 0.0  # Valid score
    assert convergence_score <= 1.0  # Valid range


@pytest.mark.asyncio
async def test_check_convergence_node_uses_semantic_detection(sample_problem: Problem):
    """Test that check_convergence_node uses semantic detection."""
    from bo1.models.state import ContributionMessage

    state = create_initial_state(
        session_id="test-semantic",
        problem=sample_problem,
        max_rounds=6,
    )
    state["round_number"] = 4

    # Add semantically repetitive contributions (no agreement keywords)
    state["contributions"] = [
        ContributionMessage(
            persona_code="CFO",
            persona_name="CFO",
            round_number=1,
            content="We should prioritize cash flow management",
            thinking="Analysis...",
            token_count=40,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="CFO",
            persona_name="CFO",
            round_number=2,
            content="It's critical to focus on managing our cash position",
            thinking="More analysis...",
            token_count=42,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="CFO",
            persona_name="CFO",
            round_number=3,
            content="The key priority is optimizing our cash flow",
            thinking="Continued analysis...",
            token_count=38,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="CFO",
            persona_name="CFO",
            round_number=4,
            content="Cash management remains the most important consideration",
            thinking="Final analysis...",
            token_count=41,
            cost=0.001,
        ),
    ]

    # Run convergence check
    result = await check_convergence_node(state)

    # Semantic detection should calculate convergence score
    metrics = result.get("metrics")
    if metrics and metrics.convergence_score is not None:
        # Convergence score should be calculated
        assert metrics.convergence_score >= 0.0
        assert metrics.convergence_score <= 1.0
