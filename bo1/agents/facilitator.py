"""Facilitator agent that orchestrates multi-round deliberation.

The facilitator:
- Guides discussion through productive phases
- Decides when to continue, transition to voting, invoke research, or trigger moderators
- Synthesizes contributions and identifies patterns
- Maintains neutral stance while ensuring quality dialogue
"""

import logging
from typing import Any, Literal

from bo1.agents.base import BaseAgent
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.response import LLMResponse
from bo1.llm.response_parser import ResponseParser
from bo1.models.state import DeliberationState
from bo1.prompts.reusable_prompts import compose_facilitator_prompt
from bo1.utils.deliberation_analysis import DeliberationAnalyzer
from bo1.utils.json_parsing import parse_json_with_fallback
from bo1.utils.logging_helpers import LogHelper
from bo1.utils.xml_parsing import extract_xml_tag

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


class FacilitatorAgent(BaseAgent):
    """Orchestrates multi-round deliberation by deciding next actions."""

    def __init__(self, broker: PromptBroker | None = None, use_haiku: bool = True) -> None:
        """Initialize facilitator agent.

        Args:
            broker: LLM broker for making calls (creates default if not provided)
            use_haiku: Use Haiku for fast, cheap decisions (default: True)
        """
        # Facilitator allows model override via use_haiku parameter
        model = "haiku-4.5" if use_haiku else "sonnet-4.5"
        super().__init__(broker=broker, model=model)

    def get_default_model(self) -> str:
        """Return default model for facilitator (Haiku for speed/cost)."""
        return "haiku-4.5"

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
            if DeliberationAnalyzer.detect_premature_consensus(recent):
                return {
                    "type": "contrarian",
                    "reason": "Group converging too early without exploring alternatives",
                }

        # Middle rounds (5-7): Watch for unverified claims
        if 5 <= round_number <= 7:
            if DeliberationAnalyzer.detect_unverified_claims(recent):
                return {
                    "type": "skeptic",
                    "reason": "Claims made without evidence or verification",
                }

        # Late rounds (8+): Watch for negativity spiral
        if round_number >= 8:
            if DeliberationAnalyzer.detect_negativity_spiral(recent):
                return {
                    "type": "optimist",
                    "reason": "Discussion stuck in problems without exploring solutions",
                }

        # Any round: Watch for circular arguments
        if DeliberationAnalyzer.detect_circular_arguments(recent):
            return {
                "type": "contrarian",
                "reason": "Circular arguments detected, need fresh perspective",
            }

        return None

    def _check_research_needed(self, state: DeliberationState) -> dict[str, str] | None:
        """Check if research/information is needed.

        Delegates to DeliberationAnalyzer for pattern detection.

        Returns:
            dict with "query" and "reason" if research needed, None otherwise
        """
        return DeliberationAnalyzer.check_research_needed(state)

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
        parsed = ResponseParser.parse_facilitator_decision(response.content, state)
        decision = FacilitatorDecision(**parsed)

        # Log decision details using LogHelper
        details = {}
        if decision.next_speaker:
            details["next_speaker"] = decision.next_speaker
        if decision.speaker_prompt:
            details["focus"] = decision.speaker_prompt
        if decision.moderator_type:
            details["moderator_type"] = decision.moderator_type
        if decision.moderator_focus:
            details["moderator_focus"] = decision.moderator_focus

        LogHelper.log_decision(
            logger,
            agent_type="facilitator",
            decision=decision.action,
            reasoning=decision.reasoning,
            details=details if details else None,
        )

        return decision, response

    def _format_discussion_history(self, state: DeliberationState) -> str:
        """Format discussion history for facilitator context."""
        if not state.contributions:
            return "No contributions yet (initial round)."

        # Add persona code prefix for facilitator context
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
        synthesis_report = extract_xml_tag(response.content, "synthesis_report")

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

        # Add all contributions using state method
        lines.append("DELIBERATION HISTORY:")
        lines.append("")
        lines.append(state.format_discussion_history())

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
            # Parse validation result using utility

            json_content = "{" + response.content
            validation_data, parsing_errors = parse_json_with_fallback(
                content=json_content,
                prefill="",  # Already prepended above
                context="synthesis validation",
                logger=logger,
            )

            if validation_data is None:
                raise ValueError(f"Could not parse JSON from response. Errors: {parsing_errors}")

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
            LogHelper.log_fallback_used(
                logger,
                operation="Synthesis validation parsing",
                reason="Failed to parse JSON response",
                fallback_action="assuming synthesis is valid (graceful degradation)",
                error=e,
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
        revised_synthesis = extract_xml_tag(response.content, "synthesis_report")

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
