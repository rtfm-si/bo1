"""Agent module for Board of One.

Contains all agent types that participate in deliberation:
- DecomposerAgent: Breaks problems into sub-problems
- PersonaSelectorAgent: Recommends expert personas
- FacilitatorAgent: Orchestrates deliberation rounds
- ModeratorAgent: Provides interventions
- SummarizerAgent: Compresses round history
"""

from bo1.agents.decomposer import DecomposerAgent
from bo1.agents.selector import PersonaSelectorAgent

__all__ = [
    "DecomposerAgent",
    "PersonaSelectorAgent",
]
