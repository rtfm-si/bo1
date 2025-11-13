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
from bo1.models.state import ContributionMessage, DeliberationState
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

    def __init__(self, broker: PromptBroker | None = None, use_haiku: bool = True) -> None:
        """Initialize facilitator agent.

        Args:
            broker: LLM broker for making calls (creates default if not provided)
            use_haiku: Use Haiku for fast, cheap decisions (default: True)
        """
        self.broker = broker or PromptBroker()
        self.model = "haiku-4.5" if use_haiku else "sonnet-4.5"

    def _should_trigger_moderator(
        self, state: DeliberationState, round_number: int
    ) -> dict[str, str] | None:
        """Check if moderator intervention is needed.

        Returns:
            dict with "type" and "reason" if moderator needed, None otherwise
        """
        if len(state.contributions) < 4:
            return None  # Need at least 4 contributions to analyze

        recent = state.contributions[-6:]  # Last 2 rounds (~6 contributions)

        # Early rounds (1-4): Watch for premature consensus
        if round_number <= 4:
            if self._detect_premature_consensus(recent):
                return {
                    "type": "contrarian",
                    "reason": "Group converging too early without exploring alternatives",
                }

        # Middle rounds (5-7): Watch for unverified claims
        if 5 <= round_number <= 7:
            if self._detect_unverified_claims(recent):
                return {
                    "type": "skeptic",
                    "reason": "Claims made without evidence or verification",
                }

        # Late rounds (8+): Watch for negativity spiral
        if round_number >= 8:
            if self._detect_negativity_spiral(recent):
                return {
                    "type": "optimist",
                    "reason": "Discussion stuck in problems without exploring solutions",
                }

        # Any round: Watch for circular arguments
        if self._detect_circular_arguments(recent):
            return {
                "type": "contrarian",
                "reason": "Circular arguments detected, need fresh perspective",
            }

        return None

    def _detect_premature_consensus(self, contributions: list[ContributionMessage]) -> bool:
        """Detect if group is agreeing too quickly."""
        if len(contributions) < 4:
            return False

        # Count agreement keywords
        agreement_keywords = ["agree", "yes", "correct", "exactly", "indeed", "aligned", "same"]
        total_words = 0
        agreement_count = 0

        for contrib in contributions:
            words = contrib.content.lower().split()
            total_words += len(words)
            agreement_count += sum(
                1 for word in words if any(kw in word for kw in agreement_keywords)
            )

        if total_words == 0:
            return False

        # If >15% agreement words in early rounds = premature consensus
        agreement_ratio = agreement_count / total_words
        return agreement_ratio > 0.15

    def _detect_unverified_claims(self, contributions: list[ContributionMessage]) -> bool:
        """Detect claims without evidence."""
        claim_keywords = ["should", "must", "will definitely", "certainly", "always", "never"]
        evidence_keywords = [
            "because",
            "data shows",
            "research indicates",
            "according to",
            "evidence",
            "study",
        ]

        for contrib in contributions:
            text = contrib.content.lower()
            has_claims = sum(1 for kw in claim_keywords if kw in text)
            has_evidence = sum(1 for kw in evidence_keywords if kw in text)

            # If 3+ claims but no evidence markers = red flag
            if has_claims >= 3 and has_evidence == 0:
                return True

        return False

    def _detect_negativity_spiral(self, contributions: list[ContributionMessage]) -> bool:
        """Detect if discussion stuck in problems."""
        negative_keywords = [
            "won't work",
            "impossible",
            "can't",
            "too risky",
            "fail",
            "problem",
            "issue",
        ]
        positive_keywords = [
            "could",
            "might",
            "opportunity",
            "solution",
            "approach",
            "possible",
            "potential",
        ]

        negative_count = 0
        positive_count = 0

        for contrib in contributions:
            text = contrib.content.lower()
            negative_count += sum(1 for kw in negative_keywords if kw in text)
            positive_count += sum(1 for kw in positive_keywords if kw in text)

        # If 3x more negative than positive = spiral
        if positive_count == 0:
            return negative_count > 5

        return negative_count > 3 * positive_count

    def _detect_circular_arguments(self, contributions: list[ContributionMessage]) -> bool:
        """Detect if same arguments repeating."""
        if len(contributions) < 4:
            return False

        # Extract key phrases (4+ char words, deduplicated per contribution)
        all_phrases: list[str] = []
        for contrib in contributions:
            words = [w.lower() for w in contrib.content.split() if len(w) >= 4]
            unique_in_contrib = list(set(words))
            all_phrases.extend(unique_in_contrib)

        if not all_phrases:
            return False

        unique_phrases = len(set(all_phrases))
        total_phrases = len(all_phrases)

        # If <40% are unique = lots of repetition = circular
        return (unique_phrases / total_phrases) < 0.40

    def _check_research_needed(self, state: DeliberationState) -> dict[str, str] | None:
        """Check if research/information is needed.

        Returns:
            dict with "query" and "reason" if research needed, None otherwise
        """
        if len(state.contributions) < 2:
            return None

        recent = state.contributions[-3:]  # Last round

        # Look for questions or information gaps
        question_patterns = [
            "what is",
            "what are",
            "how much",
            "how many",
            "do we know",
            "unclear",
            "uncertain",
            "need data",
            "need information",
            "need research",
            "don't have data",
            "missing information",
        ]

        for contrib in recent:
            text = contrib.content.lower()
            for pattern in question_patterns:
                if pattern in text:
                    # Extract the sentence containing the pattern
                    sentences = text.split(".")
                    for sentence in sentences:
                        if pattern in sentence:
                            query = sentence.strip()[:200]  # Limit to 200 chars
                            return {
                                "query": query,
                                "reason": f"{contrib.persona_name} raised: {query}",
                            }

        return None

    async def decide_next_action(
        self, state: DeliberationState, round_number: int, max_rounds: int
    ) -> tuple[FacilitatorDecision, LLMResponse | None]:
        """Decide what should happen next in the deliberation.

        Args:
            state: Current deliberation state
            round_number: Current round number (1-indexed)
            max_rounds: Maximum rounds allowed based on complexity

        Returns:
            Tuple of (decision, llm_response)
        """
        logger.info(f"Facilitator deciding next action for round {round_number}/{max_rounds}")

        # Check for research needs FIRST (fastest check)
        research_needed = self._check_research_needed(state)

        if research_needed:
            logger.info(f"🔍 Research needed: {research_needed['query'][:100]}...")

            return (
                FacilitatorDecision(
                    action="research",
                    reasoning=research_needed["reason"],
                    research_query=research_needed["query"],
                ),
                None,  # Skip LLM call
            )

        # Check if moderator should intervene BEFORE calling LLM (saves time and cost)
        moderator_trigger = self._should_trigger_moderator(state, round_number)

        if moderator_trigger:
            logger.info(f"🎭 Auto-triggering {moderator_trigger['type']} moderator")
            logger.info(f"   Reason: {moderator_trigger['reason']}")

            # Cast moderator_type to correct Literal type
            mod_type = moderator_trigger["type"]
            if mod_type not in ("contrarian", "skeptic", "optimist"):
                mod_type = "contrarian"  # Default fallback

            return (
                FacilitatorDecision(
                    action="moderator",
                    reasoning=moderator_trigger["reason"],
                    moderator_type=mod_type,  # type: ignore[arg-type]
                    moderator_focus=moderator_trigger["reason"],
                ),
                None,  # Skip LLM call, return None for response
            )

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
            max_tokens=800,  # Reduced from 2048 - facilitator doesn't need long responses
            phase="facilitator_decision",
            agent_type="facilitator",
            model=self.model,  # Use configured model (Haiku by default)
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
                (
                    p.display_name
                    for p in state.selected_personas
                    if p.code == decision.next_speaker
                ),
                decision.next_speaker,
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
