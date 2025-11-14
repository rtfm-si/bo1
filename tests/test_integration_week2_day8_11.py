"""Integration test for Week 2 Day 8-11: Problem Decomposition & Initial Round.

Tests the complete flow from problem intake through initial deliberation round:
1. Problem decomposition
2. Persona selection
3. Initial round (parallel contributions)
"""

import asyncio
import json
import logging

import pytest

from bo1.agents.decomposer import DecomposerAgent
from bo1.agents.selector import PersonaSelectorAgent
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import DeliberationState
from bo1.orchestration.deliberation import DeliberationEngine

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.requires_llm
@pytest.mark.asyncio
async def test_decomposition_simple_problem():
    """Test decomposition of a simple (atomic) problem."""
    decomposer = DecomposerAgent()

    # Simple technical decision
    problem = "Should I use PostgreSQL or MySQL for my database?"
    context = "Building a B2B SaaS app, solo developer, familiar with both"

    response = await decomposer.decompose_problem(
        problem_description=problem,
        context=context,
    )

    # Parse decomposition from response
    result = json.loads(response.content)

    # Validate result structure
    assert "sub_problems" in result
    assert "is_atomic" in result
    assert result["is_atomic"] is True  # Should be atomic
    assert len(result["sub_problems"]) == 1  # Only one sub-problem

    # Validate decomposition quality
    is_valid, errors = decomposer.validate_decomposition(result)
    assert is_valid, f"Decomposition validation failed: {errors}"

    # Validate token usage tracking
    assert response.token_usage.total_tokens > 0
    assert response.cost_total > 0

    logger.info(
        f"✓ Simple problem decomposed correctly: {result['is_atomic']=} ({response.summary()})"
    )


@pytest.mark.integration
@pytest.mark.requires_llm
@pytest.mark.asyncio
async def test_decomposition_moderate_problem():
    """Test decomposition of a moderate complexity problem."""
    decomposer = DecomposerAgent()

    # Growth investment decision
    problem = (
        "I have $50K to invest in growth. Should I focus on SEO, paid ads, or content marketing?"
    )
    context = "Solo founder, SaaS product, $100K ARR, 12 months runway"
    constraints = ["Budget: $50K", "Timeline: 6 months"]

    response = await decomposer.decompose_problem(
        problem_description=problem,
        context=context,
        constraints=constraints,
    )

    # Parse decomposition from response
    result = json.loads(response.content)

    # Validate result structure
    assert "sub_problems" in result
    assert "is_atomic" in result

    # Should be decomposed (2-4 sub-problems for moderate complexity)
    assert result["is_atomic"] is False
    assert 2 <= len(result["sub_problems"]) <= 4

    # Validate each sub-problem has required fields
    for sp in result["sub_problems"]:
        assert "id" in sp
        assert "goal" in sp
        assert "complexity_score" in sp
        assert 1 <= sp["complexity_score"] <= 10

    # Validate decomposition quality
    is_valid, errors = decomposer.validate_decomposition(result)
    assert is_valid, f"Decomposition validation failed: {errors}"

    # Validate token usage tracking
    assert response.token_usage.total_tokens > 0
    assert response.cost_total > 0

    logger.info(
        f"✓ Moderate problem decomposed: {len(result['sub_problems'])} sub-problems ({response.summary()})"
    )


@pytest.mark.integration
@pytest.mark.requires_llm
@pytest.mark.asyncio
async def test_persona_selection():
    """Test persona selection for a sub-problem."""
    selector = PersonaSelectorAgent()

    # Create a test sub-problem
    sub_problem = SubProblem(
        id="sp_001",
        goal="Should I invest $50K in SEO or paid ads?",
        context="Solo founder, SaaS product, $100K ARR, 12 months runway",
        complexity_score=6,
    )

    response = await selector.recommend_personas(
        sub_problem=sub_problem,
        problem_context="Growth investment decision",
    )

    # Parse recommendation from response
    result = json.loads(response.content)

    # Validate result structure
    assert "recommended_personas" in result
    assert "analysis" in result
    assert "coverage_summary" in result

    # Should recommend 3-5 personas for complexity 6
    personas = result["recommended_personas"]
    assert 3 <= len(personas) <= 5

    # Validate each persona has required fields
    for p in personas:
        assert "code" in p
        assert "name" in p
        assert "rationale" in p

    # Validate persona codes exist
    persona_codes = [p["code"] for p in personas]
    is_valid, invalid_codes = selector.validate_persona_codes(persona_codes)
    assert is_valid, f"Invalid persona codes: {invalid_codes}"

    # Validate token usage tracking
    assert response.token_usage.total_tokens > 0
    assert response.cost_total > 0

    logger.info(f"✓ Personas selected: {', '.join(persona_codes)} ({response.summary()})")


@pytest.mark.integration
@pytest.mark.requires_llm
@pytest.mark.asyncio
async def test_initial_round_execution():
    """Test initial round with parallel persona contributions."""
    # Step 1: Create a simple problem
    problem = Problem(
        title="Growth Investment Decision",
        description="Determine optimal growth channel for $50K investment",
        context="Solo founder, SaaS product, $100K ARR",
        sub_problems=[
            SubProblem(
                id="sp_001",
                goal="Should I invest $50K in SEO or paid ads?",
                context="12 months runway, B2B SaaS targeting SMBs",
                complexity_score=6,
            )
        ],
    )

    # Step 2: Select personas (use manual selection for test speed)
    # In real flow, PersonaSelectorAgent would recommend these
    from bo1.data import get_persona_by_code
    from bo1.models.persona import PersonaProfile

    persona_codes = ["finance_strategist", "growth_hacker", "product_manager"]
    personas = []
    for code in persona_codes:
        p_data = get_persona_by_code(code)
        if p_data:
            # Create PersonaProfile from full persona data
            personas.append(PersonaProfile(**p_data))

    assert len(personas) == 3, "Failed to load test personas"

    # Step 3: Create deliberation state
    state = DeliberationState(
        session_id="test_initial_round",
        problem=problem,
        selected_personas=personas,
        current_sub_problem=problem.sub_problems[0],
    )

    # Step 4: Run initial round
    engine = DeliberationEngine(state=state)
    contributions, llm_responses = await engine.run_initial_round()

    # Validate results
    assert len(contributions) == 3, "Should have 3 contributions (1 per persona)"
    assert len(llm_responses) == 3, "Should have 3 LLM responses (1 per persona)"

    # Check each contribution has required fields
    for contrib in contributions:
        assert contrib.persona_code in persona_codes
        assert contrib.content  # Should have content
        assert contrib.round_number == 0  # Initial round
        assert contrib.token_count and contrib.token_count > 0  # Should have token count
        assert contrib.cost and contrib.cost > 0  # Should have cost

    # Check state was updated
    assert len(state.contributions) == 3
    assert state.phase.value == "discussion"  # Should advance to discussion phase

    # Log metrics
    total_cost = engine.get_total_cost()
    total_tokens = engine.get_total_tokens()
    logger.info("✓ Initial round complete:")
    logger.info(f"  - Contributions: {len(contributions)}")
    logger.info(f"  - Total tokens: {total_tokens}")
    logger.info(f"  - Total cost: ${total_cost:.4f}")

    # Cost should be reasonable (3 personas, ~200 tokens each = ~600 tokens)
    # With caching: first call creates cache, next 2 read from cache
    # Target: < $0.10 for initial round (allows for prompt variance)
    assert total_cost < 0.10, f"Initial round too expensive: ${total_cost:.4f}"

    logger.info("✓ Initial round test passed")


@pytest.mark.integration
@pytest.mark.requires_llm
@pytest.mark.asyncio
async def test_full_pipeline_simple():
    """Test the full pipeline: decomposition → selection → initial round."""
    # Step 1: Decompose problem
    decomposer = DecomposerAgent()
    problem_desc = "Should I invest $50K in SEO or paid ads?"
    context = "Solo founder, SaaS product, $100K ARR"

    decomp_response = await decomposer.decompose_problem(
        problem_description=problem_desc,
        context=context,
    )

    # Parse decomposition from response
    decomposition = json.loads(decomp_response.content)

    # Create Problem model
    problem = decomposer.create_problem_from_decomposition(
        title="Growth Investment",
        problem_description=problem_desc,
        context=context,
        decomposition=decomposition,
    )

    logger.info(
        f"✓ Problem decomposed: {len(problem.sub_problems)} sub-problems ({decomp_response.summary()})"
    )

    # Step 2: Select personas
    selector = PersonaSelectorAgent()
    selector_response = await selector.recommend_personas(
        sub_problem=problem.sub_problems[0],
        problem_context=problem.context,
    )

    # Parse recommendation from response
    recommendation = json.loads(selector_response.content)

    persona_codes = [p["code"] for p in recommendation["recommended_personas"]]
    personas = selector.get_personas_by_codes(persona_codes[:3])  # Use first 3 for speed

    # Convert to PersonaProfile models
    from bo1.models.persona import PersonaProfile

    persona_profiles = [PersonaProfile(**p) for p in personas]

    logger.info(f"✓ Personas selected: {', '.join(persona_codes[:3])}")

    # Step 3: Create state and run initial round
    state = DeliberationState(
        session_id="test_full_pipeline",
        problem=problem,
        selected_personas=persona_profiles,
        current_sub_problem=problem.sub_problems[0],
    )

    engine = DeliberationEngine(state=state)
    contributions, llm_responses = await engine.run_initial_round()

    # Validate end-to-end results
    assert len(contributions) == len(persona_profiles)
    assert len(llm_responses) == len(persona_profiles)

    # Calculate total cost including decomposition and selection
    total_cost = decomp_response.cost_total + selector_response.cost_total + engine.get_total_cost()
    total_tokens = (
        decomp_response.total_tokens + selector_response.total_tokens + engine.get_total_tokens()
    )

    assert total_cost < 0.15  # Should be under $0.15 (including decomp + selection)

    logger.info("✓ Full pipeline test passed")
    logger.info(f"  - Decomposition cost: ${decomp_response.cost_total:.4f}")
    logger.info(f"  - Selection cost: ${selector_response.cost_total:.4f}")
    logger.info(f"  - Deliberation cost: ${engine.get_total_cost():.4f}")
    logger.info(f"  - Total cost: ${total_cost:.4f}")
    logger.info(f"  - Total tokens: {total_tokens}")


if __name__ == "__main__":
    # Run tests manually
    logging.basicConfig(level=logging.INFO)

    print("\n" + "=" * 60)
    print("Week 2 Day 8-11 Integration Tests")
    print("=" * 60 + "\n")

    print("Test 1: Simple Problem Decomposition")
    asyncio.run(test_decomposition_simple_problem())
    print()

    print("Test 2: Moderate Problem Decomposition")
    asyncio.run(test_decomposition_moderate_problem())
    print()

    print("Test 3: Persona Selection")
    asyncio.run(test_persona_selection())
    print()

    print("Test 4: Initial Round Execution")
    asyncio.run(test_initial_round_execution())
    print()

    print("Test 5: Full Pipeline")
    asyncio.run(test_full_pipeline_simple())
    print()

    print("=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
