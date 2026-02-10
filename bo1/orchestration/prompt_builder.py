"""Prompt construction utilities for deliberation.

Handles all prompt building logic for persona contributions including:
- Hierarchical context (round summaries + recent contributions)
- Phase-based critical thinking protocols
- Regular contribution prompts
- Expert memory integration
"""

import logging
from typing import Any

from bo1.constants import GraphConfig
from bo1.data import get_persona_by_code
from bo1.graph.state import DeliberationGraphState
from bo1.models.state import ContributionMessage
from bo1.prompts import (
    BEST_EFFORT_PROMPT,
    compose_persona_contribution_prompt,
    compose_persona_prompt_hierarchical,
    get_round_phase_config,
)
from bo1.prompts.constraints import format_constraints_for_prompt

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Builds prompts for persona contributions.

    Handles the complex logic of selecting the appropriate prompt strategy
    based on available context (summaries, previous contributions, round phase).
    """

    @staticmethod
    def _should_inject_best_effort(state: DeliberationGraphState) -> bool:
        """Check if best effort prompt should be injected.

        Best effort mode is enabled when:
        - limited_context_mode is True (user provided partial clarification answers)
        - user_context_choice is "continue" (user chose to proceed with limited context)

        Args:
            state: Current deliberation state

        Returns:
            True if best effort prompt should be injected
        """
        limited_context_mode = state.get("limited_context_mode", False)
        user_context_choice = state.get("user_context_choice")

        should_inject = limited_context_mode and user_context_choice == "continue"

        if should_inject:
            logger.info(
                "Best effort mode enabled: limited_context_mode=%s, user_context_choice=%s",
                limited_context_mode,
                user_context_choice,
            )

        return should_inject

    @staticmethod
    def build_persona_prompt(
        persona_profile: Any,  # PersonaProfile type
        problem_statement: str,
        state: DeliberationGraphState,
        round_number: int,
        expert_memory: str | None = None,
        previous_contributions: list[ContributionMessage] | None = None,
    ) -> tuple[str, str]:
        """Build system and user prompts for persona contribution.

        Automatically selects between hierarchical prompts (with summaries) and
        regular prompts based on available context.

        Args:
            persona_profile: Persona to generate prompt for
            problem_statement: The problem/goal to address
            state: Current deliberation state
            round_number: Current round number (0-indexed)
            expert_memory: Optional cross-sub-problem memory
            previous_contributions: Previous round contributions for context

        Returns:
            Tuple of (system_prompt, user_message)

        Example:
            >>> builder = PromptBuilder()
            >>> system, user = builder.build_persona_prompt(
            ...     persona_profile=persona,
            ...     problem_statement="Should we migrate to cloud?",
            ...     state=state,
            ...     round_number=2,
            ... )
        """
        # Get full persona data
        persona_data = get_persona_by_code(persona_profile.code)
        if not persona_data:
            raise ValueError(f"Persona not found: {persona_profile.code}")

        # Get round configuration
        max_rounds = state.get("max_rounds", GraphConfig.MAX_ROUNDS_DEFAULT)
        round_config = get_round_phase_config(round_number + 1, max_rounds)  # +1 for 1-indexed

        logger.debug(
            f"Round {round_number + 1} phase: {round_config['phase']} "
            f"(temp={round_config['temperature']}, max_tokens={round_config['max_tokens']})"
        )

        # Check if we have round summaries for hierarchical context
        round_summaries = state.get("round_summaries", [])

        # Extract business context for style adaptation
        business_context = state.get("business_context")

        # Extract constraints from problem for prompt injection
        constraints_text = ""
        problem = state.get("problem")
        if problem:
            from bo1.models.problem import Constraint
            from bo1.utils.checkpoint_helpers import get_problem_attr

            raw_constraints = get_problem_attr(problem, "constraints", [])
            if raw_constraints:
                # Handle dict (checkpoint restore) vs Pydantic
                constraints = [
                    Constraint.model_validate(c) if isinstance(c, dict) else c
                    for c in raw_constraints
                ]
                constraints_text = format_constraints_for_prompt(constraints)

        if round_summaries and round_number > 1:
            # Use hierarchical prompts (summaries + recent contributions)
            system_prompt, user_message = PromptBuilder._build_hierarchical_prompt(
                persona_data=persona_data,
                persona_profile=persona_profile,
                problem_statement=problem_statement,
                state=state,
                round_number=round_number,
                round_summaries=round_summaries,
                previous_contributions=previous_contributions,
                expert_memory=expert_memory,
                round_config=round_config,
                constraints_text=constraints_text,
            )
        else:
            # Use regular prompts (no summaries yet or early rounds)
            system_prompt, user_message = PromptBuilder._build_regular_prompt(
                persona_data=persona_data,
                problem_statement=problem_statement,
                previous_contributions=previous_contributions,
                expert_memory=expert_memory,
                round_number=round_number,
                round_config=round_config,
                business_context=business_context,
                constraints_text=constraints_text,
            )

        # Inject best effort prompt if context is limited and user chose to continue
        if PromptBuilder._should_inject_best_effort(state):
            system_prompt = f"{BEST_EFFORT_PROMPT}\n\n{system_prompt}"
            logger.info(
                f"Injected BEST_EFFORT_PROMPT for {persona_profile.display_name} "
                f"(limited_context_mode=True, user_context_choice=continue)"
            )

        return system_prompt, user_message

    @staticmethod
    def _build_hierarchical_prompt(
        persona_data: dict[str, Any],
        persona_profile: Any,
        problem_statement: str,
        state: DeliberationGraphState,
        round_number: int,
        round_summaries: list[str],
        previous_contributions: list[ContributionMessage] | None,
        expert_memory: str | None,
        round_config: dict[str, Any],
        constraints_text: str = "",
    ) -> tuple[str, str]:
        """Build hierarchical prompt with round summaries and critical thinking protocol.

        Args:
            persona_data: Full persona data from personas.json
            persona_profile: Persona profile object
            problem_statement: The problem/goal
            state: Current deliberation state
            round_number: Current round (0-indexed)
            round_summaries: Previous round summaries
            previous_contributions: Recent contributions for context
            expert_memory: Cross-sub-problem memory
            round_config: Round configuration (phase, temperature, etc.)

        Returns:
            Tuple of (system_prompt, user_message)
        """
        # Get participant list
        personas = state.get("personas", [])
        participant_list = ", ".join([p.display_name for p in personas])

        # Get current round contributions (last round, for full detail)
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
            constraints_text=constraints_text,
        )

        # Add critical thinking protocol
        critical_thinking_section = PromptBuilder._build_critical_thinking_protocol(
            round_number, state
        )

        # Merge into system prompt
        system_prompt = base_system_prompt + "\n\n" + critical_thinking_section

        # User message is the speaker prompt
        user_message = expert_memory or round_config["directive"]

        logger.debug(
            f"Using hierarchical prompts with critical thinking: {len(round_summaries)} summaries, "
            f"{len(prev_round_contribs)} recent contributions, phase={round_config['phase']}"
        )

        return system_prompt, user_message

    @staticmethod
    def _build_regular_prompt(
        persona_data: dict[str, Any],
        problem_statement: str,
        previous_contributions: list[ContributionMessage] | None,
        expert_memory: str | None,
        round_number: int,
        round_config: dict[str, Any],
        business_context: dict[str, Any] | None = None,
        constraints_text: str = "",
    ) -> tuple[str, str]:
        """Build regular prompt for early rounds or when no summaries available.

        Args:
            persona_data: Full persona data from personas.json
            problem_statement: The problem/goal
            previous_contributions: Previous contributions for context
            expert_memory: Cross-sub-problem memory
            round_number: Current round (0-indexed)
            round_config: Round configuration (phase, temperature, etc.)
            business_context: Optional business context for style adaptation

        Returns:
            Tuple of (system_prompt, user_message)
        """
        # Convert previous contributions to dict format
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
            business_context=business_context,
            word_budget=round_config.get("word_budget", 200),
            constraints_text=constraints_text,
        )

        return system_prompt, user_message

    @staticmethod
    def _build_critical_thinking_protocol(round_number: int, state: DeliberationGraphState) -> str:
        """Build phase-specific critical thinking protocol.

        Args:
            round_number: Current round (0-indexed)
            state: Current deliberation state

        Returns:
            Critical thinking protocol text for injection into system prompt
        """
        # Note: get_round_phase_config could be used here for more dynamic phase handling
        # For now using simplified phase logic based on round number

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

        return critical_thinking_section
