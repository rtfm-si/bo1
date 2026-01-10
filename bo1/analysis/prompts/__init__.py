"""Prompts for objective-driven data analysis.

This module contains prompts for the Data Analysis Reimagination feature,
transforming data analysis from statistics dashboards to objective-driven
insight engines.

Modules:
- data_requirements: What data users need for specific objectives
- relevance_assessment: How well a dataset serves business objectives
- insight_generation: Generate objective-aligned insights from data
- story_synthesis: Synthesize insights into a narrative data story
- conversation: Respond to user questions about their data
"""

from bo1.analysis.prompts.conversation import (
    CONVERSATION_SYSTEM_PROMPT,
    build_conversation_prompt,
)
from bo1.analysis.prompts.data_requirements import (
    DATA_REQUIREMENTS_SYSTEM_PROMPT,
    build_data_requirements_prompt,
)
from bo1.analysis.prompts.insight_generation import (
    INSIGHT_GENERATION_SYSTEM_PROMPT,
    build_insight_generation_prompt,
)
from bo1.analysis.prompts.relevance_assessment import (
    RELEVANCE_ASSESSMENT_SYSTEM_PROMPT,
    build_relevance_assessment_prompt,
)
from bo1.analysis.prompts.story_synthesis import (
    STORY_SYNTHESIS_SYSTEM_PROMPT,
    build_story_synthesis_prompt,
)

__all__ = [
    # Data Requirements
    "DATA_REQUIREMENTS_SYSTEM_PROMPT",
    "build_data_requirements_prompt",
    # Relevance Assessment
    "RELEVANCE_ASSESSMENT_SYSTEM_PROMPT",
    "build_relevance_assessment_prompt",
    # Insight Generation
    "INSIGHT_GENERATION_SYSTEM_PROMPT",
    "build_insight_generation_prompt",
    # Story Synthesis
    "STORY_SYNTHESIS_SYSTEM_PROMPT",
    "build_story_synthesis_prompt",
    # Conversation
    "CONVERSATION_SYSTEM_PROMPT",
    "build_conversation_prompt",
]
