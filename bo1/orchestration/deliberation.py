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
from bo1.config import MODEL_BY_ROLE
from bo1.data import get_persona_by_code
from bo1.llm.client import ClaudeClient
from bo1.llm.response import LLMResponse
from bo1.llm.response_parser import ResponseParser
from bo1.models.state import (
    ContributionMessage,
    ContributionType,
    DeliberationPhase,
    DeliberationState,
)
from bo1.prompts.reusable_prompts import get_round_phase_config
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
        state: DeliberationState,
        client: ClaudeClient | None = None,
        facilitator: FacilitatorAgent | None = None,
        moderator: ModeratorAgent | None = None,
        summarizer: SummarizerAgent | None = None,
    ) -> None:
        """Initialize the deliberation engine.

        Args:
            state: Current deliberation state
            client: Optional ClaudeClient instance. If None, creates a new one.
            facilitator: Optional facilitator agent. If None, creates a new one.
            moderator: Optional moderator agent. If None, creates a new one.
            summarizer: Optional summarizer agent. If None, creates a new one.
        """
        from bo1.config import resolve_model_alias

        self.state = state
        self.client = client or ClaudeClient()
        self.facilitator = facilitator or FacilitatorAgent()
        self.moderator = moderator or ModeratorAgent()
        self.summarizer = summarizer or SummarizerAgent()
        self.model_name = MODEL_BY_ROLE["persona"]
        self.model_id = resolve_model_alias(self.model_name)  # Full ID for pricing
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
            # Check if expert has memory from previous sub-problems
            expert_memory: str | None = None
            if hasattr(self.state, "sub_problem_results") and self.state.sub_problem_results:
                # Collect memory from all previous sub-problems where this expert contributed
                memory_parts = []
                for result in self.state.sub_problem_results:
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
                problem_statement=current_sp.goal,
                problem_context=current_sp.context,
                participant_list=participant_list,
                round_number=0,
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
        # Use estimated max_rounds based on complexity (default to 10 for moderate complexity)
        max_rounds = getattr(self.state, "max_rounds", 10) if hasattr(self, "state") else 10
        round_config = get_round_phase_config(
            round_number + 1, max_rounds
        )  # +1 because round_number is 0-indexed

        logger.debug(
            f"Round {round_number + 1} phase: {round_config['phase']} "
            f"(temp={round_config['temperature']}, max_tokens={round_config['max_tokens']})"
        )

        # Get full persona data
        persona_data = get_persona_by_code(persona_profile.code)
        if not persona_data:
            raise ValueError(f"Persona not found: {persona_profile.code}")

        # Check if we have round summaries for hierarchical context
        round_summaries = (
            self.state.round_summaries if hasattr(self.state, "round_summaries") else []
        )

        if round_summaries and round_number > 1:
            # Use hierarchical prompts (summaries + recent contributions)
            # MERGED WITH CRITICAL THINKING PROTOCOL (P1.1 fix)
            from bo1.prompts.reusable_prompts import compose_persona_prompt_hierarchical

            # Get participant list
            participant_list = ", ".join([p.display_name for p in self.state.selected_personas])

            # Get current round contributions (last round, for full detail)
            # We want the most recent round's contributions in full
            prev_round_contribs = [
                {"persona": c.persona_name, "content": c.content}
                for c in (previous_contributions or [])[-10:]  # Last 10 contributions
            ]

            # Compose hierarchical base prompt
            base_system_prompt = compose_persona_prompt_hierarchical(
                persona_system_role=f"{persona_data['name']}, {persona_data['description']}",
                problem_statement=problem_statement,
                participant_list=participant_list,
                round_summaries=round_summaries,  # All previous round summaries
                current_round_contributions=prev_round_contribs,  # Recent full contributions
                round_number=round_number + 1,  # +1 for 1-indexed display
                current_phase="discussion",
            )

            # MERGE: Inject critical thinking protocol
            # Get the protocol from enhanced prompts
            phase_config = get_round_phase_config(round_number + 1, self.state.max_rounds)

            # Determine debate phase based on round number
            if round_number <= 1:
                phase_instruction = """
                <debate_phase>EARLY - DIVERGENT THINKING</debate_phase>
                <phase_goals>
                - Explore multiple perspectives
                - Challenge initial assumptions
                - Raise concerns and risks
                - Identify gaps in analysis
                - DON'T seek consensus yet - surface disagreements
                </phase_goals>
                """
            elif round_number <= 3:
                phase_instruction = """
                <debate_phase>MIDDLE - DEEP ANALYSIS</debate_phase>
                <phase_goals>
                - Provide evidence for claims
                - Challenge weak arguments
                - Request clarification on unclear points
                - Build on strong ideas from others
                - Identify trade-offs and constraints
                </phase_goals>
                """
            else:
                phase_instruction = """
                <debate_phase>LATE - CONVERGENT THINKING</debate_phase>
                <phase_goals>
                - Synthesize key insights
                - Recommend specific actions
                - Acknowledge remaining uncertainties
                - Build consensus on critical points
                - Propose next steps
                </phase_goals>
                """

            critical_thinking_section = f"""
{phase_instruction}

<critical_thinking_protocol>
You MUST engage critically with the discussion:

1. **Challenge Assumptions**: If someone makes an assumption, question it
2. **Demand Evidence**: If a claim lacks support, ask for evidence
3. **Identify Gaps**: Point out what's missing from the analysis
4. **Build or Refute**: Explicitly agree/disagree with previous speakers
5. **Recommend Actions**: End with specific, actionable recommendations

**Format your response with explicit structure:**
- Start with: "Based on [previous speaker's] point about X..."
- Include: "I disagree/agree with [persona] because..."
- End with: "My recommendation is to [specific action]..."
</critical_thinking_protocol>

<forbidden_patterns>
- Generic agreement ("I agree with the previous speakers...")
- Vague observations without conclusions
- Listing facts without analysis
- Ending without a recommendation or question
</forbidden_patterns>
"""

            # Merge into system prompt
            system_prompt = base_system_prompt + "\n\n" + critical_thinking_section

            # User message is the speaker prompt
            user_message = expert_memory or round_config["directive"]

            logger.debug(
                f"Using hierarchical prompts with critical thinking: {len(round_summaries)} summaries, "
                f"{len(prev_round_contribs)} recent contributions, phase={phase_config['phase']}"
            )
        else:
            # Use regular prompts (no summaries yet or early rounds)
            from bo1.prompts.reusable_prompts import compose_persona_contribution_prompt

            # Convert previous contributions to dict format for enhanced prompts
            prev_contribs = [
                {
                    "persona_code": c.persona_code,
                    "persona_name": c.persona_name,
                    "content": c.content,
                }
                for c in (previous_contributions or [])
            ]

            # Use enhanced prompts with phase-based critical thinking
            system_prompt, user_message = compose_persona_contribution_prompt(
                persona_name=persona_data["name"],
                persona_description=persona_data["description"],
                persona_expertise=", ".join(persona_data.get("domain_expertise", [])),
                persona_communication_style=persona_data.get("response_style", "analytical"),
                problem_statement=problem_statement,
                previous_contributions=prev_contribs,
                speaker_prompt=expert_memory or round_config["directive"],
                round_number=round_number + 1,  # +1 for 1-indexed rounds
            )

        # Call LLM (async) with timing - use PromptBroker for retry protection
        from datetime import datetime

        from bo1.llm.broker import PromptBroker, PromptRequest
        from bo1.llm.response import LLMResponse

        start_time = datetime.now()

        # Create prompt request to use broker (with retry protection)
        broker = PromptBroker(client=self.client)
        request = PromptRequest(
            system=system_prompt,
            user_message=user_message,
            model=self.model_name,
            cache_system=True,  # Enable prompt caching for cost optimization
            temperature=round_config["temperature"],  # Adaptive temperature
            max_tokens=round_config["max_tokens"],  # Adaptive token limit
            phase="deliberation",
            agent_type=f"persona_{persona_profile.code}",
        )

        # Use broker call for retry protection (not direct client call)
        llm_response_temp = await broker.call(request)
        response_text = llm_response_temp.content
        token_usage = llm_response_temp.token_usage
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Parse response (extract <thinking> and <contribution>)
        thinking, contribution = ResponseParser.parse_persona_response(response_text)

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
                # Only include facilitator_response if it's not None
                return [], [facilitator_response] if facilitator_response else []

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

        # Calculate and log consensus metrics (if round > 1)
        if round_number > 1:
            metrics = self._calculate_round_metrics(round_number)

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
        round_contributions = self.state.get_contributions_for_round(round_number)
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
        if round_number == 1 and self.state.current_sub_problem:
            problem_statement = self.state.current_sub_problem.goal

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
            self.state.round_summaries.append(response.content)

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

    def _calculate_round_metrics(self, round_number: int) -> dict[str, Any]:
        """Calculate convergence and consensus metrics for current round.

        Uses heuristic-based analysis for v1 (can be upgraded to embeddings in v2).

        Args:
            round_number: Current round number

        Returns:
            Dictionary with metrics:
            - convergence: 0-1 (higher = more agreement)
            - novelty: 0-1 (higher = more new ideas)
            - conflict: 0-1 (higher = more disagreement)
            - should_stop: bool (recommendation to stop deliberation)
            - stop_reason: str or None (explanation if should_stop is True)
        """
        if len(self.state.contributions) < 2:
            return {
                "convergence": 0.0,
                "novelty": 1.0,
                "conflict": 0.0,
                "should_stop": False,
                "stop_reason": None,
            }

        # Analyze recent contributions (last 2 rounds = ~6 contributions)
        recent_contributions = self.state.contributions[-6:]

        convergence = self._calculate_convergence(recent_contributions)
        novelty = self._calculate_novelty(recent_contributions)
        conflict = self._calculate_conflict(recent_contributions)

        # Decide if deliberation should stop early
        should_stop = False
        stop_reason = None

        if convergence > 0.85 and novelty < 0.30 and round_number > 5:
            should_stop = True
            stop_reason = "High convergence + low novelty"

        if conflict > 0.80 and round_number > 10:
            should_stop = True
            stop_reason = "Deadlock detected"

        return {
            "convergence": convergence,
            "novelty": novelty,
            "conflict": conflict,
            "should_stop": should_stop,
            "stop_reason": stop_reason,
        }

    def _calculate_convergence(self, contributions: list[ContributionMessage]) -> float:
        """Calculate convergence score (0-1, higher = more agreement).

        Uses keyword-based heuristic: count agreement vs. total words.
        """
        if not contributions:
            return 0.0

        agreement_keywords = [
            "agree",
            "yes",
            "correct",
            "exactly",
            "indeed",
            "aligned",
            "consensus",
            "support",
            "concur",
            "same",
            "similar",
        ]

        total_words = 0
        agreement_count = 0

        for contrib in contributions:
            words = contrib.content.lower().split()
            total_words += len(words)
            agreement_count += sum(
                1 for word in words if any(kw in word for kw in agreement_keywords)
            )

        if total_words == 0:
            return 0.0

        # Normalize to 0-1 range (assume 10% agreement words = full convergence)
        raw_score = agreement_count / total_words
        return min(raw_score * 10, 1.0)

    def _calculate_novelty(self, contributions: list[ContributionMessage]) -> float:
        """Calculate novelty score (0-1, higher = more new ideas).

        Uses simple heuristic: check for unique vs. repeated key phrases.
        """
        if not contributions:
            return 1.0

        # Extract key phrases (3+ char words, lowercase, deduplicated per contribution)
        all_phrases: list[str] = []
        for contrib in contributions:
            words = [w.lower() for w in contrib.content.split() if len(w) > 3]
            unique_words_in_contrib = list(set(words))
            all_phrases.extend(unique_words_in_contrib)

        if not all_phrases:
            return 0.5

        unique_phrases = len(set(all_phrases))
        total_phrases = len(all_phrases)

        # Novelty = ratio of unique to total phrases
        return unique_phrases / total_phrases

    def _calculate_conflict(self, contributions: list[ContributionMessage]) -> float:
        """Calculate conflict score (0-1, higher = more disagreement).

        Uses keyword-based heuristic: count disagreement vs. total words.
        """
        if not contributions:
            return 0.0

        disagreement_keywords = [
            "disagree",
            "no",
            "wrong",
            "incorrect",
            "however",
            "but",
            "concern",
            "risk",
            "problem",
            "issue",
            "challenge",
        ]

        total_words = 0
        disagreement_count = 0

        for contrib in contributions:
            words = contrib.content.lower().split()
            total_words += len(words)
            disagreement_count += sum(
                1 for word in words if any(kw in word for kw in disagreement_keywords)
            )

        if total_words == 0:
            return 0.0

        # Normalize to 0-1 range (assume 10% disagreement words = full conflict)
        raw_score = disagreement_count / total_words
        return min(raw_score * 10, 1.0)
