"""Persona execution engine for LLM calls and response processing.

Handles the complete lifecycle of a persona contribution:
- LLM API calls with retry protection
- Response parsing and validation
- Meta-discussion detection and retry
- Database persistence
- Token usage and cost tracking
"""

import logging
from datetime import datetime
from typing import Any

from bo1.config import MODEL_BY_ROLE, resolve_model_alias
from bo1.constants import TokenLimits
from bo1.graph.state import DeliberationGraphState
from bo1.llm.broker import PromptBroker, PromptRequest, get_model_for_phase
from bo1.llm.client import ClaudeClient
from bo1.llm.response import LLMResponse
from bo1.llm.response_parser import ResponseParser
from bo1.models.state import ContributionMessage, ContributionType

logger = logging.getLogger(__name__)


class PersonaExecutor:
    """Executes persona contributions with LLM calls and response processing.

    Handles:
    - LLM API calls with retry protection via PromptBroker
    - Response parsing (thinking/contribution extraction)
    - Meta-discussion detection and retry logic
    - Database persistence of contributions
    - Token usage and cost calculation
    """

    def __init__(
        self,
        client: ClaudeClient | None = None,
        state: DeliberationGraphState | None = None,
    ) -> None:
        """Initialize the persona executor.

        Args:
            client: Optional ClaudeClient instance. If None, creates a new one.
            state: Optional deliberation state for database persistence.
        """
        self.client = client or ClaudeClient()
        self.state = state
        self.model_name = MODEL_BY_ROLE["persona"]
        self.model_id = resolve_model_alias(self.model_name)  # Full ID for pricing

    async def execute_persona_call(
        self,
        persona_profile: Any,  # PersonaProfile type
        system_prompt: str,
        user_message: str,
        round_number: int,
        contribution_type: ContributionType,
        round_config: dict[str, Any],
    ) -> tuple[ContributionMessage, LLMResponse]:
        """Execute a persona LLM call and return parsed contribution.

        Args:
            persona_profile: The persona profile to call
            system_prompt: System prompt for the LLM
            user_message: User message/directive
            round_number: Current round number (0-indexed)
            contribution_type: Type of contribution (INITIAL, RESPONSE, etc.)
            round_config: Round configuration (temperature, max_tokens, phase)

        Returns:
            Tuple of (contribution_message, llm_response) for metrics tracking

        Example:
            >>> executor = PersonaExecutor()
            >>> contrib, llm_resp = await executor.execute_persona_call(
            ...     persona_profile=persona,
            ...     system_prompt="You are an expert...",
            ...     user_message="Analyze this problem...",
            ...     round_number=0,
            ...     contribution_type=ContributionType.INITIAL,
            ...     round_config={"temperature": 1.0, "max_tokens": 4096, "phase": "exploration"}
            ... )
        """
        logger.debug(f"Calling persona: {persona_profile.display_name}")

        start_time = datetime.now()

        # Select model based on phase and round
        selected_model = get_model_for_phase("contribution", round_number=round_number + 1)

        # Create prompt request with retry protection
        broker = PromptBroker(client=self.client)
        request = PromptRequest(
            system=system_prompt,
            user_message=user_message,
            prefill=f"[{persona_profile.display_name}]\n\n<thinking>",  # Force character consistency
            model=selected_model,
            cache_system=True,  # Enable prompt caching for cost optimization
            temperature=round_config["temperature"],
            max_tokens=round_config["max_tokens"],
            phase="deliberation",
            agent_type=f"persona_{persona_profile.code}",
        )

        # Execute LLM call with retry protection
        llm_response_temp = await broker.call(request)

        # Prefill is already prepended by ClaudeClient
        response_text = llm_response_temp.content
        token_usage = llm_response_temp.token_usage
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Parse response (extract <thinking> and <contribution>)
        thinking, contribution = ResponseParser.parse_persona_response(response_text)

        # Validate response - check for meta-discussion (persona confusion)
        if ResponseParser.is_meta_discussion(contribution):
            logger.warning(
                f"⚠️ Meta-discussion detected from {persona_profile.display_name}, retrying with clarification"
            )

            # Retry with clarification
            (
                contribution,
                thinking,
                retry_token_usage,
                duration_ms,
            ) = await self._retry_with_clarification(
                broker=broker,
                system_prompt=system_prompt,
                user_message=user_message,
                persona_profile=persona_profile,
                selected_model=selected_model,
                round_config=round_config,
                start_time=start_time,
                original_token_usage=token_usage,
            )
            token_usage = retry_token_usage

        # Check for overlength contribution
        word_count = len(contribution.split())
        if word_count > TokenLimits.MAX_CONTRIBUTION_WORDS:
            logger.warning(
                f"⚠️ Overlength contribution from {persona_profile.display_name}: "
                f"{word_count} words (max {TokenLimits.MAX_CONTRIBUTION_WORDS})"
            )
            # Truncate at sentence boundary (cheaper than retry)
            contribution = ResponseParser.truncate_contribution(
                contribution, TokenLimits.MAX_CONTRIBUTION_WORDS
            )
            logger.info(
                f"Truncated {persona_profile.display_name} contribution to "
                f"{len(contribution.split())} words"
            )

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
            model=self.model_id,  # Track which model was used
        )

        # Create LLM response for metrics tracking
        llm_response = LLMResponse(
            content=response_text,
            model=self.model_id,
            token_usage=token_usage,
            duration_ms=duration_ms,
            phase="deliberation",
            agent_type=f"persona_{persona_profile.code}",
        )

        logger.debug(
            f"Persona {persona_profile.display_name} contributed "
            f"({contrib_msg.token_count} tokens, ${contrib_msg.cost:.4f})"
        )

        # Save to database
        await self._save_contribution_to_db(contrib_msg, persona_profile)

        return contrib_msg, llm_response

    async def _retry_with_clarification(
        self,
        broker: PromptBroker,
        system_prompt: str,
        user_message: str,
        persona_profile: Any,
        selected_model: str,
        round_config: dict[str, Any],
        start_time: datetime,
        original_token_usage: Any,
    ) -> tuple[str, str | None, Any, int]:
        """Retry LLM call with clarification to fix meta-discussion.

        Args:
            broker: PromptBroker instance
            system_prompt: Original system prompt
            user_message: Original user message
            persona_profile: Persona profile
            selected_model: Model to use
            round_config: Round configuration
            start_time: Original call start time
            original_token_usage: Token usage from original call

        Returns:
            Tuple of (contribution, thinking, token_usage, duration_ms)
        """
        # Add explicit clarification to user message
        clarification_msg = (
            f"{user_message}\n\n"
            "IMPORTANT: You ARE the expert. Do not ask questions about your role or how to respond. "
            "Engage directly with the problem statement above. Provide your expert analysis NOW."
        )

        request_retry = PromptRequest(
            system=system_prompt,
            user_message=clarification_msg,
            model=selected_model,
            cache_system=True,
            temperature=round_config["temperature"] + 0.1,  # Slightly higher temp
            max_tokens=round_config["max_tokens"],
            phase="deliberation",
            agent_type=f"persona_{persona_profile.code}_retry",
        )

        retry_response = await broker.call(request_retry)
        response_text = retry_response.content

        # Add retry tokens to total
        original_token_usage.input_tokens += retry_response.token_usage.input_tokens
        original_token_usage.output_tokens += retry_response.token_usage.output_tokens
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        thinking, contribution = ResponseParser.parse_persona_response(response_text)

        logger.info(f"Retry response from {persona_profile.display_name}: {contribution[:100]}...")

        return contribution, thinking, original_token_usage, duration_ms

    async def _save_contribution_to_db(
        self, contrib_msg: ContributionMessage, persona_profile: Any
    ) -> None:
        """Save contribution to database for analytics and recovery.

        Args:
            contrib_msg: Contribution message to save
            persona_profile: Persona profile

        Note:
            Errors are logged but don't block deliberation.
        """
        if not self.state:
            logger.debug("No state provided, skipping database save")
            return

        try:
            from bo1.state.repositories import contribution_repository

            session_id = self.state.get("session_id", "unknown")
            phase_name = self.state.get("phase", "unknown")

            # Extract enum value if DeliberationPhase
            if hasattr(phase_name, "value"):
                phase_name = phase_name.value

            contribution_repository.save_contribution(
                session_id=session_id,
                persona_code=persona_profile.code,
                content=contrib_msg.content,
                round_number=contrib_msg.round_number,
                phase=phase_name,
                cost=contrib_msg.cost or 0.0,
                tokens=contrib_msg.token_count or 0,
                model=self.model_id,
            )

            logger.debug(f"Saved contribution from {persona_profile.display_name} to database")

        except Exception as e:
            # Enhanced logging for debugging database save failures
            logger.error(
                f"Failed to save contribution to database: {e!r}, "
                f"type={type(e).__name__}, "
                f"session_id={session_id}, "
                f"persona_code={persona_profile.code}, "
                f"round_number={contrib_msg.round_number}"
            )
