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
from bo1.agents.summarizer import SummarizerAgent
from bo1.graph.state import DeliberationGraphState
from bo1.llm.client import ClaudeClient
from bo1.llm.response import LLMResponse
from bo1.models.state import (
    ContributionMessage,
    ContributionType,
    DeliberationPhase,
)
from bo1.orchestration.metrics_calculator import MetricsCalculator
from bo1.orchestration.persona_executor import PersonaExecutor
from bo1.orchestration.prompt_builder import PromptBuilder
from bo1.prompts import get_round_phase_config
from bo1.utils.checkpoint_helpers import get_sub_problem_context, get_sub_problem_goal
from bo1.utils.logging_helpers import LogHelper

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
        state: DeliberationGraphState,
        client: ClaudeClient | None = None,
        facilitator: FacilitatorAgent | None = None,
        moderator: ModeratorAgent | None = None,
        summarizer: SummarizerAgent | None = None,
    ) -> None:
        """Initialize the deliberation engine.

        Args:
            state: Current deliberation state (v2 graph state)
            client: Optional ClaudeClient instance. If None, creates a new one.
            facilitator: Optional facilitator agent. If None, creates a new one.
            moderator: Optional moderator agent. If None, creates a new one.
            summarizer: Optional summarizer agent. If None, creates a new one.
        """
        self.state: DeliberationGraphState = state
        self.client = client or ClaudeClient()
        self.facilitator = facilitator or FacilitatorAgent()
        self.moderator = moderator or ModeratorAgent()
        self.summarizer = summarizer or SummarizerAgent()
        self.persona_executor = PersonaExecutor(client=self.client, state=state)
        self.used_moderators: list[ModeratorType] = []  # Track moderators used
        self.pending_summary_task: asyncio.Task[LLMResponse] | None = (
            None  # Track background summarization
        )

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
        personas = self.state.get("personas", [])
        logger.info(f"Starting initial round with {len(personas)} personas")

        # Update state phase
        self.state["phase"] = DeliberationPhase.INITIAL_ROUND

        # Get current sub-problem
        current_sp = self.state.get("current_sub_problem")
        if not current_sp:
            raise ValueError("No current sub-problem set in deliberation state")

        # Build participant list
        participant_names = [persona.display_name for persona in personas]
        participant_list = ", ".join(participant_names)

        # Create tasks for parallel execution
        tasks = []
        sub_problem_results = self.state.get("sub_problem_results", [])
        for persona_profile in personas:
            # Check if expert has memory from previous sub-problems
            expert_memory: str | None = None
            if sub_problem_results:
                # Collect memory from all previous sub-problems where this expert contributed
                memory_parts = []
                for result in sub_problem_results:
                    if persona_profile.code in result.expert_summaries:
                        prev_summary = result.expert_summaries[persona_profile.code]
                        prev_goal = result.sub_problem_goal
                        memory_parts.append(
                            f"Sub-problem: {prev_goal}\nYour position: {prev_summary}"
                        )

                if memory_parts:
                    expert_memory = "\n\n".join(memory_parts)
                    logger.info(
                        f"{persona_profile.display_name} has memory from {len(memory_parts)} "
                        f"previous sub-problem(s)"
                    )

            task = self._call_persona_async(
                persona_profile=persona_profile,
                problem_statement=get_sub_problem_goal(current_sp),
                problem_context=get_sub_problem_context(current_sp),
                participant_list=participant_list,
                round_number=1,  # Initial round IS round 1 (fixes double-contribution bug)
                contribution_type=ContributionType.INITIAL,
                expert_memory=expert_memory,
            )
            tasks.append(task)

        # Execute all persona calls in parallel
        logger.info(f"Executing {len(tasks)} persona calls in parallel...")
        results = await asyncio.gather(*tasks)

        # Separate contributions and LLM responses
        contributions = [r[0] for r in results]
        llm_responses = [r[1] for r in results]

        # Add contributions to state
        contributions_list = self.state.get("contributions", [])
        for contribution in contributions:
            contributions_list.append(contribution)
        self.state["contributions"] = contributions_list

        logger.info(f"Initial round complete: {len(contributions)} contributions collected")

        # Update phase
        self.state["phase"] = DeliberationPhase.DISCUSSION

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
        expert_memory: str | None = None,
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
            expert_memory: Optional cross-sub-problem memory (summary from previous sub-problems)

        Returns:
            Tuple of (contribution_message, llm_response) for metrics tracking
        """
        logger.debug(f"Calling persona: {persona_profile.display_name}")

        # Get adaptive round configuration
        max_rounds = self.state.get("max_rounds", 10) if self.state else 10
        round_config = get_round_phase_config(round_number + 1, max_rounds)

        # BUG FIX: Include clarification answers from problem.context
        # The identify_gaps_node injects clarification answers into problem.context,
        # but this context was never being passed to persona prompts
        enriched_problem_statement = problem_statement
        main_problem = self.state.get("problem") if self.state else None
        if main_problem:
            main_problem_context = (
                main_problem.get("context", "")
                if isinstance(main_problem, dict)
                else getattr(main_problem, "context", "")
            ) or ""
            # If there are clarification answers in the main problem context, include them
            if main_problem_context and "## User Clarifications" in main_problem_context:
                enriched_problem_statement = f"{problem_statement}\n\n{main_problem_context}"
                logger.info(
                    f"Included clarification answers in problem statement "
                    f"({len(main_problem_context)} chars)"
                )

        # Build prompts using PromptBuilder
        system_prompt, user_message = PromptBuilder.build_persona_prompt(
            persona_profile=persona_profile,
            problem_statement=enriched_problem_statement,
            state=self.state,
            round_number=round_number,
            expert_memory=expert_memory,
            previous_contributions=previous_contributions,
        )

        # Execute persona call using PersonaExecutor
        contrib_msg, llm_response = await self.persona_executor.execute_persona_call(
            persona_profile=persona_profile,
            system_prompt=system_prompt,
            user_message=user_message,
            round_number=round_number,
            contribution_type=contribution_type,
            round_config=round_config,
        )

        return contrib_msg, llm_response

    def get_participant_summary(self) -> str:
        """Get a summary of current participants.

        Returns:
            Formatted string with participant names and roles
        """
        lines = ["## Participants"]
        personas = self.state.get("personas", [])
        for persona in personas:
            lines.append(f"- **{persona.display_name}**: {persona.archetype}")
        return "\n".join(lines)

    def get_round_summary(self, round_number: int) -> list[ContributionMessage]:
        """Get all contributions from a specific round.

        Args:
            round_number: The round to retrieve

        Returns:
            List of contributions from that round
        """
        contributions = self.state.get("contributions", [])
        return [msg for msg in contributions if msg.round_number == round_number]

    def get_total_cost(self) -> float:
        """Calculate total cost of deliberation so far.

        Returns:
            Total cost in USD
        """
        contributions = self.state.get("contributions", [])
        return sum(msg.cost or 0.0 for msg in contributions)

    def get_total_tokens(self) -> int:
        """Calculate total tokens used so far.

        Returns:
            Total token count
        """
        contributions = self.state.get("contributions", [])
        return sum(msg.token_count or 0 for msg in contributions)

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

        # Get personas from state
        personas = self.state.get("personas", [])

        # Get current sub-problem
        current_sp = self.state.get("current_sub_problem")
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
                self.state["phase"] = DeliberationPhase.VOTING
                # Only include facilitator_response if it's not None
                return [], [facilitator_response] if facilitator_response else []

            # DISABLED: Moderator functionality removed (keeping research only)
            # if decision.action == "moderator":
            #     # Facilitator requested moderator intervention
            #     mod_type = decision.moderator_type or "contrarian"
            #     logger.info(f"Facilitator requested {mod_type} moderator intervention")
            #     # Get discussion excerpt for moderator
            #     discussion_excerpt = self.build_discussion_context(include_thinking=False)[-2000:]
            #     trigger_reason = decision.moderator_focus or decision.reasoning
            #     # Get moderator intervention
            #     intervention_text, mod_response = await self.moderator.intervene(
            #         moderator_type=mod_type,
            #         problem_statement=current_sp.goal,
            #         discussion_excerpt=discussion_excerpt,
            #         trigger_reason=trigger_reason,
            #     )
            #     # Create contribution message for moderator
            #     moderator_name = {
            #         "contrarian": "The Contrarian",
            #         "skeptic": "The Skeptic",
            #         "optimist": "The Optimist",
            #     }[mod_type]
            #     # Calculate cost from mod_response
            #     cost = mod_response.cost_total
            #     moderator_contrib = ContributionMessage(
            #         persona_code=f"moderator_{mod_type}",
            #         persona_name=moderator_name,
            #         content=intervention_text,
            #         thinking=None,
            #         contribution_type=ContributionType.MODERATOR,
            #         round_number=round_number,
            #         token_count=mod_response.total_tokens,
            #         cost=cost,
            #     )
            #     # Add to state
            #     contributions_list = self.state.get("contributions", [])
            #     contributions_list.append(moderator_contrib)
            #     self.state["contributions"] = contributions_list
            #     self.used_moderators.append(mod_type)
            #     logger.info(
            #         f"Moderator intervention complete ({moderator_contrib.token_count} tokens, ${cost:.4f})"
            #     )
            #     return [moderator_contrib], [mod_response]

            if decision.action == "research":
                # TODO: Implement research tool (Week 4)
                logger.warning("Research requested but not yet implemented")
                # For now, fall through to continue with first persona
                speaker_code = personas[0].code if personas else None

            if decision.action == "continue":
                speaker_code = decision.next_speaker
                speaker_prompt = decision.speaker_prompt or speaker_prompt

            if not speaker_code:
                # Fallback: use first persona
                speaker_code = personas[0].code if personas else None
                if not speaker_code:
                    raise ValueError("No personas available for deliberation")

        # Get speaker persona profile
        speaker_profile = next((p for p in personas if p.code == speaker_code), None)
        if not speaker_profile:
            raise ValueError(f"Speaker persona not found: {speaker_code}")

        logger.info(f"Round {round_number}: {speaker_profile.display_name} contributing")

        # Build context for this round
        problem_statement = get_sub_problem_goal(current_sp)
        problem_context = get_sub_problem_context(current_sp)
        participant_list = ", ".join([p.display_name for p in personas])

        # Get previous contributions for context (all contributions so far)
        # NOTE: In Week 3, we'll optimize this with hierarchical summarization
        previous_contributions = self.state.get("contributions", [])

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
        contributions_list = self.state.get("contributions", [])
        contributions_list.append(contribution)
        self.state["contributions"] = contributions_list

        # Calculate and log consensus metrics (if round > 1)
        if round_number > 1:
            contributions = self.state.get("contributions", [])
            metrics = MetricsCalculator.calculate_round_metrics(contributions, round_number)

            LogHelper.log_consensus_metrics(
                logger,
                round_number=round_number,
                max_rounds=max_rounds,
                convergence=metrics["convergence"],
                novelty=metrics["novelty"],
                conflict=metrics["conflict"],
                should_stop=metrics["should_stop"],
                stop_reason=metrics["stop_reason"],
            )

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

    async def trigger_background_summarization(self, round_number: int) -> None:
        """Trigger background summarization for a completed round.

        This method creates an asyncio task to summarize the round in the background
        while the next round proceeds. The summary will be ready when Round N+2 needs it.

        Design pattern:
        - Round 1 completes → trigger_background_summarization(1) → summary task created
        - Round 2 starts immediately (doesn't wait for summary)
        - Round 2 completes → await_pending_summary() → Round 1 summary ready
        - Round 2 summary created in background
        - Round 3 uses Round 1 summary (hierarchical context)

        Args:
            round_number: The round number that was just completed

        Example:
            >>> # After round 1 completes
            >>> await engine.trigger_background_summarization(1)
            >>> # Round 2 starts immediately, summary happens in background
        """
        # Wait for any pending summary from previous round
        await self.await_pending_summary()

        # Get contributions for this round
        contributions = self.state.get("contributions", [])
        round_contributions = [c for c in contributions if c.round_number == round_number]
        if not round_contributions:
            logger.warning(
                f"No contributions found for round {round_number}, skipping summarization"
            )
            return

        # Format contributions for summarizer
        contributions_data = [
            {"persona": msg.persona_name, "content": msg.content} for msg in round_contributions
        ]

        # Get problem statement for context (especially helpful for Round 1)
        problem_statement = None
        current_sp = self.state.get("current_sub_problem")
        if round_number == 1 and current_sp:
            problem_statement = get_sub_problem_goal(current_sp)

        # Create background task
        logger.info(f"Triggering background summarization for Round {round_number}")
        self.pending_summary_task = asyncio.create_task(
            self.summarizer.summarize_round(
                round_number=round_number,
                contributions=contributions_data,
                problem_statement=problem_statement,
            )
        )

    async def await_pending_summary(self) -> LLMResponse | None:
        """Wait for pending summary task to complete and store result.

        Returns:
            LLMResponse from the completed summary task, or None if no pending task

        Example:
            >>> response = await engine.await_pending_summary()
            >>> if response:
            ...     print(f"Summary ready: {response.content}")
        """
        if not self.pending_summary_task:
            return None

        try:
            logger.info("Awaiting pending summary task...")
            response = await self.pending_summary_task

            # Add summary to state
            round_summaries = self.state.get("round_summaries", [])
            round_summaries.append(response.content)
            self.state["round_summaries"] = round_summaries

            logger.info(
                f"Summary added to state (tokens: {response.token_usage.output_tokens}, "
                f"cost: ${response.cost_total:.6f})"
            )

            # Clear the task
            self.pending_summary_task = None

            return response

        except Exception as e:
            logger.error(f"Failed to await pending summary task: {e}")
            self.pending_summary_task = None
            return None

    def build_discussion_context(self, include_thinking: bool = False) -> str:
        """Build formatted discussion context for facilitator or other agents.

        Args:
            include_thinking: Whether to include <thinking> sections (default False)

        Returns:
            Formatted discussion history string
        """
        contributions = self.state.get("contributions", [])
        if not contributions:
            return "No contributions yet."

        lines = []
        current_round = -1

        for msg in contributions:
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
