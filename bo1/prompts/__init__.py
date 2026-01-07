"""Centralized reusable prompt components for the Board of One system.

This module contains common prompt sections that can be composed into
agent-specific prompts, ensuring consistency and maintainability.

Based on PROMPT_ENGINEERING_FRAMEWORK.md best practices:
- XML structure for all prompts
- <thinking> tags required for reasoning
- Behavioral guidelines (ALWAYS/NEVER/UNCERTAIN)
- Evidence protocol for hallucination prevention
- Response prefilling support for character consistency

REORGANIZATION NOTE:
As of 2025-12-02, this module has been split into domain-specific files:
- protocols.py: Behavioral guidelines, evidence protocol, security protocol
- facilitator.py: Facilitator orchestration prompts
- moderator.py: Moderator intervention prompts
- researcher.py: Research analyst prompts
- recommendations.py: Final recommendation (voting) prompts
- synthesis.py: Synthesis and final report prompts
- meta_synthesis.py: Meta-synthesis for multi-sub-problem integration
- persona.py: Persona contribution prompts
- utils.py: Utility functions (prefill, phase config)

This __init__.py re-exports everything for backward compatibility.
All existing imports like `from bo1.prompts.reusable_prompts import X` continue to work.
"""

# =============================================================================
# Re-export all public APIs for backward compatibility
# =============================================================================

# Protocol definitions
# Facilitator prompts
from bo1.prompts.facilitator import (
    FACILITATOR_SYSTEM_TEMPLATE,
    compose_facilitator_prompt,
)

# Meta-synthesis prompts
from bo1.prompts.meta_synthesis import (
    META_SYNTHESIS_ACTION_PLAN_PROMPT,
    META_SYNTHESIS_PROMPT_TEMPLATE,
)

# Moderator prompts
from bo1.prompts.moderator import (
    MODERATOR_SYSTEM_TEMPLATE,
    compose_moderator_prompt,
)

# Persona prompts
from bo1.prompts.persona import (
    BEST_EFFORT_PROMPT,
    CHALLENGE_PHASE_PROMPT,
    compose_persona_contribution_prompt,
    compose_persona_prompt,
    compose_persona_prompt_cached,
    compose_persona_prompt_hierarchical,
)
from bo1.prompts.protocols import (
    BEHAVIORAL_GUIDELINES,
    COMMUNICATION_PROTOCOL,
    CORE_PROTOCOL,
    DELIBERATION_CONTEXT_TEMPLATE,
    EVIDENCE_PROTOCOL,
    PLAIN_LANGUAGE_STYLE,
    SECURITY_ADDENDUM,
    SECURITY_PROTOCOL,
    SUB_PROBLEM_FOCUS_TEMPLATE,
    _build_prompt_protocols,
    _get_security_task,
)

# Recommendation prompts
from bo1.prompts.recommendations import (
    RECOMMENDATION_SYSTEM_PROMPT,
    RECOMMENDATION_USER_MESSAGE,
)

# Researcher prompts
from bo1.prompts.researcher import (
    RESEARCHER_SYSTEM_TEMPLATE,
    compose_researcher_prompt,
)

# Synthesis prompts
from bo1.prompts.synthesis import (
    SYNTHESIS_HIERARCHICAL_TEMPLATE,
    SYNTHESIS_LEAN_TEMPLATE,
    SYNTHESIS_PROMPT_TEMPLATE,
    compose_synthesis_prompt,
    get_limited_context_sections,
)

# Utility functions
from bo1.prompts.utils import (
    get_prefill_text,
    get_round_phase_config,
)

# Define public API
__all__ = [
    # Protocols
    "BEHAVIORAL_GUIDELINES",
    "COMMUNICATION_PROTOCOL",
    "CORE_PROTOCOL",
    "DELIBERATION_CONTEXT_TEMPLATE",
    "EVIDENCE_PROTOCOL",
    "PLAIN_LANGUAGE_STYLE",
    "SECURITY_ADDENDUM",
    "SECURITY_PROTOCOL",
    "SUB_PROBLEM_FOCUS_TEMPLATE",
    "_build_prompt_protocols",
    "_get_security_task",
    # Facilitator
    "FACILITATOR_SYSTEM_TEMPLATE",
    "compose_facilitator_prompt",
    # Moderator
    "MODERATOR_SYSTEM_TEMPLATE",
    "compose_moderator_prompt",
    # Researcher
    "RESEARCHER_SYSTEM_TEMPLATE",
    "compose_researcher_prompt",
    # Recommendations
    "RECOMMENDATION_SYSTEM_PROMPT",
    "RECOMMENDATION_USER_MESSAGE",
    # Synthesis
    "SYNTHESIS_HIERARCHICAL_TEMPLATE",
    "SYNTHESIS_LEAN_TEMPLATE",
    "SYNTHESIS_PROMPT_TEMPLATE",
    "compose_synthesis_prompt",
    "get_limited_context_sections",
    # Meta-synthesis
    "META_SYNTHESIS_ACTION_PLAN_PROMPT",
    "META_SYNTHESIS_PROMPT_TEMPLATE",
    # Persona
    "BEST_EFFORT_PROMPT",
    "CHALLENGE_PHASE_PROMPT",
    "compose_persona_contribution_prompt",
    "compose_persona_prompt",
    "compose_persona_prompt_cached",
    "compose_persona_prompt_hierarchical",
    # Utils
    "get_prefill_text",
    "get_round_phase_config",
]
