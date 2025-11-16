"""Moderator agents that intervene strategically to improve deliberation quality.

Moderators challenge assumptions, raise overlooked questions, and push for more
rigorous thinking when the discussion needs it.

Three types:
- Contrarian: Challenges consensus, raises alternative perspectives
- Skeptic: Questions assumptions, demands evidence, highlights risks
- Optimist: Highlights opportunities, encourages action, counters excessive caution
"""

import logging
from typing import Literal

from bo1.agents.base import BaseAgent
from bo1.llm.response import LLMResponse
from bo1.prompts.reusable_prompts import compose_moderator_prompt
from bo1.utils.xml_parsing import extract_xml_tag

logger = logging.getLogger(__name__)

ModeratorType = Literal["contrarian", "skeptic", "optimist"]


# Moderator configurations
MODERATOR_CONFIGS = {
    "contrarian": {
        "name": "The Contrarian",
        "archetype": "Devil's Advocate",
        "specific_role": "Challenge prevailing assumptions and explore alternative perspectives",
        "task_specific": "challenging consensus and raising alternatives that may be overlooked",
    },
    "skeptic": {
        "name": "The Skeptic",
        "archetype": "Critical Thinker",
        "specific_role": "Question assumptions, demand evidence, and highlight potential risks",
        "task_specific": "questioning assumptions and ensuring rigorous evidence-based thinking",
    },
    "optimist": {
        "name": "The Optimist",
        "archetype": "Opportunity Finder",
        "specific_role": "Highlight opportunities, encourage decisive action, and counter excessive caution",
        "task_specific": "identifying opportunities and encouraging pragmatic action when overthinking occurs",
    },
}


class ModeratorAgent(BaseAgent):
    """Strategic moderator that intervenes to improve deliberation quality."""

    def get_default_model(self) -> str:
        """Return default model for moderator (Sonnet 4.5)."""
        return "sonnet-4.5"

    async def intervene(
        self,
        moderator_type: ModeratorType,
        problem_statement: str,
        discussion_excerpt: str,
        trigger_reason: str,
    ) -> tuple[str, LLMResponse]:
        """Generate a moderator intervention.

        Args:
            moderator_type: Type of moderator (contrarian/skeptic/optimist)
            problem_statement: The problem being deliberated
            discussion_excerpt: Recent discussion context
            trigger_reason: Why the moderator is being invoked

        Returns:
            Tuple of (intervention_text, llm_response)

        Example:
            >>> moderator = ModeratorAgent()
            >>> intervention, response = await moderator.intervene(
            ...     moderator_type="contrarian",
            ...     problem_statement="Should we invest in SEO or paid ads?",
            ...     discussion_excerpt="[Recent contributions...]",
            ...     trigger_reason="Group is converging too quickly without exploring alternatives"
            ... )
        """
        logger.info(f"Moderator intervening: {moderator_type}")

        # Get moderator config
        config = MODERATOR_CONFIGS[moderator_type]

        # Compose moderator prompt
        system_prompt = compose_moderator_prompt(
            persona_name=config["name"],
            persona_archetype=config["archetype"],
            moderator_specific_role=config["specific_role"],
            moderator_task_specific=config["task_specific"],
            problem_statement=problem_statement,
            discussion_excerpt=discussion_excerpt,
            trigger_reason=trigger_reason,
        )

        # Build user message
        user_message = """Generate your intervention now.

Use the <thinking> and <intervention> structure as specified in your guidelines.

Remember: Your goal is to improve the quality of the deliberation by raising an important
question or challenge, then return focus to the standard expert personas."""

        # Use new helper method instead of manual PromptRequest creation
        response = await self._create_and_call_prompt(
            system=system_prompt,
            user_message=user_message,
            phase="moderator_intervention",
            temperature=1.0,
            max_tokens=1024,
        )

        # Extract intervention content
        intervention_text = self._extract_intervention(response.content)

        logger.info(f"Moderator {moderator_type} intervention complete")

        return intervention_text, response

    def _extract_intervention(self, content: str) -> str:
        """Extract intervention content from response.

        Args:
            content: Full response content

        Returns:
            Intervention text (with or without tags)
        """
        # Use new extract_xml_tag_with_fallback utility
        intervention = extract_xml_tag(content, "intervention")
        if intervention:
            return intervention

        # If no tags, return everything after </thinking> if present
        if "</thinking>" in content:
            return content.split("</thinking>", 1)[1].strip()

        # Otherwise return full content
        return content.strip()

    def should_trigger_moderator(
        self, round_number: int, used_moderators: list[ModeratorType]
    ) -> ModeratorType | None:
        """Determine if a moderator should be triggered and which type.

        Simple logic for v1:
        - Every 5 rounds: Trigger contrarian (prevent groupthink)
        - Don't repeat moderators in same deliberation

        Args:
            round_number: Current round number
            used_moderators: List of moderators already used

        Returns:
            Moderator type to trigger, or None if no moderator needed

        Example:
            >>> moderator = ModeratorAgent()
            >>> moderator.should_trigger_moderator(5, [])
            'contrarian'
            >>> moderator.should_trigger_moderator(5, ['contrarian'])
            'skeptic'
            >>> moderator.should_trigger_moderator(3, [])
            None
        """
        # Only trigger every 5 rounds
        if round_number % 5 != 0:
            return None

        # Prioritize moderators not yet used
        for mod_type in ["contrarian", "skeptic", "optimist"]:
            if mod_type not in used_moderators:
                return mod_type  # type: ignore

        # If all used, don't repeat (v1 simple logic)
        logger.info(f"All moderators already used, skipping moderator at round {round_number}")
        return None
