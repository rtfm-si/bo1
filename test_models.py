#!/usr/bin/env python3
"""Test script to validate Day 1-2 implementation.

Tests:
1. Load personas from personas.json
2. Create DeliberationState object
3. Validate all Pydantic models with sample data
"""

import json
import uuid

from bo1.config import calculate_cost, get_model_for_role, get_settings
from bo1.models import (
    Constraint,
    ConstraintType,
    ContributionMessage,
    ContributionType,
    DeliberationState,
    PersonaProfile,
    Problem,
    SubProblem,
    Vote,
    VoteDecision,
    aggregate_votes,
)


def test_load_personas() -> list[PersonaProfile]:
    """Test loading personas from personas.json."""
    print("🧪 Test 1: Loading personas from personas.json...")

    settings = get_settings()
    personas_path = settings.personas_path

    print(f"   📁 Personas path: {personas_path}")

    if not personas_path.exists():
        print(f"   ❌ FAIL: personas.json not found at {personas_path}")
        return []

    with open(personas_path) as f:
        personas_data = json.load(f)

    print(f"   📊 Found {len(personas_data)} personas in JSON")

    # Load all personas
    personas = [PersonaProfile(**p) for p in personas_data]

    print(f"   ✅ Successfully loaded {len(personas)} personas")
    print(f"   👥 Sample personas: {', '.join(p.display_name for p in personas[:5])}")

    # Test persona methods
    test_persona = personas[0]
    print(f"\n   🔍 Testing persona methods with {test_persona.display_name}:")
    print(f"      - Traits: {test_persona.get_traits()}")
    print(f"      - Expertise: {test_persona.get_expertise_list()}")

    return personas


def test_create_deliberation_state(personas: list[PersonaProfile]) -> DeliberationState:
    """Test creating a DeliberationState object."""
    print("\n🧪 Test 2: Creating DeliberationState object...")

    # Create a sample problem
    problem = Problem(
        title="SaaS Pricing Strategy",
        description="Determine optimal pricing model for new B2B SaaS product",
        context="Solo founder, $50K runway, launching in 6 months",
        constraints=[
            Constraint(
                type=ConstraintType.BUDGET,
                description="Total development budget",
                value=50000,
            ),
            Constraint(
                type=ConstraintType.TIME,
                description="Launch deadline",
                value="6 months",
            ),
        ],
        sub_problems=[
            SubProblem(
                id="sp_001",
                goal="Determine pricing tier structure (free, paid, enterprise)",
                context="Need to balance affordability with revenue goals",
                complexity_score=6,
                dependencies=[],
                constraints=[],
            )
        ],
    )

    print(f"   ✅ Created Problem: {problem.title}")
    print(f"      - Sub-problems: {len(problem.sub_problems)}")
    print(f"      - Constraints: {len(problem.constraints)}")
    print(f"      - Is atomic: {problem.is_atomic()}")

    # Create deliberation state
    state = DeliberationState(
        session_id=str(uuid.uuid4()),
        problem=problem,
        selected_personas=personas[:5],  # First 5 personas
        max_rounds=7,  # Moderate complexity
    )

    print(f"   ✅ Created DeliberationState: {state.session_id}")
    print(f"      - Phase: {state.phase}")
    print(f"      - Max rounds: {state.max_rounds}")
    print(f"      - Selected personas: {len(state.selected_personas)}")

    # Test adding contributions
    contribution = ContributionMessage(
        persona_code=personas[0].code,
        persona_name=personas[0].display_name,
        content="I recommend starting with a freemium model...",
        thinking="Let me analyze the growth opportunities...",
        contribution_type=ContributionType.INITIAL,
        round_number=0,
        token_count=250,
        cost=0.0015,
    )

    state.add_contribution(contribution)
    print(f"   ✅ Added contribution from {contribution.persona_name}")
    print(f"      - Total contributions: {len(state.contributions)}")

    # Test metrics update
    state.update_metrics(cost=0.0015, tokens=250, cache_hit=True, cache_read=100)
    print("   ✅ Updated metrics:")
    print(f"      - Total cost: ${state.metrics.total_cost:.4f}")
    print(f"      - Total tokens: {state.metrics.total_tokens}")
    print(f"      - Cache hits: {state.metrics.cache_hits}")

    return state


def test_validate_all_models() -> None:
    """Test validation of all Pydantic models."""
    print("\n🧪 Test 3: Validating all Pydantic models...")

    # Test Vote model
    votes = [
        Vote(
            persona_code="growth_hacker",
            persona_name="Zara",
            decision=VoteDecision.YES,
            reasoning="The freemium model aligns with growth hacking principles",
            confidence=0.85,
            weight=1.0,
        ),
        Vote(
            persona_code="finance_strategist",
            persona_name="Maria",
            decision=VoteDecision.CONDITIONAL,
            reasoning="Budget is tight, need to ensure positive ROI",
            confidence=0.7,
            conditions=["CAC must be < $50", "Payback period < 6 months"],
            weight=1.2,
        ),
        Vote(
            persona_code="risk_officer",
            persona_name="Ahmad",
            decision=VoteDecision.NO,
            reasoning="Too much risk without proven demand",
            confidence=0.9,
            weight=1.0,
        ),
    ]

    print(f"   ✅ Created {len(votes)} Vote objects")

    # Test vote aggregation
    aggregation = aggregate_votes(votes)
    print("   ✅ Aggregated votes:")
    print(f"      - Simple majority: {aggregation.simple_majority}")
    print(f"      - Consensus level: {aggregation.consensus_level}")
    print(f"      - Confidence-weighted score: {aggregation.confidence_weighted_score:.2f}")
    print(f"      - Average confidence: {aggregation.average_confidence:.2f}")
    print(f"      - Dissenting opinions: {len(aggregation.dissenting_opinions)}")
    print(f"      - Conditions: {len(aggregation.conditions_summary)}")


def test_config_functions() -> None:
    """Test configuration functions."""
    print("\n🧪 Test 4: Testing configuration functions...")

    # Test model selection
    persona_model = get_model_for_role("PERSONA")
    print(f"   ✅ Model for PERSONA: {persona_model}")

    facilitator_model = get_model_for_role("FACILITATOR")
    print(f"   ✅ Model for FACILITATOR: {facilitator_model}")

    summarizer_model = get_model_for_role("SUMMARIZER")
    print(f"   ✅ Model for SUMMARIZER: {summarizer_model}")

    # Test cost calculation using simple aliases
    cost_no_cache = calculate_cost(
        model_id="sonnet",  # Simple alias!
        input_tokens=1000,
        output_tokens=200,
    )
    print(f"   💰 Cost (no cache, using 'sonnet' alias): ${cost_no_cache:.6f}")

    cost_with_cache = calculate_cost(
        model_id="sonnet",  # Simple alias!
        input_tokens=0,  # No regular input
        output_tokens=200,
        cache_read_tokens=1000,  # All from cache
    )
    print(f"   💰 Cost (with cache, using 'sonnet' alias): ${cost_with_cache:.6f}")

    savings = (cost_no_cache - cost_with_cache) / cost_no_cache * 100
    print(f"   📊 Cache savings: {savings:.1f}%")

    # Test with haiku alias too
    haiku_cost = calculate_cost(
        model_id="haiku",  # Simple alias!
        input_tokens=1000,
        output_tokens=200,
    )
    print(f"   💰 Haiku cost (using 'haiku' alias): ${haiku_cost:.6f}")


def main() -> None:
    """Run all tests."""
    print("=" * 70)
    print("Day 1-2 Implementation Validation Tests")
    print("=" * 70)

    try:
        # Test 1: Load personas
        personas = test_load_personas()
        if not personas:
            print("\n❌ FAILED: Could not load personas")
            return

        # Test 2: Create deliberation state
        state = test_create_deliberation_state(personas)

        # Test 3: Validate all models
        test_validate_all_models()

        # Test 4: Config functions
        test_config_functions()

        print("\n" + "=" * 70)
        print("✅ All tests passed!")
        print("=" * 70)
        print("\n📋 Summary:")
        print(f"   - Personas loaded: {len(personas)}")
        print(f"   - DeliberationState created: {state.session_id}")
        print("   - All Pydantic models validated: ✅")
        print("   - Configuration functions working: ✅")
        print("\n🎉 Day 1-2 Foundation Complete!")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
