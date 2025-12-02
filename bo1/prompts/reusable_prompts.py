"""Centralized reusable prompt components for the Board of One system.

DEPRECATED: This file is kept for backward compatibility only.
Please import from the new module structure:

- bo1.prompts.protocols (or bo1.prompts) for protocol definitions
- bo1.prompts.facilitator (or bo1.prompts) for facilitator prompts
- bo1.prompts.moderator (or bo1.prompts) for moderator prompts
- bo1.prompts.researcher (or bo1.prompts) for researcher prompts
- bo1.prompts.recommendations (or bo1.prompts) for voting prompts
- bo1.prompts.synthesis (or bo1.prompts) for synthesis prompts
- bo1.prompts.meta_synthesis (or bo1.prompts) for meta-synthesis prompts
- bo1.prompts.persona (or bo1.prompts) for persona prompts
- bo1.prompts.utils (or bo1.prompts) for utility functions

This file re-exports everything from the new modules for backward compatibility.
"""

# Re-export everything from the new module structure
from bo1.prompts import *  # noqa: F401, F403

# Keep the example at the bottom for reference
if __name__ == "__main__":
    # Example: Compose a persona prompt
    example_system_role = """<system_role>
You are Maria Santos, a financial strategy advisor who helps founders make data-driven investment decisions.
Your expertise includes financial modeling, ROI analysis, budget optimization, and fundraising strategy.
You are analytical, data-driven, and ask probing questions about numbers.
</system_role>"""

    from bo1.prompts.persona import compose_persona_prompt

    example_prompt = compose_persona_prompt(
        persona_system_role=example_system_role,
        problem_statement="Should we invest $500K in cloud migration?",
        participant_list="Maria Santos (Financial Strategy), Tariq Osman (Security), Aria Hoffman (Engineering)",
        current_phase="discussion",
    )

    print("=== Example Framework-Aligned Persona Prompt ===\n")
    print(example_prompt[:1000])
    print("\n[...truncated for brevity...]")

    from bo1.prompts.utils import get_prefill_text

    print("\n\n=== Example Prefill Text ===\n")
    print(get_prefill_text("Maria Santos"))
    print("[Claude continues from here...]")
