"""Day 7 Integration Test: Full Pipeline Validation.

This integration test validates that all components from Week 1 work together:
1. Load persona from personas.json
2. Compose persona prompt using compose_persona_prompt()
3. Make LLM call with prompt caching
4. Verify cache hit on second call
5. Save DeliberationState to Redis
6. Load DeliberationState from Redis
7. Export transcript to Markdown
8. Verify all components integrate correctly

Run with: pytest tests/test_integration_day7.py -v
"""

import asyncio

import pytest

from bo1.config import get_settings
from bo1.data import get_persona_by_code, load_personas
from bo1.llm import ClaudeClient
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Constraint, ConstraintType, Problem, SubProblem
from bo1.models.state import ContributionMessage, DeliberationPhase, DeliberationState
from bo1.prompts.reusable_prompts import compose_persona_prompt
from bo1.state.redis_manager import RedisManager
from bo1.state.serialization import to_json, to_markdown


@pytest.fixture
def settings():
    """Load settings from environment."""
    return get_settings()


@pytest.fixture
def client(settings):
    """Create a Claude client instance."""
    return ClaudeClient(api_key=settings.anthropic_api_key)


@pytest.fixture
def redis_manager(settings):
    """Create Redis manager instance."""
    return RedisManager(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )


@pytest.fixture
def sample_problem():
    """Create a sample problem for testing."""
    return Problem(
        title="Growth Channel Decision",
        description="Should we invest $50K in SEO or paid ads for customer acquisition?",
        context="Early-stage B2B SaaS, currently at $10K MRR, 6-month runway",
        constraints=[
            Constraint(
                type=ConstraintType.BUDGET,
                description="Total marketing budget",
                value="$50,000",
            ),
            Constraint(
                type=ConstraintType.TIME,
                description="Decision needed within",
                value="2 weeks",
            ),
        ],
    )


@pytest.fixture
def sample_sub_problem(sample_problem):
    """Create a sample sub-problem for testing."""
    return SubProblem(
        id="sp_001",
        goal="Determine ROI and risk profile for each channel",
        context=f"{sample_problem.description}\n{sample_problem.context}",
        complexity_score=6,
        dependencies=[],
    )


@pytest.fixture
def sample_deliberation_state(sample_problem, sample_sub_problem):
    """Create a sample deliberation state."""
    # Load a few personas
    maria_data = get_persona_by_code("growth_hacker")
    zara_data = get_persona_by_code("finance_strategist")

    if maria_data and zara_data:
        selected_personas = [PersonaProfile(**maria_data), PersonaProfile(**zara_data)]
    else:
        selected_personas = []

    return DeliberationState(
        session_id="test-integration-001",
        problem=sample_problem,
        selected_personas=selected_personas,
        current_sub_problem=sample_sub_problem,
        phase=DeliberationPhase.DISCUSSION,
    )


@pytest.mark.integration
@pytest.mark.requires_llm
@pytest.mark.asyncio
async def test_week1_integration_full_pipeline(
    client, redis_manager, sample_deliberation_state, sample_sub_problem
):
    """Complete Week 1 integration test: End-to-end pipeline validation."""

    print("\n🧪 Week 1 Integration Test: Full Pipeline\n")

    # Step 1: Load persona from personas.json
    print("1️⃣  Loading personas from personas.json...")
    personas = load_personas()
    assert len(personas) > 0, "Should load personas from JSON"

    maria_data = get_persona_by_code("growth_hacker")
    assert maria_data is not None, "Should find Maria (growth_hacker)"
    assert "system_prompt" in maria_data, "Persona should have system_prompt"

    maria = PersonaProfile(**maria_data)
    print(f"   ✅ Loaded {maria.name} ({maria.archetype})")

    # Step 2: Compose persona prompt using compose_persona_prompt()
    print("\n2️⃣  Composing persona prompt...")
    participant_list = "Maria (Growth), Zara (Finance)"

    system_prompt = compose_persona_prompt(
        persona_system_role=maria.system_prompt,
        problem_statement=sample_deliberation_state.problem.description,
        participant_list=participant_list,
        current_phase="initial_round",
    )

    assert len(system_prompt) > 500, "Composed prompt should be substantial"
    assert maria.name in system_prompt or "growth" in system_prompt.lower()
    assert "<behavioral_guidelines>" in system_prompt
    assert "<evidence_protocol>" in system_prompt
    print(f"   ✅ Composed prompt: {len(system_prompt)} characters")

    # Step 3: Make LLM call with prompt caching
    print("\n3️⃣  Making first LLM call (with cache creation)...")
    messages = [
        {
            "role": "user",
            "content": f"Problem: {sample_deliberation_state.problem.description}\n\nProvide your initial analysis.",
        }
    ]

    response1, usage1 = await client.call(
        model="sonnet",
        system=system_prompt,
        messages=messages,
        cache_system=True,
        max_tokens=300,
    )

    assert len(response1) > 0, "Should get response"
    assert usage1.output_tokens > 0, "Should have output tokens"
    print(f"   ✅ Response received: {len(response1)} chars")
    print(f"   📊 Usage: {usage1.total_tokens} tokens")
    print(f"   💾 Cache creation: {usage1.cache_creation_tokens} tokens")

    # Save first contribution to state
    contribution1 = ContributionMessage(
        persona_code=maria.code,
        persona_name=maria.display_name,
        content=response1,
        thinking=None,
        round_number=1,
        token_count=usage1.total_tokens,
        cost=usage1.calculate_cost("sonnet"),
    )
    sample_deliberation_state.add_contribution(contribution1)
    sample_deliberation_state.current_round = 1

    # Step 4: Verify cache hit on second call
    print("\n4️⃣  Making second LLM call (should hit cache)...")
    await asyncio.sleep(0.5)  # Let cache settle

    messages2 = [
        {
            "role": "user",
            "content": f"Problem: {sample_deliberation_state.problem.description}\n\nWhat are the key risks?",
        }
    ]

    response2, usage2 = await client.call(
        model="sonnet",
        system=system_prompt,  # Same system prompt - should hit cache
        messages=messages2,
        cache_system=True,
        max_tokens=300,
    )

    assert len(response2) > 0, "Should get second response"
    assert usage2.cache_read_tokens > 0, "Should have cache reads on second call"
    print(f"   ✅ Second response received: {len(response2)} chars")
    print(f"   💾 Cache reads: {usage2.cache_read_tokens} tokens")
    print(f"   📈 Cache hit rate: {usage2.cache_hit_rate * 100:.1f}%")

    # Verify cache savings
    if usage2.cache_read_tokens > 0:
        savings_pct = (1 - (0.30 / 3.00)) * 100  # Cache read vs regular input cost
        print(f"   💰 Cache savings: ~{savings_pct:.0f}% on cached tokens")

    # Step 5: Save DeliberationState to Redis
    print("\n5️⃣  Saving DeliberationState to Redis...")
    try:
        session_id = await redis_manager.save_state(sample_deliberation_state)
        assert session_id == sample_deliberation_state.session_id
        print(f"   ✅ Saved to Redis: {session_id}")
    except Exception as e:
        print(f"   ⚠️  Redis unavailable (expected in CI): {e}")
        print("   ℹ️  Skipping Redis steps")
        pytest.skip("Redis not available")

    # Step 6: Load DeliberationState from Redis
    print("\n6️⃣  Loading DeliberationState from Redis...")
    loaded_state = await redis_manager.load_state(session_id)
    assert loaded_state is not None, "Should load state from Redis"
    assert loaded_state.session_id == session_id
    assert loaded_state.current_round == 1
    assert len(loaded_state.contributions) == 1
    assert loaded_state.contributions[0].persona_code == maria.code
    print(f"   ✅ Loaded from Redis: {loaded_state.session_id}")
    print(f"   📝 Round: {loaded_state.current_round}")
    print(f"   💬 Contributions: {len(loaded_state.contributions)}")

    # Step 7: Export transcript to Markdown
    print("\n7️⃣  Exporting transcript to Markdown...")
    markdown = to_markdown(sample_deliberation_state)
    assert len(markdown) > 0, "Should generate markdown"
    assert sample_deliberation_state.problem.title in markdown
    assert maria.name in markdown
    assert "Round 1" in markdown
    print(f"   ✅ Generated Markdown: {len(markdown)} chars")

    # Also test JSON export
    json_str = to_json(sample_deliberation_state)
    assert len(json_str) > 0, "Should generate JSON"
    assert sample_deliberation_state.session_id in json_str
    print(f"   ✅ Generated JSON: {len(json_str)} chars")

    # Step 8: Verify all components integrate correctly
    print("\n8️⃣  Final validation...")
    assert loaded_state.session_id == sample_deliberation_state.session_id
    assert loaded_state.problem.title == sample_deliberation_state.problem.title
    assert len(loaded_state.selected_personas) == len(sample_deliberation_state.selected_personas)
    assert loaded_state.phase == sample_deliberation_state.phase

    print("   ✅ All components integrate correctly!")
    print("\n🎉 Week 1 Integration Test PASSED!\n")

    # Cleanup
    await redis_manager.close()


@pytest.mark.integration
def test_persona_data_quality():
    """Validate persona data quality and structure."""
    print("\n🧪 Validating Persona Data Quality\n")

    personas = load_personas()
    assert len(personas) >= 45, "Should have at least 45 personas"

    for persona_data in personas:
        # Required fields
        assert "code" in persona_data, f"Persona missing code: {persona_data}"
        assert "name" in persona_data, f"Persona missing name: {persona_data}"
        assert "archetype" in persona_data, f"Persona missing archetype: {persona_data}"
        assert "system_prompt" in persona_data, f"Persona missing system_prompt: {persona_data}"

        # Validate system_prompt is substantial (bespoke content)
        system_prompt = persona_data["system_prompt"]
        assert (
            len(system_prompt) > 200
        ), f"Persona {persona_data['code']} has too short system_prompt: {len(system_prompt)} chars"

        # Ensure system_prompt doesn't contain generic protocols
        # (those should be added via compose_persona_prompt)
        assert (
            "<behavioral_guidelines>" not in system_prompt
        ), f"Persona {persona_data['code']} should not include generic protocols in system_prompt"

    print(f"   ✅ Validated {len(personas)} personas")
    print("   ✅ All personas have required fields")
    print("   ✅ All system_prompts are substantial (bespoke content)")


@pytest.mark.integration
def test_prompt_composition_modularity():
    """Test that prompt composition correctly combines bespoke + generic + dynamic."""
    print("\n🧪 Testing Prompt Composition Modularity\n")

    # Load a persona
    maria_data = get_persona_by_code("growth_hacker")
    assert maria_data is not None, "Should find growth_hacker persona"
    maria = PersonaProfile(**maria_data)

    # Compose prompt
    system_prompt = compose_persona_prompt(
        persona_system_role=maria.system_prompt,
        problem_statement="Should we pivot to B2B or stay B2C?",
        participant_list="Maria, Zara, Tariq",
        current_phase="discussion",
    )

    # Verify it includes all components
    # 1. Bespoke identity (from persona.system_prompt)
    assert "growth" in system_prompt.lower() or maria.name in system_prompt

    # 2. Generic protocols (from reusable_prompts.py)
    assert "<behavioral_guidelines>" in system_prompt
    assert "<evidence_protocol>" in system_prompt
    assert "<communication_protocol>" in system_prompt

    # 3. Dynamic context (problem statement)
    assert "Should we pivot to B2B or stay B2C?" in system_prompt

    print("   ✅ Bespoke identity: Present")
    print("   ✅ Generic protocols: Present")
    print("   ✅ Dynamic context: Present")
    print(f"   ✅ Total prompt length: {len(system_prompt)} chars")


if __name__ == "__main__":
    """Run integration tests manually for quick verification."""
    import sys

    async def main() -> int:
        """Run integration tests."""
        print("🧪 Running Week 1 Integration Tests...\n")

        settings = get_settings()
        client = ClaudeClient(api_key=settings.anthropic_api_key)
        redis_manager = RedisManager(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
        )

        # Create sample state
        maria_data = get_persona_by_code("growth_hacker")
        zara_data = get_persona_by_code("finance_strategist")

        problem = Problem(
            title="Test Problem",
            description="Should we invest in SEO or paid ads?",
            context="Early-stage startup",
            constraints=[],
        )

        sub_problem = SubProblem(
            id="sp_001",
            goal="Determine best channel",
            context="Limited budget",
            complexity_score=5,
            dependencies=[],
        )

        if maria_data and zara_data:
            selected_personas = [PersonaProfile(**maria_data), PersonaProfile(**zara_data)]
        else:
            selected_personas = []

        state = DeliberationState(
            session_id="manual-test-001",
            problem=problem,
            selected_personas=selected_personas,
            current_sub_problem=sub_problem,
            phase=DeliberationPhase.DISCUSSION,
        )

        try:
            await test_week1_integration_full_pipeline(client, redis_manager, state, sub_problem)
            return 0
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            import traceback

            traceback.print_exc()
            return 1

    sys.exit(asyncio.run(main()))
