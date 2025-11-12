"""Deliberation orchestration engine.

Manages the end-to-end deliberation flow including:
- Initial round execution (parallel persona contributions)
- Multi-round deliberation
- Round management and state tracking
"""

import asyncio
import logging
from typing import Any

from bo1.config import MODEL_BY_ROLE
from bo1.data import get_persona_by_code
from bo1.llm.client import ClaudeClient
from bo1.models.state import (
    ContributionMessage,
    ContributionType,
    DeliberationPhase,
    DeliberationState,
)
from bo1.prompts.reusable_prompts import compose_persona_prompt

logger = logging.getLogger(__name__)


class DeliberationEngine:
    """Orchestrates the deliberation process.

    Manages:
    - Initial round (parallel contributions from all personas)
    - Multi-round deliberation
    - Context building and management
    - State updates

    Uses Sonnet 4.5 for personas with prompt caching for cost optimization.
    """

    def __init__(
        self,
        state: DeliberationState,
        client: ClaudeClient | None = None,
    ) -> None:
        """Initialize the deliberation engine.

        Args:
            state: Current deliberation state
            client: Optional ClaudeClient instance. If None, creates a new one.
        """
        self.state = state
        self.client = client or ClaudeClient()
        self.model_name = MODEL_BY_ROLE["persona"]

    async def run_initial_round(self) -> list[ContributionMessage]:
        """Run the initial round with parallel persona contributions.

        All personas contribute simultaneously based on the problem statement.
        This is more efficient than sequential contributions and provides
        diverse initial perspectives.

        Returns:
            List of contribution messages from all personas

        Example:
            >>> engine = DeliberationEngine(state)
            >>> contributions = await engine.run_initial_round()
            >>> len(contributions)
            5
        """
        logger.info(f"Starting initial round with {len(self.state.selected_personas)} personas")

        # Update state phase
        self.state.phase = DeliberationPhase.INITIAL_ROUND

        # Get current sub-problem
        current_sp = self.state.problem.get_sub_problem(self.state.current_sub_problem_id)
        if not current_sp:
            raise ValueError(f"Sub-problem not found: {self.state.current_sub_problem_id}")

        # Build participant list
        participant_names = [persona.display_name for persona in self.state.selected_personas]
        participant_list = ", ".join(participant_names)

        # Create tasks for parallel execution
        tasks = []
        for persona_profile in self.state.selected_personas:
            task = self._call_persona_async(
                persona_profile=persona_profile,
                problem_statement=current_sp.goal,
                problem_context=current_sp.context,
                participant_list=participant_list,
                round_number=0,
                contribution_type=ContributionType.INITIAL,
            )
            tasks.append(task)

        # Execute all persona calls in parallel
        logger.info(f"Executing {len(tasks)} persona calls in parallel...")
        contributions = await asyncio.gather(*tasks)

        # Add contributions to state
        for contribution in contributions:
            self.state.add_contribution(contribution)

        logger.info(f"Initial round complete: {len(contributions)} contributions collected")

        # Update phase
        self.state.phase = DeliberationPhase.DISCUSSION

        return contributions

    async def _call_persona_async(
        self,
        persona_profile: Any,  # PersonaProfile type
        problem_statement: str,
        problem_context: str,
        participant_list: str,
        round_number: int,
        contribution_type: ContributionType,
        previous_contributions: list[ContributionMessage] | None = None,
    ) -> ContributionMessage:
        """Call a single persona asynchronously.

        Args:
            persona_profile: The persona profile to call
            problem_statement: The problem/goal to address
            problem_context: Additional context
            participant_list: Comma-separated list of participant names
            round_number: Current round number
            contribution_type: Type of contribution
            previous_contributions: Previous round contributions (for context)

        Returns:
            ContributionMessage with the persona's contribution
        """
        logger.debug(f"Calling persona: {persona_profile.display_name}")

        # Get full persona data
        persona_data = get_persona_by_code(persona_profile.code)
        if not persona_data:
            raise ValueError(f"Persona not found: {persona_profile.code}")

        # Compose system prompt
        system_prompt = compose_persona_prompt(
            persona_system_role=persona_data["system_prompt"],
            problem_statement=problem_statement,
            participant_list=participant_list,
            current_phase="initial_round" if round_number == 0 else "discussion",
        )

        # Build user message with context
        user_message_parts = [
            f"## Problem\n{problem_statement}\n",
        ]

        if problem_context:
            user_message_parts.append(f"\n## Context\n{problem_context}\n")

        if previous_contributions:
            user_message_parts.append("\n## Previous Contributions\n")
            for contrib in previous_contributions:
                user_message_parts.append(f"**{contrib.persona_name}**: {contrib.content}\n\n")

        if round_number == 0:
            user_message_parts.append(
                "\n## Your Task\n"
                "Provide your initial analysis and recommendations for this problem. "
                "Use the <thinking> and <contribution> structure as specified in your guidelines."
            )
        else:
            user_message_parts.append(
                "\n## Your Task\n"
                "Respond to the previous contributions, building on or challenging points raised. "
                "Use the <thinking> and <contribution> structure as specified in your guidelines."
            )

        user_message = "".join(user_message_parts)

        # Call LLM
        response = self.client.call(
            model_name=self.model_name,
            system_prompt=system_prompt,
            user_message=user_message,
        )

        # Parse response (extract <thinking> and <contribution>)
        thinking, contribution = self._parse_persona_response(response["content"])

        # Create contribution message
        contrib_msg = ContributionMessage(
            persona_code=persona_profile.code,
            persona_name=persona_profile.display_name,
            content=contribution,
            thinking=thinking,
            contribution_type=contribution_type,
            round_number=round_number,
            token_count=response.get("usage", {}).get("total_tokens", 0),
            cost=response.get("cost", 0.0),
        )

        logger.debug(
            f"Persona {persona_profile.display_name} contributed "
            f"({contrib_msg.token_count} tokens, ${contrib_msg.cost:.4f})"
        )

        return contrib_msg

    def _parse_persona_response(self, content: str) -> tuple[str | None, str]:
        """Parse persona response to extract <thinking> and <contribution>.

        Args:
            content: Raw response content

        Returns:
            Tuple of (thinking, contribution)
        """
        thinking = None
        contribution = content

        # Extract <thinking> if present
        if "<thinking>" in content and "</thinking>" in content:
            thinking_start = content.index("<thinking>") + len("<thinking>")
            thinking_end = content.index("</thinking>")
            thinking = content[thinking_start:thinking_end].strip()

        # Extract <contribution> if present
        if "<contribution>" in content and "</contribution>" in content:
            contrib_start = content.index("<contribution>") + len("<contribution>")
            contrib_end = content.index("</contribution>")
            contribution = content[contrib_start:contrib_end].strip()
        else:
            # If no explicit <contribution> tag, use the part after </thinking>
            if "</thinking>" in content:
                contribution = content.split("</thinking>", 1)[1].strip()

        return thinking, contribution

    def get_participant_summary(self) -> str:
        """Get a summary of current participants.

        Returns:
            Formatted string with participant names and roles
        """
        lines = ["## Participants"]
        for persona in self.state.selected_personas:
            lines.append(f"- **{persona.display_name}**: {persona.archetype}")
        return "\n".join(lines)

    def get_round_summary(self, round_number: int) -> list[ContributionMessage]:
        """Get all contributions from a specific round.

        Args:
            round_number: The round to retrieve

        Returns:
            List of contributions from that round
        """
        return [msg for msg in self.state.messages if msg.round_number == round_number]

    def get_total_cost(self) -> float:
        """Calculate total cost of deliberation so far.

        Returns:
            Total cost in USD
        """
        return sum(msg.cost or 0.0 for msg in self.state.messages)

    def get_total_tokens(self) -> int:
        """Calculate total tokens used so far.

        Returns:
            Total token count
        """
        return sum(msg.token_count or 0 for msg in self.state.messages)
