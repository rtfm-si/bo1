"""Facilitator agent that orchestrates multi-round deliberation.

The facilitator:
- Guides discussion through productive phases
- Decides when to continue, transition to voting, invoke research, or trigger moderators
- Synthesizes contributions and identifies patterns
- Maintains neutral stance while ensuring quality dialogue
"""

import logging
from typing import Literal

from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.response import LLMResponse
from bo1.models.state import DeliberationState
from bo1.prompts.reusable_prompts import compose_facilitator_prompt

logger = logging.getLogger(__name__)

FacilitatorAction = Literal["continue", "vote", "research", "moderator"]


class FacilitatorDecision:
    """Parsed decision from facilitator."""

    def __init__(
        self,
        action: FacilitatorAction,
        reasoning: str,
        # For "continue" action
        next_speaker: str | None = None,
        speaker_prompt: str | None = None,
        # For "moderator" action
        moderator_type: Literal["contrarian", "skeptic", "optimist"] | None = None,
        moderator_focus: str | None = None,
        # For "research" action
        research_query: str | None = None,
        # For "vote" action (transition)
        phase_summary: str | None = None,
    ) -> None:
        """Initialize facilitator decision."""
        self.action = action
        self.reasoning = reasoning
        self.next_speaker = next_speaker
        self.speaker_prompt = speaker_prompt
        self.moderator_type = moderator_type
        self.moderator_focus = moderator_focus
        self.research_query = research_query
        self.phase_summary = phase_summary


class FacilitatorAgent:
    """Orchestrates multi-round deliberation by deciding next actions."""

    def __init__(self, broker: PromptBroker | None = None) -> None:
        """Initialize facilitator agent.

        Args:
            broker: LLM broker for making calls (creates default if not provided)
        """
        self.broker = broker or PromptBroker()

    async def decide_next_action(
        self, state: DeliberationState, round_number: int, max_rounds: int
    ) -> tuple[FacilitatorDecision, LLMResponse]:
        """Decide what should happen next in the deliberation.

        Args:
            state: Current deliberation state
            round_number: Current round number (1-indexed)
            max_rounds: Maximum rounds allowed based on complexity

        Returns:
            Tuple of (decision, llm_response)
        """
        logger.info(f"Facilitator deciding next action for round {round_number}/{max_rounds}")

        # Build discussion history
        discussion_history = self._format_discussion_history(state)

        # Build phase objectives
        phase_objectives = self._get_phase_objectives(state.phase, round_number, max_rounds)

        # Compose facilitator prompt
        system_prompt = compose_facilitator_prompt(
            current_phase=state.phase,
            discussion_history=discussion_history,
            phase_objectives=phase_objectives,
        )

        # Build user message
        user_message = f"""Current round: {round_number} of {max_rounds}
Total contributions so far: {len(state.contributions)}
Personas participating: {", ".join([p.code for p in state.selected_personas])}

Analyze the discussion and decide the next action."""

        # Call LLM
        request = PromptRequest(
            system=system_prompt,
            user_message=user_message,
            temperature=1.0,
            max_tokens=2048,
            phase="facilitator_decision",
            agent_type="facilitator",
        )

        response = await self.broker.call(request)

        # Parse decision from response
        decision = self._parse_decision(response.content, state)

        logger.info(f"Facilitator decision: {decision.action}")

        # Log detailed reasoning in debug mode
        if decision.reasoning:
            logger.debug(f"  Reasoning: {decision.reasoning[:200]}...")

        if decision.action == "continue" and decision.next_speaker:
            speaker_name = next(
                (p.display_name for p in state.selected_personas if p.code == decision.next_speaker),
                decision.next_speaker
            )
            logger.info(f"  Next speaker: {speaker_name} ({decision.next_speaker})")
            if decision.speaker_prompt:
                logger.debug(f"  Focus: {decision.speaker_prompt}")
        elif decision.action == "moderator" and decision.moderator_type:
            logger.info(f"  Moderator type: {decision.moderator_type}")
            if decision.moderator_focus:
                logger.debug(f"  Focus: {decision.moderator_focus}")
        elif decision.action == "vote":
            logger.info("  Transition to voting phase")
            if decision.phase_summary:
                logger.debug(f"  Summary: {decision.phase_summary[:150]}...")

        return decision, response

    def _format_discussion_history(self, state: DeliberationState) -> str:
        """Format discussion history for facilitator context."""
        if not state.contributions:
            return "No contributions yet (initial round)."

        lines = []
        for msg in state.contributions:
            lines.append(f"[Round {msg.round_number}] {msg.persona_code}:")
            lines.append(msg.content)
            lines.append("")

        return "\n".join(lines)

    def _get_phase_objectives(self, phase: str, round_number: int, max_rounds: int) -> str:
        """Get objectives for current phase."""
        if phase == "initial":
            return """INITIAL ROUND OBJECTIVES:
- Each persona provides their initial perspective
- Identify key themes and concerns
- Surface different viewpoints
- Set foundation for deeper discussion"""

        if phase == "discussion":
            progress_pct = (round_number / max_rounds) * 100
            remaining = max_rounds - round_number

            return f"""DISCUSSION PHASE OBJECTIVES:
- Build on initial contributions
- Explore disagreements constructively
- Deepen analysis of key factors
- Work toward consensus or clarify tradeoffs

Progress: Round {round_number}/{max_rounds} ({progress_pct:.0f}%)
Remaining rounds: {remaining}

Consider:
- Is there sufficient depth to reach a quality recommendation?
- Are there critical perspectives not yet heard?
- Are we converging toward consensus or clarifying tradeoffs?
- Should we continue, bring in a moderator, or move to voting?"""

        return f"Phase: {phase} (objectives not defined)"

    def _parse_decision(self, content: str, state: DeliberationState) -> FacilitatorDecision:
        """Parse facilitator's decision from response content.

        This is a simple parser - looks for key patterns in the response.
        In v2, we could use structured output (JSON schema).
        """
        content_lower = content.lower()

        # Detect action type
        action: FacilitatorAction

        if "option a" in content_lower or "continue discussion" in content_lower:
            action = "continue"
        elif (
            "option b" in content_lower or "transition" in content_lower or "vote" in content_lower
        ):
            action = "vote"
        elif "option c" in content_lower or "research" in content_lower:
            action = "research"
        elif "option d" in content_lower or "moderator" in content_lower:
            action = "moderator"
        else:
            # Default to continue if unclear
            logger.warning("Could not parse facilitator action clearly, defaulting to 'continue'")
            action = "continue"

        # Extract reasoning (look for content in <thinking> or <decision> tags)
        reasoning = self._extract_tag_content(content, "thinking") or content[:500]

        # Parse based on action type
        if action == "continue":
            next_speaker = self._extract_next_speaker(content, state)
            speaker_prompt = self._extract_speaker_prompt(content)
            return FacilitatorDecision(
                action=action,
                reasoning=reasoning,
                next_speaker=next_speaker,
                speaker_prompt=speaker_prompt,
            )

        if action == "moderator":
            moderator_type = self._extract_moderator_type(content)
            moderator_focus = self._extract_moderator_focus(content)
            return FacilitatorDecision(
                action=action,
                reasoning=reasoning,
                moderator_type=moderator_type,
                moderator_focus=moderator_focus,
            )

        if action == "research":
            research_query = self._extract_research_query(content)
            return FacilitatorDecision(
                action=action, reasoning=reasoning, research_query=research_query
            )

        # action == "vote"
        phase_summary = self._extract_phase_summary(content)
        return FacilitatorDecision(action=action, reasoning=reasoning, phase_summary=phase_summary)

    def _extract_tag_content(self, content: str, tag: str) -> str | None:
        """Extract content between XML tags."""
        start_tag = f"<{tag}>"
        end_tag = f"</{tag}>"

        start_idx = content.find(start_tag)
        if start_idx == -1:
            return None

        end_idx = content.find(end_tag, start_idx)
        if end_idx == -1:
            return None

        return content[start_idx + len(start_tag) : end_idx].strip()

    def _extract_next_speaker(self, content: str, state: DeliberationState) -> str | None:
        """Extract next speaker persona code from facilitator response."""
        # Look for persona codes in the content
        for persona in state.selected_personas:
            if persona.code in content or persona.code.replace("_", " ") in content.lower():
                return persona.code

        # Default to first persona if unclear
        if state.selected_personas:
            logger.warning(
                f"Could not identify next speaker, defaulting to {state.selected_personas[0].code}"
            )
            return state.selected_personas[0].code

        return None

    def _extract_speaker_prompt(self, content: str) -> str | None:
        """Extract specific prompt for next speaker."""
        # Look for "Prompt:" or "Focus:" sections
        for marker in ["prompt:", "focus:", "question:"]:
            idx = content.lower().find(marker)
            if idx != -1:
                # Extract until next line break or end
                snippet = content[idx + len(marker) : idx + 300].split("\n")[0].strip()
                if snippet:
                    return snippet

        return None

    def _extract_moderator_type(
        self, content: str
    ) -> Literal["contrarian", "skeptic", "optimist"] | None:
        """Extract moderator type from content."""
        content_lower = content.lower()
        if "contrarian" in content_lower:
            return "contrarian"
        if "skeptic" in content_lower:
            return "skeptic"
        if "optimist" in content_lower:
            return "optimist"
        return "contrarian"  # Default

    def _extract_moderator_focus(self, content: str) -> str | None:
        """Extract what moderator should focus on."""
        for marker in ["focus:", "address:", "challenge:"]:
            idx = content.lower().find(marker)
            if idx != -1:
                snippet = content[idx + len(marker) : idx + 300].split("\n")[0].strip()
                if snippet:
                    return snippet
        return None

    def _extract_research_query(self, content: str) -> str | None:
        """Extract research query from content."""
        for marker in ["query:", "question:", "information needed:"]:
            idx = content.lower().find(marker)
            if idx != -1:
                snippet = content[idx + len(marker) : idx + 300].split("\n")[0].strip()
                if snippet:
                    return snippet
        return None

    def _extract_phase_summary(self, content: str) -> str | None:
        """Extract phase summary when transitioning."""
        summary = self._extract_tag_content(content, "summary")
        if summary:
            return summary

        # Look for "Summary:" marker
        idx = content.lower().find("summary:")
        if idx != -1:
            snippet = content[idx + 8 : idx + 500].split("\n\n")[0].strip()
            if snippet:
                return snippet

        return None
