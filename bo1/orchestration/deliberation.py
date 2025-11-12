"""Deliberation orchestration engine.

Manages the end-to-end deliberation flow including:
- Initial round execution (parallel persona contributions)
- Multi-round deliberation
- Round management and state tracking
"""

import asyncio
import logging
from typing import Any

from bo1.agents.facilitator import FacilitatorAgent
from bo1.agents.moderator import ModeratorAgent, ModeratorType
from bo1.config import MODEL_BY_ROLE
from bo1.data import get_persona_by_code
from bo1.llm.client import ClaudeClient
from bo1.llm.response import LLMResponse
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
        facilitator: FacilitatorAgent | None = None,
        moderator: ModeratorAgent | None = None,
    ) -> None:
        """Initialize the deliberation engine.

        Args:
            state: Current deliberation state
            client: Optional ClaudeClient instance. If None, creates a new one.
            facilitator: Optional facilitator agent. If None, creates a new one.
            moderator: Optional moderator agent. If None, creates a new one.
        """
        from bo1.config import resolve_model_alias

        self.state = state
        self.client = client or ClaudeClient()
        self.facilitator = facilitator or FacilitatorAgent()
        self.moderator = moderator or ModeratorAgent()
        self.model_name = MODEL_BY_ROLE["persona"]
        self.model_id = resolve_model_alias(self.model_name)  # Full ID for pricing
        self.used_moderators: list[ModeratorType] = []  # Track moderators used

    async def run_initial_round(self) -> tuple[list[ContributionMessage], list[Any]]:
        """Run the initial round with parallel persona contributions.

        All personas contribute simultaneously based on the problem statement.
        This is more efficient than sequential contributions and provides
        diverse initial perspectives.

        Returns:
            Tuple of (contributions, llm_responses) where:
            - contributions: List of contribution messages from all personas
            - llm_responses: List of LLMResponse objects for metrics tracking

        Example:
            >>> engine = DeliberationEngine(state)
            >>> contributions, llm_responses = await engine.run_initial_round()
            >>> len(contributions)
            5
            >>> len(llm_responses)
            5
        """
        logger.info(f"Starting initial round with {len(self.state.selected_personas)} personas")

        # Update state phase
        self.state.phase = DeliberationPhase.INITIAL_ROUND

        # Get current sub-problem
        current_sp = self.state.current_sub_problem
        if not current_sp:
            raise ValueError("No current sub-problem set in deliberation state")

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
        results = await asyncio.gather(*tasks)

        # Separate contributions and LLM responses
        contributions = [r[0] for r in results]
        llm_responses = [r[1] for r in results]

        # Add contributions to state
        for contribution in contributions:
            self.state.add_contribution(contribution)

        logger.info(f"Initial round complete: {len(contributions)} contributions collected")

        # Update phase
        self.state.phase = DeliberationPhase.DISCUSSION

        return contributions, llm_responses

    async def _call_persona_async(
        self,
        persona_profile: Any,  # PersonaProfile type
        problem_statement: str,
        problem_context: str,
        participant_list: str,
        round_number: int,
        contribution_type: ContributionType,
        previous_contributions: list[ContributionMessage] | None = None,
    ) -> tuple[ContributionMessage, Any]:
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
            Tuple of (contribution_message, llm_response) for metrics tracking
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

        # Call LLM (async) with timing
        from datetime import datetime

        from bo1.llm.response import LLMResponse

        start_time = datetime.now()
        messages = [{"role": "user", "content": user_message}]
        response_text, token_usage = await self.client.call(
            model=self.model_name,
            messages=messages,
            system=system_prompt,
            cache_system=True,  # Enable prompt caching for cost optimization
        )
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Parse response (extract <thinking> and <contribution>)
        thinking, contribution = self._parse_persona_response(response_text)

        # Calculate cost
        cost = token_usage.calculate_cost(self.model_name)

        # Create contribution message
        contrib_msg = ContributionMessage(
            persona_code=persona_profile.code,
            persona_name=persona_profile.display_name,
            content=contribution,
            thinking=thinking,
            contribution_type=contribution_type,
            round_number=round_number,
            token_count=token_usage.total_tokens,
            cost=cost,
        )

        # Create LLM response for metrics tracking
        llm_response = LLMResponse(
            content=response_text,
            model=self.model_id,  # Use full model ID for accurate pricing
            token_usage=token_usage,
            duration_ms=duration_ms,
            phase="deliberation",
            agent_type=f"persona_{persona_profile.code}",
        )

        logger.debug(
            f"Persona {persona_profile.display_name} contributed "
            f"({contrib_msg.token_count} tokens, ${contrib_msg.cost:.4f})"
        )

        return contrib_msg, llm_response

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
        return [msg for msg in self.state.contributions if msg.round_number == round_number]

    def get_total_cost(self) -> float:
        """Calculate total cost of deliberation so far.

        Returns:
            Total cost in USD
        """
        return sum(msg.cost or 0.0 for msg in self.state.contributions)

    def get_total_tokens(self) -> int:
        """Calculate total tokens used so far.

        Returns:
            Total token count
        """
        return sum(msg.token_count or 0 for msg in self.state.contributions)

    async def run_round(
        self,
        round_number: int,
        max_rounds: int,
        speaker_code: str | None = None,
        speaker_prompt: str | None = None,
    ) -> tuple[list[ContributionMessage], list[LLMResponse]]:
        """Run a single round of deliberation.

        Args:
            round_number: Current round number (1-indexed)
            max_rounds: Maximum rounds allowed
            speaker_code: Optional specific persona to call (if None, facilitator decides)
            speaker_prompt: Optional specific prompt/focus for the speaker

        Returns:
            Tuple of (contributions, llm_responses) from this round

        Example:
            >>> # Run a round with facilitator deciding next speaker
            >>> contributions, responses = await engine.run_round(
            ...     round_number=2,
            ...     max_rounds=7
            ... )
            >>>
            >>> # Run a round with specific speaker
            >>> contributions, responses = await engine.run_round(
            ...     round_number=3,
            ...     max_rounds=7,
            ...     speaker_code="growth_hacker",
            ...     speaker_prompt="How would you prioritize these options?"
            ... )
        """
        logger.info(f"Starting round {round_number}/{max_rounds}")

        # Get current sub-problem
        current_sp = self.state.current_sub_problem
        if not current_sp:
            raise ValueError("No current sub-problem set in deliberation state")

        # If no speaker specified, ask facilitator to decide
        if speaker_code is None:
            logger.info("Asking facilitator to decide next action...")
            decision, facilitator_response = await self.facilitator.decide_next_action(
                state=self.state, round_number=round_number, max_rounds=max_rounds
            )

            # Handle facilitator decision
            if decision.action == "vote":
                logger.info("Facilitator decided to transition to voting phase")
                self.state.phase = DeliberationPhase.VOTING
                return [], [facilitator_response]

            if decision.action == "moderator":
                # Facilitator requested moderator intervention
                mod_type = decision.moderator_type or "contrarian"
                logger.info(f"Facilitator requested {mod_type} moderator intervention")

                # Get discussion excerpt for moderator
                discussion_excerpt = self.build_discussion_context(include_thinking=False)[-2000:]
                trigger_reason = decision.moderator_focus or decision.reasoning

                # Get moderator intervention
                intervention_text, mod_response = await self.moderator.intervene(
                    moderator_type=mod_type,
                    problem_statement=current_sp.goal,
                    discussion_excerpt=discussion_excerpt,
                    trigger_reason=trigger_reason,
                )

                # Create contribution message for moderator
                moderator_name = {
                    "contrarian": "The Contrarian",
                    "skeptic": "The Skeptic",
                    "optimist": "The Optimist",
                }[mod_type]

                # Calculate cost from mod_response
                cost = mod_response.cost_total

                moderator_contrib = ContributionMessage(
                    persona_code=f"moderator_{mod_type}",
                    persona_name=moderator_name,
                    content=intervention_text,
                    thinking=None,
                    contribution_type=ContributionType.MODERATOR,
                    round_number=round_number,
                    token_count=mod_response.total_tokens,
                    cost=cost,
                )

                # Add to state
                self.state.add_contribution(moderator_contrib)
                self.used_moderators.append(mod_type)

                logger.info(
                    f"Moderator intervention complete ({moderator_contrib.token_count} tokens, ${cost:.4f})"
                )

                return [moderator_contrib], [mod_response]

            if decision.action == "research":
                # TODO: Implement research tool (Week 4)
                logger.warning("Research requested but not yet implemented")
                # For now, fall through to continue with first persona
                speaker_code = (
                    self.state.selected_personas[0].code if self.state.selected_personas else None
                )

            if decision.action == "continue":
                speaker_code = decision.next_speaker
                speaker_prompt = decision.speaker_prompt or speaker_prompt

            if not speaker_code:
                # Fallback: use first persona
                speaker_code = (
                    self.state.selected_personas[0].code if self.state.selected_personas else None
                )
                if not speaker_code:
                    raise ValueError("No personas available for deliberation")

        # Get speaker persona profile
        speaker_profile = next(
            (p for p in self.state.selected_personas if p.code == speaker_code), None
        )
        if not speaker_profile:
            raise ValueError(f"Speaker persona not found: {speaker_code}")

        logger.info(f"Round {round_number}: {speaker_profile.display_name} contributing")

        # Build context for this round
        problem_statement = current_sp.goal
        problem_context = current_sp.context or ""
        participant_list = ", ".join([p.display_name for p in self.state.selected_personas])

        # Get previous contributions for context (all contributions so far)
        # NOTE: In Week 3, we'll optimize this with hierarchical summarization
        previous_contributions = self.state.contributions

        # Call the persona
        contribution, llm_response = await self._call_persona_async(
            persona_profile=speaker_profile,
            problem_statement=problem_statement,
            problem_context=problem_context,
            participant_list=participant_list,
            round_number=round_number,
            contribution_type=ContributionType.RESPONSE,
            previous_contributions=previous_contributions,
        )

        # Add contribution to state
        self.state.add_contribution(contribution)

        logger.info(
            f"Round {round_number} complete: {speaker_profile.display_name} contributed "
            f"({contribution.token_count} tokens, ${contribution.cost:.4f})"
        )

        return [contribution], [llm_response]

    def calculate_max_rounds(self, complexity_score: int) -> int:
        """Calculate maximum rounds based on problem complexity.

        Args:
            complexity_score: Complexity score from decomposition (1-10)

        Returns:
            Maximum number of rounds allowed

        Example:
            >>> engine.calculate_max_rounds(2)  # Simple
            5
            >>> engine.calculate_max_rounds(5)  # Moderate
            7
            >>> engine.calculate_max_rounds(9)  # Complex
            10
        """
        if complexity_score <= 3:
            return 5  # Simple problems: 5 rounds max
        elif complexity_score <= 6:
            return 7  # Moderate problems: 7 rounds max
        else:
            return 10  # Complex problems: 10 rounds max

    def build_discussion_context(self, include_thinking: bool = False) -> str:
        """Build formatted discussion context for facilitator or other agents.

        Args:
            include_thinking: Whether to include <thinking> sections (default False)

        Returns:
            Formatted discussion history string
        """
        if not self.state.contributions:
            return "No contributions yet."

        lines = []
        current_round = -1

        for msg in self.state.contributions:
            # Add round header if new round
            if msg.round_number != current_round:
                current_round = msg.round_number
                if current_round == 0:
                    lines.append("## Initial Round\n")
                else:
                    lines.append(f"## Round {current_round}\n")

            # Add contribution
            lines.append(f"**{msg.persona_name}**:\n")

            if include_thinking and msg.thinking:
                lines.append(f"<thinking>\n{msg.thinking}\n</thinking>\n\n")

            lines.append(f"{msg.content}\n\n")
            lines.append("---\n\n")

        return "".join(lines)
