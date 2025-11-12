#!/usr/bin/env python3
"""Fix test_integration_day7.py to match current schema."""

import re

with open("tests/test_integration_day7.py") as f:
    content = f.read()

# Fix 1: Import ConstraintType enum
if "from bo1.models.problem import" in content:
    content = content.replace(
        "from bo1.models.problem import Constraint, Problem, SubProblem",
        "from bo1.models.problem import Constraint, ConstraintType, Problem, SubProblem",
    )

# Fix 2: Use ConstraintType enum values
content = content.replace('type="budget"', "type=ConstraintType.BUDGET")
content = content.replace('type="time"', "type=ConstraintType.TIME")
content = content.replace('type="timeline"', "type=ConstraintType.TIME")

# Fix 3: Fix sample_deliberation_state fixture - use proper DeliberationState schema
# This is complex, so we'll replace the whole fixture

old_fixture = r'''@pytest.fixture
def sample_deliberation_state\(sample_problem, sample_sub_problem\):
    """Create a sample deliberation state for testing\."""
    maria_data = get_persona_by_code\("growth_hacker"\)
    zara_data = get_persona_by_code\("finance_strategist"\)

    return DeliberationState\(
        session_id="test-session-001",
        problem=sample_problem,
        sub_problems=\[sample_sub_problem\],
        current_sub_problem_index=0,
        personas=\[PersonaProfile\(\*\*maria_data\), PersonaProfile\(\*\*zara_data\)\],
        messages=\[\],
        round_number=0,
        phase="initial_round",
        max_rounds=10,
        metrics=\{\},
    \)'''

new_fixture = '''@pytest.fixture
def sample_deliberation_state(sample_problem, sample_sub_problem):
    """Create a sample deliberation state for testing."""
    maria_data = get_persona_by_code("growth_hacker")
    zara_data = get_persona_by_code("finance_strategist")

    if maria_data and zara_data:
        selected_personas = [PersonaProfile(**maria_data), PersonaProfile(**zara_data)]
    else:
        selected_personas = []

    return DeliberationState(
        session_id="test-session-001",
        problem=sample_problem,
        selected_personas=selected_personas,
        current_sub_problem=sample_sub_problem,
        phase=DeliberationPhase.INITIAL_ROUND,
    )'''

content = re.sub(old_fixture, new_fixture, content, flags=re.DOTALL)

# Fix 4: Import DeliberationPhase
if "from bo1.models.state import" in content:
    content = content.replace(
        "from bo1.models.state import ContributionMessage, DeliberationState",
        "from bo1.models.state import ContributionMessage, DeliberationPhase, DeliberationState",
    )

# Fix 5: Fix ContributionMessage - add thinking parameter (optional)
content = content.replace(
    """    contribution1 = ContributionMessage(
        persona_code=maria.code,
        persona_name=maria.display_name,
        content=response1,
        round_number=1,
        token_count=usage1.total_tokens,
        cost=usage1.calculate_cost("sonnet"),
    )""",
    """    contribution1 = ContributionMessage(
        persona_code=maria.code,
        persona_name=maria.display_name,
        content=response1,
        thinking=None,
        round_number=1,
        token_count=usage1.total_tokens,
        cost=usage1.calculate_cost("sonnet"),
    )""",
)

# Fix 6: Fix the second DeliberationState creation in the full pipeline test
# Look for the pattern and replace
old_state_creation = r'''        state = DeliberationState\(
            session_id="manual-test-001",
            problem=problem,
            sub_problems=\[sub_problem\],
            current_sub_problem_index=0,
            personas=\[PersonaProfile\(\*\*maria_data\), PersonaProfile\(\*\*zara_data\)\],
            messages=\[\],
            round_number=0,
        \)

        state.phase = "discussion"'''

new_state_creation = """        state = DeliberationState(
            session_id="manual-test-001",
            problem=problem,
            selected_personas=[PersonaProfile(**maria_data), PersonaProfile(**zara_data)] if maria_data and zara_data else [],
            current_sub_problem=sub_problem,
            phase=DeliberationPhase.DISCUSSION,
        )"""

content = re.sub(old_state_creation, new_state_creation, content, flags=re.DOTALL)

# Fix 7: Fix the assertion about role -> archetype
content = content.replace('assert "role" in persona_data', 'assert "archetype" in persona_data')
content = content.replace('f"Persona missing role:', 'f"Persona missing archetype:')

# Fix 8: Fix prompt assertions
content = content.replace(
    '"BEHAVIORAL_GUIDELINES" in system_prompt', '"<behavioral_guidelines>" in system_prompt'
)
content = content.replace(
    '"BEHAVIORAL_GUIDELINES" not in system_prompt', '"<behavioral_guidelines>" not in system_prompt'
)
content = content.replace(
    '"EVIDENCE_PROTOCOL" in system_prompt', '"<evidence_protocol>" in system_prompt'
)
content = content.replace(
    '"COMMUNICATION_PROTOCOL" in system_prompt', '"<communication_protocol>" in system_prompt'
)

# Fix 9: Fix maria.role -> maria.archetype
content = content.replace("maria.role", "maria.archetype")

# Fix 10: Type annotation for main function
content = content.replace("async def main():", "async def main() -> int:")

with open("tests/test_integration_day7.py", "w") as f:
    f.write(content)

print("✓ Fixed test_integration_day7.py")
