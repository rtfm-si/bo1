"""Facilitator agent that orchestrates multi-round deliberation.

The facilitator:
- Guides discussion through productive phases
- Decides when to continue, transition to voting, invoke research, or trigger moderators
- Synthesizes contributions and identifies patterns
- Maintains neutral stance while ensuring quality dialogue
"""

import logging
from typing import Any, Literal

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

    async def synthesize_deliberation(
        self,
        state: DeliberationState,
        votes: list[Any],
        vote_aggregation: Any,
    ) -> tuple[str, LLMResponse]:
        """Synthesize the full deliberation into a comprehensive report.

        Args:
            state: Current deliberation state
            votes: List of Vote objects
            vote_aggregation: VoteAggregation object

        Returns:
            Tuple of (synthesis_report, LLMResponse)
        """
        from bo1.prompts.reusable_prompts import SYNTHESIS_PROMPT_TEMPLATE

        logger.info("Generating synthesis report")

        # Build full deliberation history
        all_contributions_and_votes = self._format_full_deliberation(state, votes)

        # Compose synthesis prompt
        synthesis_prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
            problem_statement=state.problem.description,
            all_contributions_and_votes=all_contributions_and_votes,
        )

        # Request synthesis from Sonnet (needs reasoning capability)
        request = PromptRequest(
            system=synthesis_prompt,
            user_message="Generate the comprehensive synthesis report.",
            temperature=0.7,
            max_tokens=4096,
            phase="synthesis",
            agent_type="facilitator_synthesis",
        )

        response = await self.broker.call(request)
        synthesis_report = self._extract_tag_content(response.content, "synthesis_report")

        if not synthesis_report:
            # Fallback: use full response if no tags
            logger.warning(
                f"⚠️ FALLBACK: Could not extract <synthesis_report> tag from synthesis response. "
                f"Using full response content instead. This may include thinking tags and other metadata. "
                f"Response preview: {response.content[:200]}..."
            )
            synthesis_report = response.content
        else:
            logger.info("✓ Successfully extracted structured synthesis report")

        logger.info(f"Generated synthesis report ({len(synthesis_report)} chars)")

        return synthesis_report, response

    def _format_full_deliberation(self, state: DeliberationState, votes: list[Any]) -> str:
        """Format full deliberation history including contributions and votes.

        Args:
            state: Current deliberation state
            votes: List of Vote objects

        Returns:
            Formatted string
        """
        lines = []

        # Add all contributions
        lines.append("DELIBERATION HISTORY:")
        lines.append("")

        for msg in state.contributions:
            lines.append(f"--- {msg.persona_name} (Round {msg.round_number}) ---")
            lines.append(msg.content)
            lines.append("")

        # Add votes
        lines.append("FINAL VOTES:")
        lines.append("")

        for vote in votes:
            lines.append(f"--- {vote.persona_name} ---")
            lines.append(f"Decision: {vote.decision.value}")
            lines.append(f"Reasoning: {vote.reasoning}")
            if vote.conditions:
                lines.append(f"Conditions: {', '.join(vote.conditions)}")
            lines.append("")

        return "\n".join(lines)

    async def validate_synthesis_quality(
        self,
        synthesis_report: str,
        state: DeliberationState,
        votes: list[Any],
    ) -> tuple[bool, str | None, LLMResponse]:
        """Validate synthesis quality using AI (Haiku).

        Checks:
        - Are all dissenting views included?
        - Are conditions clear?
        - Is recommendation actionable?
        - Are risks acknowledged?

        Args:
            synthesis_report: The generated synthesis
            state: Deliberation state
            votes: List of votes

        Returns:
            Tuple of (is_valid, feedback_for_revision, LLMResponse)
        """
        logger.info("Validating synthesis quality with AI (Haiku)")

        # Collect dissenting votes
        dissenting_votes = [v for v in votes if v.decision.value in ["no", "abstain"]]
        conditional_votes = [v for v in votes if v.decision.value == "conditional"]

        # Format for validation
        dissenting_summary = "\n".join(
            [f"- {v.persona_name}: {v.reasoning[:200]}..." for v in dissenting_votes]
        )
        conditional_summary = "\n".join(
            [f"- {v.persona_name}: {', '.join(v.conditions[:3])}" for v in conditional_votes]
        )

        system_prompt = """You are a synthesis quality validator.

Your task: Check if a synthesis report is comprehensive and actionable.

Output ONLY valid JSON in this exact format:
{
  "is_valid": true | false,
  "missing_elements": ["element 1", "element 2", ...],
  "quality_score": 0.0-1.0,
  "revision_guidance": "specific feedback for improvement" | null
}"""

        user_message = f"""Validate this synthesis report:

<synthesis_report>
{synthesis_report[:2000]}...
</synthesis_report>

<dissenting_views_expected>
{dissenting_summary if dissenting_summary else "None"}
</dissenting_views_expected>

<conditional_votes_expected>
{conditional_summary if conditional_summary else "None"}
</conditional_votes_expected>

Check:
1. Are all dissenting views ({len(dissenting_votes)}) included and explained?
2. Are critical conditions ({len([c for v in conditional_votes for c in v.conditions])}) clearly stated?
3. Is the recommendation specific and actionable (not vague)?
4. Are risks and implementation challenges addressed?

Output JSON only."""

        request = PromptRequest(
            system=system_prompt,
            user_message=user_message,
            prefill="{",
            temperature=0.3,
            max_tokens=1000,
            phase="synthesis_validation",
            agent_type="synthesis_validator",
        )

        response = await self.broker.call(request)

        try:
            # Parse validation result
            json_content = "{" + response.content
            import json

            validation_data = json.loads(json_content)

            is_valid = validation_data.get("is_valid", True)
            quality_score = validation_data.get("quality_score", 1.0)
            revision_guidance = validation_data.get("revision_guidance")

            if is_valid and quality_score >= 0.7:
                logger.info(f"Synthesis validation PASSED (quality: {quality_score:.2f})")
                return True, None, response
            else:
                logger.warning(
                    f"Synthesis validation FAILED (quality: {quality_score:.2f}), "
                    f"missing: {validation_data.get('missing_elements', [])}"
                )
                return False, revision_guidance, response

        except Exception as e:
            logger.error(
                f"⚠️ FALLBACK: Synthesis validation parsing FAILED. Assuming synthesis is valid "
                f"(graceful degradation). Error: {e}. Response: {response.content[:200]}..."
            )
            # Assume valid on parse failure (graceful degradation)
            return True, None, response

    async def revise_synthesis(
        self,
        original_synthesis: str,
        feedback: str,
        state: DeliberationState,
        votes: list[Any],
    ) -> tuple[str, LLMResponse]:
        """Revise synthesis based on quality feedback.

        Args:
            original_synthesis: Original synthesis report
            feedback: Feedback from validation
            state: Deliberation state
            votes: List of votes

        Returns:
            Tuple of (revised_synthesis, LLMResponse)
        """
        logger.info("Revising synthesis based on feedback")

        system_prompt = """You are the Facilitator revising a synthesis report.

Your task: Improve the synthesis by addressing specific quality issues.

Output the revised <synthesis_report> with all required sections."""

        user_message = f"""Revise this synthesis report to address the feedback:

<original_synthesis>
{original_synthesis}
</original_synthesis>

<quality_feedback>
{feedback}
</quality_feedback>

<problem_statement>
{state.problem.description}
</problem_statement>

Ensure the revised report:
1. Includes ALL dissenting views with substantive explanation
2. Clearly states ALL critical conditions
3. Provides specific, actionable recommendations
4. Addresses risks and implementation challenges

Output the complete revised <synthesis_report>...</synthesis_report>."""

        request = PromptRequest(
            system=system_prompt,
            user_message=user_message,
            temperature=0.7,
            max_tokens=4096,
            phase="synthesis_revision",
            agent_type="facilitator_synthesis",
        )

        response = await self.broker.call(request)
        revised_synthesis = self._extract_tag_content(response.content, "synthesis_report")

        if not revised_synthesis:
            logger.warning(
                f"⚠️ FALLBACK: Could not extract <synthesis_report> tag from REVISED synthesis response. "
                f"Using full response content instead. Response preview: {response.content[:200]}..."
            )
            revised_synthesis = response.content
        else:
            logger.info("✓ Successfully extracted structured revised synthesis report")

        logger.info(f"Generated revised synthesis ({len(revised_synthesis)} chars)")

        return revised_synthesis, response
