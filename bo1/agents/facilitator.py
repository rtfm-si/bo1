"""Facilitator agent that orchestrates multi-round deliberation.

The facilitator:
- Guides discussion through productive phases
- Decides when to continue, transition to voting, invoke research, or trigger moderators
- Synthesizes contributions and identifies patterns
- Maintains neutral stance while ensuring quality dialogue
"""

import logging
from dataclasses import dataclass
from typing import Any, Literal

from bo1.agents.base import BaseAgent
from bo1.graph.state import DeliberationGraphState
from bo1.llm.broker import PromptBroker
from bo1.llm.response import LLMResponse
from bo1.llm.response_parser import ResponseParser
from bo1.prompts import compose_facilitator_prompt
from bo1.state.discussion_formatter import format_discussion_history
from bo1.utils.deliberation_analysis import DeliberationAnalyzer
from bo1.utils.error_logger import ErrorLogger
from bo1.utils.json_parsing import parse_json_with_fallback
from bo1.utils.logging_helpers import LogHelper
from bo1.utils.xml_parsing import extract_xml_tag_with_fallback

logger = logging.getLogger(__name__)

FacilitatorAction = Literal["continue", "vote", "research", "moderator", "clarify", "analyze_data"]

# Valid action values as a set for validation
VALID_FACILITATOR_ACTIONS: set[str] = {
    "continue",
    "vote",
    "research",
    "moderator",
    "clarify",
    "analyze_data",
}


def is_valid_facilitator_action(action: str) -> bool:
    """Check if an action string is a valid FacilitatorAction.

    Args:
        action: Action string to validate

    Returns:
        True if action is valid, False otherwise
    """
    return action.lower().strip() in VALID_FACILITATOR_ACTIONS


@dataclass
class FacilitatorDecision:
    """Parsed decision from facilitator.

    NEW PARALLEL ARCHITECTURE: Added fields for phase-based multi-expert selection.
    """

    action: FacilitatorAction
    reasoning: str

    # For "continue" action (LEGACY - kept for backward compatibility)
    next_speaker: str | None = None  # DEPRECATED in parallel mode
    speaker_prompt: str | None = None

    # NEW PARALLEL ARCHITECTURE: Phase and expert count selection
    next_phase: str | None = None  # "exploration", "challenge", "convergence"
    num_experts: int | None = None  # How many experts for next round (2-5)

    # For "moderator" action
    moderator_type: Literal["contrarian", "skeptic", "optimist"] | None = None
    moderator_focus: str | None = None
    # For "research" action
    research_query: str | None = None
    # For "analyze_data" action
    dataset_id: str | None = None
    analysis_questions: list[str] | None = None
    # For "vote" action (transition)
    phase_summary: str | None = None
    # For "clarify" action
    clarification_question: str | None = None
    clarification_reason: str | None = None


class FacilitatorAgent(BaseAgent):
    """Orchestrates multi-round deliberation by deciding next actions."""

    def __init__(self, broker: PromptBroker | None = None, use_haiku: bool = True) -> None:
        """Initialize facilitator agent.

        Args:
            broker: LLM broker for making calls (creates default if not provided)
            use_haiku: Use Haiku for fast, cheap decisions (default: True)
        """
        # Facilitator allows model override via use_haiku parameter
        model = "haiku" if use_haiku else "sonnet"
        super().__init__(broker=broker, model=model)

    def get_default_model(self) -> str:
        """Return default model for facilitator (Haiku for speed/cost)."""
        return "haiku"

    def _should_trigger_moderator(
        self, state: DeliberationGraphState, round_number: int
    ) -> dict[str, str] | None:
        """Check if moderator intervention is needed for premature consensus.

        TARGETED USE: Only triggers for unanimous agreement BEFORE round 3.
        This prevents groupthink in early deliberation without adding noise
        to mature discussions.

        Returns:
            dict with "type" and "reason" if moderator needed, None otherwise
        """
        # ONLY check for premature consensus in rounds 1-2 (before round 3)
        if round_number >= 3:
            return None  # No moderator after round 2

        contributions = state.get("contributions", [])
        if len(contributions) < 4:
            return None  # Need at least 4 contributions to analyze

        recent = contributions[-6:]  # Last 2 rounds (~6 contributions)

        # Check for premature consensus ONLY
        if DeliberationAnalyzer.detect_premature_consensus(recent):
            return {
                "type": "contrarian",
                "reason": "Group converging too early without exploring alternatives (round 1-2)",
            }

        return None

    def _check_research_needed(self, state: DeliberationGraphState) -> dict[str, str] | None:
        """Check if research/information is needed.

        Delegates to DeliberationAnalyzer for pattern detection.
        Respects research loop prevention counter to avoid infinite research loops.

        Returns:
            dict with "query" and "reason" if research needed, None otherwise
        """
        # RESEARCH LOOP PREVENTION (Option D+E Hybrid - Phase 7)
        # Skip research if we've had consecutive research without improvement
        consecutive_without_improvement = state.get("consecutive_research_without_improvement", 0)
        if consecutive_without_improvement >= 2:
            logger.warning(
                f"🔄 Research loop prevented: {consecutive_without_improvement} consecutive "
                f"research queries without improvement. Forcing continuation with available context."
            )
            return None

        # Also skip research if we're in best effort mode (user chose to continue with limited context)
        limited_context_mode = state.get("limited_context_mode", False)
        user_context_choice = state.get("user_context_choice")
        if limited_context_mode and user_context_choice == "continue":
            logger.info(
                "⏭️ Skipping research check: user chose to continue with limited context (best effort mode)"
            )
            return None

        return DeliberationAnalyzer.check_research_needed(state)

    def _count_contributions(self, contributions: list[Any]) -> dict[str, int]:
        """Count contributions per persona.

        Args:
            contributions: List of contribution messages

        Returns:
            Dictionary mapping persona_code to contribution count
        """
        counts: dict[str, int] = {}
        for contrib in contributions:
            persona_code = contrib.persona_code
            counts[persona_code] = counts.get(persona_code, 0) + 1
        return counts

    def _check_rotation_limits(self, state: DeliberationGraphState) -> dict[str, str] | None:
        """Check if rotation rules require overriding facilitator decision.

        Issue #5 fix: Enforces hard rotation limits to prevent expert dominance.

        NEW PARALLEL ARCHITECTURE: Updated rules for multi-expert-per-round model.

        Rules (UPDATED for parallel):
        1. No expert in >50% of recent 4 rounds (was: 3 consecutive contributions)
        2. Each expert 15-25% of total contributions (was: no more than 40%)
        3. Every expert must contribute at least once per 3 rounds (was: once per 2 rounds)

        Args:
            state: Current deliberation state

        Returns:
            dict with rotation override info if limits exceeded, None otherwise
        """
        contributions = state.get("contributions", [])
        personas = state.get("personas", [])

        if not contributions or not personas:
            return None

        # Rule 1 (UPDATED for parallel): No expert in >50% of recent 4 rounds
        # In parallel model, multiple experts contribute per round, so we check round participation
        recent_round_limit = 4
        max_round_participation_rate = 0.50  # 50% of recent rounds

        # Get recent rounds (last 4 rounds worth of contributions)
        # Estimate: avg 3 contributions per round
        recent_contributions = contributions[-12:]  # Last ~4 rounds

        if len(recent_contributions) >= 6:  # At least 2 rounds of data
            contribution_counts_recent = self._count_contributions(recent_contributions)

            for persona_code, recent_count in contribution_counts_recent.items():
                # Estimate rounds participated (contributions / avg 3 per round)
                estimated_rounds_participated = recent_count / 3.0
                estimated_total_recent_rounds = len(recent_contributions) / 3.0

                if estimated_total_recent_rounds > 0:
                    participation_rate = (
                        estimated_rounds_participated / estimated_total_recent_rounds
                    )

                    if participation_rate > max_round_participation_rate:
                        # This expert is in too many recent rounds
                        contribution_counts_all = self._count_contributions(contributions)
                        other_experts = [
                            p.code
                            for p in personas
                            if contribution_counts_recent.get(p.code, 0) < recent_count * 0.7
                        ]

                        if other_experts:
                            # Select least-contributing expert (across all rounds)
                            other_experts.sort(
                                key=lambda code: contribution_counts_all.get(code, 0)
                            )
                            next_speaker = other_experts[0]

                            return {
                                "reason": f"ROTATION LIMIT: {persona_code} participated in "
                                f"{participation_rate:.0%} of recent {recent_round_limit} rounds "
                                f"(limit: {max_round_participation_rate:.0%}). Rotating to {next_speaker}.",
                                "next_speaker": next_speaker,
                                "prompt": "Provide a fresh perspective on the discussion so far. "
                                "Challenge points you disagree with or build on strong arguments.",
                            }

        # Rule 2 (UPDATED for parallel): Each expert 15-25% of total contributions (balanced)
        # With parallel rounds, we want MORE balanced distribution (not just "not dominating")
        contribution_counts = self._count_contributions(contributions)
        total_contributions = len(contributions)

        if total_contributions >= 10:  # Meaningful sample size
            expected_per_expert = 1.0 / len(personas)  # Equal distribution
            # min_threshold = expected_per_expert * 0.75  # 75% of expected (15% with 5 experts) - TODO: use for undercontribution check
            max_threshold = expected_per_expert * 1.5  # 150% of expected (30% with 5 experts)

            for persona_code, count in contribution_counts.items():
                contribution_ratio = count / total_contributions

                # Check if expert is contributing too much (dominance)
                if contribution_ratio > max_threshold:
                    # This expert is dominating - exclude them from next round
                    other_experts = [
                        p.code for p in personas if contribution_counts.get(p.code, 0) < count * 0.7
                    ]

                    if other_experts:
                        # Select least-contributing expert
                        other_experts.sort(key=lambda code: contribution_counts.get(code, 0))
                        next_speaker = other_experts[0]

                        return {
                            "reason": f"BALANCE LIMIT: {persona_code} has {count}/{total_contributions} "
                            f"contributions ({contribution_ratio:.0%}), exceeding balanced threshold "
                            f"({max_threshold:.0%}). Rotating to {next_speaker} for balance.",
                            "next_speaker": next_speaker,
                            "prompt": "We haven't heard much from your perspective. What concerns or "
                            "opportunities do you see that haven't been discussed?",
                        }

        # Rule 3 (UPDATED for parallel): Every expert must contribute at least once per 3 rounds
        # With parallel rounds (avg 3-4 experts per round), this gives ~1 contribution per expert per 3 rounds
        if total_contributions >= 9:  # After ~3 rounds
            contribution_counts = self._count_contributions(contributions)

            # Expected: ~1 contribution per expert per 3 rounds
            min_expected = total_contributions / (len(personas) * 3)

            silent_experts = [
                p.code for p in personas if contribution_counts.get(p.code, 0) < min_expected
            ]

            if silent_experts:
                # Select expert with fewest contributions
                silent_experts.sort(key=lambda code: contribution_counts.get(code, 0))
                next_speaker = silent_experts[0]

                return {
                    "reason": f"PARTICIPATION ENFORCEMENT: {next_speaker} has been relatively quiet. "
                    f"Ensuring all perspectives are heard.",
                    "next_speaker": next_speaker,
                    "prompt": "Your expertise is needed here. What are your thoughts on the points raised so far? "
                    "What risks or opportunities do you see from your perspective?",
                }

        return None  # No rotation override needed

    def _handle_impasse_intervention(
        self,
        state: DeliberationGraphState,
        guidance: dict[str, Any],
        round_number: int,
    ) -> FacilitatorDecision | None:
        """Handle impasse intervention when stalled disagreement is detected.

        Generates guidance for experts to resolve the impasse through:
        - Finding common ground on shared facts/goals
        - Disagree-and-commit (acknowledge disagreement, recommend majority view)
        - Conditional recommendations (if X then A, if Y then B)

        Args:
            state: Current deliberation state
            guidance: Facilitator guidance dict from stopping rules
            round_number: Current round number

        Returns:
            FacilitatorDecision with impasse resolution prompt, or None
        """
        issue = guidance.get("issue", "Experts stuck in disagreement")
        resolution_options = guidance.get("resolution_options", [])
        conflict_score = guidance.get("conflict_score", 0.0)
        novelty_score = guidance.get("novelty_score", 0.0)

        logger.info(
            f"⚠️ Impasse intervention triggered (round {round_number}): "
            f"conflict={conflict_score:.2f}, novelty={novelty_score:.2f}"
        )

        # Build impasse resolution prompt for experts
        resolution_prompt = (
            "We've been discussing this for several rounds without new progress. "
            "Let's move toward resolution:\n\n"
        )

        if resolution_options:
            resolution_prompt += "Consider one of these approaches:\n"
            for i, option in enumerate(resolution_options, 1):
                resolution_prompt += f"{i}. {option}\n"
            resolution_prompt += "\n"

        resolution_prompt += (
            "Focus on: What can we agree on? What's the strongest argument "
            "for the majority position? Are there conditions under which "
            "the minority view would be preferred?"
        )

        return FacilitatorDecision(
            action="continue",
            reasoning=f"Impasse detected: {issue}. Guiding toward resolution.",
            speaker_prompt=resolution_prompt,
            # In parallel architecture, all experts will see this guidance
            next_speaker=None,  # Let all experts respond with resolution focus
        )

    async def decide_next_action(
        self, state: DeliberationGraphState, round_number: int, max_rounds: int
    ) -> tuple[FacilitatorDecision, LLMResponse | None]:
        """Decide what should happen next in the deliberation.

        Args:
            state: Current deliberation state (v2 graph state)
            round_number: Current round number (1-indexed)
            max_rounds: Maximum rounds allowed based on complexity

        Returns:
            Tuple of (decision, llm_response)
        """
        logger.info(f"Facilitator deciding next action for round {round_number}/{max_rounds}")

        # Check for impasse intervention guidance (from stopping rules)
        facilitator_guidance = state.get("facilitator_guidance")
        if facilitator_guidance and facilitator_guidance.get("type") == "impasse_intervention":
            impasse_decision = self._handle_impasse_intervention(
                state, facilitator_guidance, round_number
            )
            if impasse_decision:
                return impasse_decision, None

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

        # Issue #5 fix: Check rotation limits BEFORE moderator check
        # This ensures hard rotation rules always take precedence
        rotation_override = self._check_rotation_limits(state)

        if rotation_override:
            logger.info(f"🔄 Rotation override: {rotation_override['reason']}")

            return (
                FacilitatorDecision(
                    action="continue",
                    reasoning=rotation_override["reason"],
                    next_speaker=rotation_override["next_speaker"],
                    speaker_prompt=rotation_override["prompt"],
                ),
                None,  # Skip LLM call, use rule-based override
            )

        # TARGETED MODERATOR: Check for premature consensus BEFORE round 3 only
        # Triggers contrarian moderator to challenge groupthink in early rounds
        moderator_trigger = self._should_trigger_moderator(state, round_number)
        if moderator_trigger:
            logger.info(
                f"🎭 Auto-triggering {moderator_trigger['type']} moderator (premature consensus)"
            )
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
        phase = state.get("phase", "discussion")
        phase_objectives = self._get_phase_objectives(phase, round_number, max_rounds)

        # Compute contribution statistics for rotation guidance
        contribution_counts: dict[str, int] = {}
        last_speakers: list[str] = []
        contributions = state.get("contributions", [])
        personas = state.get("personas", [])

        if contributions:
            # Count contributions per persona
            for contrib in contributions:
                persona_code = contrib.persona_code
                contribution_counts[persona_code] = contribution_counts.get(persona_code, 0) + 1

            # Get last N speakers (most recent last)
            last_speakers = [c.persona_code for c in contributions[-5:]]

        # Get metrics from state for data-driven decisions
        metrics = state.get("metrics")

        # Compose facilitator prompt with rotation guidance and metrics
        system_prompt = compose_facilitator_prompt(
            current_phase=phase,
            discussion_history=discussion_history,
            phase_objectives=phase_objectives,
            contribution_counts=contribution_counts if contribution_counts else None,
            last_speakers=last_speakers if last_speakers else None,
            metrics=metrics,
            round_number=round_number,
        )

        # Build user message
        user_message = f"""Current round: {round_number} of {max_rounds}
Total contributions so far: {len(contributions)}
Personas participating: {", ".join([p.code for p in personas])}

Analyze the discussion and decide the next action."""

        # Use new helper method instead of manual PromptRequest creation
        response = await self._create_and_call_prompt(
            system=system_prompt,
            user_message=user_message,
            phase="facilitator_decision",
            prefill="<thinking>",  # Force character consistency and proper XML structure
            temperature=1.0,
            max_tokens=800,
        )

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

        # CRITICAL FIX: Save facilitator decision to database (Phase 1.3)
        try:
            from bo1.state.repositories import contribution_repository

            session_id = state.get("session_id", "unknown")
            sub_problem_index = state.get("sub_problem_index")
            user_id = state.get("user_id")

            contribution_repository.save_facilitator_decision(
                session_id=session_id,
                round_number=round_number,
                action=decision.action,
                reasoning=decision.reasoning,
                next_speaker=decision.next_speaker,
                moderator_type=decision.moderator_type,
                research_query=decision.research_query,
                sub_problem_index=sub_problem_index,
                user_id=user_id,  # Pass user_id for RLS compliance
            )
            logger.debug(f"Saved facilitator decision to database: action={decision.action}")
        except Exception as e:
            # Log error but don't block facilitation
            logger.error(f"Failed to save facilitator decision to database: {e}")

        return decision, response

    def _format_discussion_history(self, state: DeliberationGraphState) -> str:
        """Format discussion history for facilitator context."""
        return format_discussion_history(state, style="compact")

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
        state: DeliberationGraphState,
        votes: list[Any],
        vote_aggregation: Any,
    ) -> tuple[str, LLMResponse]:
        """Synthesize the full deliberation into a comprehensive report.

        Args:
            state: Current deliberation state (v2 graph state)
            votes: List of Vote objects
            vote_aggregation: VoteAggregation object

        Returns:
            Tuple of (synthesis_report, LLMResponse)
        """
        from bo1.prompts import SYNTHESIS_PROMPT_TEMPLATE

        logger.info("Generating synthesis report")

        # Build full deliberation history
        all_contributions_and_votes = self._format_full_deliberation(state, votes)

        # Compose synthesis prompt
        problem = state.get("problem")
        synthesis_prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
            problem_statement=problem.description if problem else "",
            all_contributions_and_votes=all_contributions_and_votes,
        )

        # Use new helper method instead of manual PromptRequest creation
        response = await self._create_and_call_prompt(
            system=synthesis_prompt,
            user_message="Generate the comprehensive synthesis report.",
            phase="synthesis",
            temperature=0.7,
            max_tokens=4096,
        )

        # Use new extract_xml_tag_with_fallback utility
        synthesis_report = extract_xml_tag_with_fallback(
            response.content,
            "synthesis_report",
            logger=logger,
            fallback_to_full=True,
            context="synthesis response",
        )

        logger.info(f"Generated synthesis report ({len(synthesis_report)} chars)")

        return synthesis_report, response

    def _format_full_deliberation(self, state: DeliberationGraphState, votes: list[Any]) -> str:
        """Format full deliberation history including contributions and votes.

        Args:
            state: Current deliberation state (v2 graph state)
            votes: List of Vote objects

        Returns:
            Formatted string
        """
        lines = []

        # Add all contributions
        lines.append("DELIBERATION HISTORY:")
        lines.append("")
        lines.append(self._format_discussion_history(state))

        # Add recommendations
        lines.append("FINAL RECOMMENDATIONS:")
        lines.append("")

        for vote in votes:
            lines.append(f"--- {vote.persona_name} ---")
            lines.append(f"Recommendation: {vote.recommendation}")
            lines.append(f"Reasoning: {vote.reasoning}")
            if vote.conditions:
                lines.append(f"Conditions: {', '.join(vote.conditions)}")
            lines.append("")

        return "\n".join(lines)

    async def validate_synthesis_quality(
        self,
        synthesis_report: str,
        state: DeliberationGraphState,
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

        # Collect recommendations with conditions (since we no longer have decision enum)
        recommendations_with_conditions = [v for v in votes if v.conditions]
        # Low confidence recommendations might indicate dissent/uncertainty
        low_confidence_recommendations = [v for v in votes if v.confidence < 0.6]

        # Format for validation
        dissenting_summary = "\n".join(
            [f"- {v.persona_name}: {v.reasoning[:200]}..." for v in low_confidence_recommendations]
        )
        conditional_summary = "\n".join(
            [
                f"- {v.persona_name}: {', '.join(v.conditions[:3])}"
                for v in recommendations_with_conditions
            ]
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
1. Are all low-confidence views ({len(low_confidence_recommendations)}) included and explained?
2. Are critical conditions ({len([c for v in recommendations_with_conditions for c in v.conditions])}) clearly stated?
3. Is the recommendation specific and actionable (not vague)?
4. Are risks and implementation challenges addressed?

Output JSON only."""

        # Use new helper method instead of manual PromptRequest creation
        response = await self._create_and_call_prompt(
            system=system_prompt,
            user_message=user_message,
            phase="synthesis_validation",
            prefill="{",
            temperature=0.3,
            max_tokens=1000,
        )

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
            ErrorLogger.log_fallback(
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
        state: DeliberationGraphState,
        votes: list[Any],
    ) -> tuple[str, LLMResponse]:
        """Revise synthesis based on quality feedback.

        Args:
            original_synthesis: Original synthesis report
            feedback: Feedback from validation
            state: Deliberation state (v2 graph state)
            votes: List of votes

        Returns:
            Tuple of (revised_synthesis, LLMResponse)
        """
        logger.info("Revising synthesis based on feedback")

        system_prompt = """You are the Facilitator revising a synthesis report.

Your task: Improve the synthesis by addressing specific quality issues.

Output the revised <synthesis_report> with all required sections."""

        problem = state.get("problem")
        problem_description = problem.description if problem else ""
        user_message = f"""Revise this synthesis report to address the feedback:

<original_synthesis>
{original_synthesis}
</original_synthesis>

<quality_feedback>
{feedback}
</quality_feedback>

<problem_statement>
{problem_description}
</problem_statement>

Ensure the revised report:
1. Includes ALL dissenting views with substantive explanation
2. Clearly states ALL critical conditions
3. Provides specific, actionable recommendations
4. Addresses risks and implementation challenges

Output the complete revised <synthesis_report>...</synthesis_report>."""

        # Use new helper method instead of manual PromptRequest creation
        response = await self._create_and_call_prompt(
            system=system_prompt,
            user_message=user_message,
            phase="synthesis_revision",
            temperature=0.7,
            max_tokens=4096,
        )

        # Use new extract_xml_tag_with_fallback utility
        revised_synthesis = extract_xml_tag_with_fallback(
            response.content,
            "synthesis_report",
            logger=logger,
            fallback_to_full=True,
            context="revised synthesis response",
        )

        logger.info(f"Generated revised synthesis ({len(revised_synthesis)} chars)")

        return revised_synthesis, response
