"""Logging helpers for consistent log formatting across agents.

Provides standardized logging methods for common patterns like LLM calls,
extractions, fallbacks, and phase transitions.
"""

import logging
from typing import Any

from bo1.llm.response import LLMResponse


class LogHelper:
    """Standardized logging utilities for agents.

    Provides consistent log formats for:
    - LLM calls and responses
    - Extraction successes and failures
    - Fallback usage
    - Phase transitions
    - Decision logging
    """

    @staticmethod
    def log_llm_call(
        logger: logging.Logger,
        agent_type: str,
        phase: str,
        model: str,
        response: LLMResponse | None = None,
        context: str = "",
    ) -> None:
        """Log LLM call with standardized format.

        Args:
            logger: Logger instance
            agent_type: Type of agent making the call (e.g., "facilitator", "persona_maria")
            phase: Phase of deliberation (e.g., "voting", "deliberation")
            model: Model used (e.g., "sonnet", "haiku")
            response: Optional LLM response with metrics
            context: Additional context (e.g., "deciding next action")
        """
        context_str = f" ({context})" if context else ""
        if response:
            logger.info(
                f"[LLM] {agent_type}/{phase}{context_str}: {model} - "
                f"{response.total_tokens:,} tokens, ${response.cost_total:.4f}, "
                f"{response.duration_ms}ms"
            )
            if response.token_usage.cache_read_tokens > 0:
                cache_pct = (response.token_usage.cache_read_tokens / response.total_tokens) * 100
                logger.debug(
                    f"  Cache hit: {response.token_usage.cache_read_tokens:,} tokens ({cache_pct:.1f}%)"
                )
        else:
            logger.info(f"[LLM] {agent_type}/{phase}{context_str}: {model}")

    @staticmethod
    def log_extraction_success(
        logger: logging.Logger,
        tag: str,
        context: str = "",
        preview: str | None = None,
    ) -> None:
        """Log successful extraction with standardized format.

        Args:
            logger: Logger instance
            tag: Tag name that was extracted (e.g., "decision", "reasoning")
            context: Context for the extraction (e.g., "vote parsing")
            preview: Optional preview of extracted content (first 100 chars)
        """
        context_str = f" ({context})" if context else ""
        if preview:
            preview_str = f": {preview[:100]}..." if len(preview) > 100 else f": {preview}"
            logger.debug(f"✓ Extracted <{tag}>{context_str}{preview_str}")
        else:
            logger.debug(f"✓ Extracted <{tag}>{context_str}")

    @staticmethod
    def log_extraction_failure(
        logger: logging.Logger,
        tag: str,
        context: str = "",
        fallback: Any = None,
        response_preview: str | None = None,
    ) -> None:
        """Log failed extraction with fallback information.

        Args:
            logger: Logger instance
            tag: Tag name that failed to extract
            context: Context for the extraction
            fallback: Fallback value being used
            response_preview: Optional preview of response content (for debugging)
        """
        context_str = f" ({context})" if context else ""
        fallback_str = f". Using fallback: {fallback}" if fallback is not None else ""
        logger.warning(f"⚠️ FALLBACK: Could not extract <{tag}>{context_str}{fallback_str}")

        if response_preview:
            logger.debug(f"  Response preview: {response_preview[:200]}...")

    @staticmethod
    def log_fallback_used(
        logger: logging.Logger,
        operation: str,
        reason: str,
        fallback_action: str,
        error: Exception | None = None,
    ) -> None:
        """Log when a fallback mechanism is triggered.

        Args:
            logger: Logger instance
            operation: Operation that failed (e.g., "AI vote aggregation")
            reason: Reason for fallback (e.g., "JSON parsing failed")
            fallback_action: What fallback action is being taken
            error: Optional exception that triggered the fallback
        """
        error_str = f" Error: {error}" if error else ""
        logger.warning(
            f"⚠️ FALLBACK: {operation} FAILED - {reason}.{error_str} "
            f"Falling back to: {fallback_action}"
        )

    @staticmethod
    def log_phase_transition(
        logger: logging.Logger,
        from_phase: str,
        to_phase: str,
        trigger: str = "",
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """Log phase transition with standardized format.

        Args:
            logger: Logger instance
            from_phase: Phase transitioning from
            to_phase: Phase transitioning to
            trigger: What triggered the transition (e.g., "facilitator decision")
            metrics: Optional metrics at time of transition
        """
        trigger_str = f" (trigger: {trigger})" if trigger else ""
        logger.info(f"🔄 PHASE TRANSITION: {from_phase} → {to_phase}{trigger_str}")

        if metrics:
            for key, value in metrics.items():
                if isinstance(value, float):
                    logger.debug(f"  {key}: {value:.2f}")
                else:
                    logger.debug(f"  {key}: {value}")

    @staticmethod
    def log_decision(
        logger: logging.Logger,
        agent_type: str,
        decision: str,
        reasoning: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log agent decision with standardized format.

        Args:
            logger: Logger instance
            agent_type: Type of agent making decision (e.g., "facilitator", "moderator")
            decision: The decision made (e.g., "continue", "vote", "intervene")
            reasoning: Optional reasoning for the decision (truncated if long)
            details: Optional additional details (e.g., next_speaker, moderator_type)
        """
        logger.info(f"[DECISION] {agent_type}: {decision}")

        if reasoning:
            reasoning_preview = reasoning[:200] + "..." if len(reasoning) > 200 else reasoning
            logger.debug(f"  Reasoning: {reasoning_preview}")

        if details:
            for key, value in details.items():
                if value is not None:
                    logger.info(f"  {key}: {value}")

    @staticmethod
    def log_persona_contribution(
        logger: logging.Logger,
        persona_name: str,
        persona_code: str,
        round_number: int,
        token_count: int,
        cost: float,
        contribution_preview: str | None = None,
    ) -> None:
        """Log persona contribution with standardized format.

        Args:
            logger: Logger instance
            persona_name: Display name of persona
            persona_code: Persona code
            round_number: Current round number
            token_count: Tokens used
            cost: Cost in USD
            contribution_preview: Optional preview of contribution content
        """
        logger.info(
            f"[Round {round_number}] {persona_name} ({persona_code}): "
            f"{token_count:,} tokens, ${cost:.4f}"
        )

        if contribution_preview:
            preview = (
                contribution_preview[:150] + "..."
                if len(contribution_preview) > 150
                else contribution_preview
            )
            logger.debug(f"  Preview: {preview}")

    @staticmethod
    def log_vote_collected(
        logger: logging.Logger,
        persona_name: str,
        decision: str,
        confidence: float,
        conditions: list[str] | None = None,
    ) -> None:
        """Log vote collection with standardized format.

        Args:
            logger: Logger instance
            persona_name: Name of persona voting
            decision: Vote decision (e.g., "approve", "reject")
            confidence: Confidence level (0-1)
            conditions: Optional list of conditions
        """
        logger.info(f"[VOTE] {persona_name}: {decision} (confidence: {confidence:.2f})")

        if conditions and len(conditions) > 0:
            logger.debug(f"  Conditions: {', '.join(conditions[:3])}")

    @staticmethod
    def log_research_needed(
        logger: logging.Logger,
        query: str,
        reason: str,
        trigger_persona: str | None = None,
    ) -> None:
        """Log when research/information gathering is needed.

        Args:
            logger: Logger instance
            query: Research query or information needed
            reason: Why research is needed
            trigger_persona: Optional persona that triggered the need
        """
        persona_str = f" (triggered by {trigger_persona})" if trigger_persona else ""
        logger.info(f"🔍 RESEARCH NEEDED{persona_str}: {query[:100]}...")
        logger.debug(f"  Reason: {reason}")

    @staticmethod
    def log_moderator_triggered(
        logger: logging.Logger,
        moderator_type: str,
        trigger_reason: str,
        round_number: int,
    ) -> None:
        """Log moderator intervention trigger.

        Args:
            logger: Logger instance
            moderator_type: Type of moderator (e.g., "contrarian", "skeptic")
            trigger_reason: Why moderator was triggered
            round_number: Current round number
        """
        logger.info(f"🎭 MODERATOR TRIGGERED (Round {round_number}): {moderator_type}")
        logger.debug(f"  Reason: {trigger_reason}")

    @staticmethod
    def log_consensus_metrics(
        logger: logging.Logger,
        round_number: int,
        max_rounds: int,
        convergence: float,
        novelty: float,
        conflict: float,
        should_stop: bool = False,
        stop_reason: str | None = None,
    ) -> None:
        """Log consensus/convergence metrics.

        Args:
            logger: Logger instance
            round_number: Current round
            max_rounds: Maximum rounds
            convergence: Convergence score (0-1)
            novelty: Novelty score (0-1)
            conflict: Conflict score (0-1)
            should_stop: Whether early stop is recommended
            stop_reason: Optional reason for early stop
        """
        logger.info(f"[METRICS] Round {round_number}/{max_rounds}")
        logger.info(f"  Convergence: {convergence:.2f} (target: >0.85)")
        logger.info(f"  Novelty: {novelty:.2f} (target: <0.30 in late rounds)")
        logger.info(f"  Conflict: {conflict:.2f} (0=consensus, 1=deadlock)")

        if should_stop and stop_reason:
            logger.info(f"  🎯 Early stop recommended: {stop_reason}")
