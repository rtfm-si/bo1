"""Base agent class for all Board of One deliberation agents.

Provides common initialization, LLM interaction patterns, and error handling
to eliminate duplication across agent implementations.
"""

from abc import ABC, abstractmethod

from bo1.config import TokenBudgets
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.response import LLMResponse
from bo1.llm.response_parser import ValidationConfig
from bo1.utils.error_logger import ErrorLogger
from bo1.utils.logging import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all deliberation agents.

    Consolidates common patterns:
    - Broker initialization with dependency injection
    - Model selection via abstract method
    - Standardized LLM call pattern
    - Cost tracking across all calls
    - Structured error logging

    Subclasses must implement get_default_model() to specify their default model.

    Attributes:
        broker: LLM broker for API calls
        model: Model name (alias or full ID)
        total_cost: Cumulative cost of all LLM calls made by this agent instance
        call_count: Number of LLM calls made by this agent instance
    """

    def __init__(
        self,
        broker: PromptBroker | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize base agent with broker and model.

        Args:
            broker: Optional PromptBroker instance. If None, creates a new one.
            model: Optional model name override. If None, uses get_default_model().
        """
        self.broker = broker or PromptBroker()
        self.model = model or self.get_default_model()
        self.total_cost = 0.0
        self.call_count = 0

    @abstractmethod
    def get_default_model(self) -> str:
        """Return the default model name for this agent.

        Returns:
            Model name (e.g., "sonnet-4.5", "haiku-4.5")
        """
        pass

    async def _call_llm(self, request: PromptRequest) -> LLMResponse:
        """Call LLM via broker with standardized error handling and cost tracking.

        Args:
            request: PromptRequest to execute

        Returns:
            LLMResponse from the model

        Raises:
            Any exceptions from the broker.call() method, logged with context
        """
        try:
            response = await self.broker.call(request)
            # Track costs and call count
            self.total_cost += response.cost_total
            self.call_count += 1
            return response
        except Exception as e:
            # Log error with structured context
            ErrorLogger.log_error_with_context(
                logger,
                e,
                "LLM call failed in agent",
                agent=self.__class__.__name__,
                model=self.model,
                phase=request.phase or "unknown",
                request_id=request.request_id,
            )
            raise

    async def _create_and_call_prompt(
        self,
        system: str,
        user_message: str,
        phase: str,
        *,
        prefill: str = "",
        temperature: float = 0.7,
        max_tokens: int = TokenBudgets.AGENT_BASE,
        cache_system: bool = True,
    ) -> LLMResponse:
        """Create PromptRequest and call LLM with standard pattern.

        Consolidates the common pattern of creating a PromptRequest and calling
        the broker, reducing duplication across agent implementations.

        Args:
            system: System prompt for the LLM
            user_message: User message/prompt
            phase: Phase name for cost tracking (e.g., "decomposition", "selection")
            prefill: Optional prefill text (e.g., "{" for JSON responses)
            temperature: LLM temperature (0.0-2.0, default 0.7)
            max_tokens: Maximum tokens in response (default TokenBudgets.AGENT_BASE)
            cache_system: Whether to cache system prompt (default True)

        Returns:
            LLMResponse from the model

        Examples:
            >>> response = await self._create_and_call_prompt(
            ...     system=SYSTEM_PROMPT,
            ...     user_message=user_input,
            ...     phase="decomposition",
            ...     prefill="{",
            ...     temperature=0.7,
            ... )
        """
        request = PromptRequest(
            system=system,
            user_message=user_message,
            model=self.model,
            prefill=prefill,
            cache_system=cache_system,
            phase=phase,
            agent_type=self.__class__.__name__,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # Use _call_llm for consistent error handling and cost tracking
        return await self._call_llm(request)

    def get_cost_stats(self) -> dict[str, float | int]:
        """Get cost statistics for this agent instance.

        Returns:
            Dictionary with total_cost, call_count, and avg_cost_per_call

        Examples:
            >>> agent = DecomposerAgent()
            >>> # ... make some LLM calls ...
            >>> stats = agent.get_cost_stats()
            >>> print(f"Total cost: ${stats['total_cost']:.4f}")
            >>> print(f"Average: ${stats['avg_cost_per_call']:.4f}")
        """
        avg_cost = self.total_cost / self.call_count if self.call_count > 0 else 0.0
        return {
            "total_cost": self.total_cost,
            "call_count": self.call_count,
            "avg_cost_per_call": avg_cost,
        }

    def reset_cost_tracking(self) -> None:
        """Reset cost and call count trackers.

        Useful when reusing an agent instance across multiple sessions.

        Examples:
            >>> agent = DecomposerAgent()
            >>> # ... use agent for session 1 ...
            >>> agent.reset_cost_tracking()
            >>> # ... use agent for session 2 ...
        """
        self.total_cost = 0.0
        self.call_count = 0

    async def _create_and_call_prompt_with_validation(
        self,
        system: str,
        user_message: str,
        phase: str,
        validation: ValidationConfig,
        *,
        prefill: str = "",
        temperature: float = 0.7,
        max_tokens: int = TokenBudgets.AGENT_BASE,
        cache_system: bool = True,
    ) -> LLMResponse:
        """Create PromptRequest and call LLM with XML validation and retry.

        Same as _create_and_call_prompt but validates response against required
        XML tags and retries if validation fails.

        Args:
            system: System prompt for the LLM
            user_message: User message/prompt
            phase: Phase name for cost tracking
            validation: ValidationConfig with required_tags, max_retries, strict
            prefill: Optional prefill text
            temperature: LLM temperature (0.0-2.0, default 0.7)
            max_tokens: Maximum tokens in response
            cache_system: Whether to cache system prompt (default True)

        Returns:
            LLMResponse from the model (with accumulated tokens if retry occurred)

        Raises:
            XMLValidationError: If strict=True and validation fails after retries

        Examples:
            >>> validation = ValidationConfig(required_tags=["action"], max_retries=1)
            >>> response = await self._create_and_call_prompt_with_validation(
            ...     system=SYSTEM_PROMPT,
            ...     user_message=user_input,
            ...     phase="facilitator_decision",
            ...     validation=validation,
            ...     prefill="<thinking>",
            ... )
        """
        request = PromptRequest(
            system=system,
            user_message=user_message,
            model=self.model,
            prefill=prefill,
            cache_system=cache_system,
            phase=phase,
            agent_type=self.__class__.__name__,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            response = await self.broker.call_with_validation(request, validation)
            # Track costs and call count
            self.total_cost += response.cost_total
            self.call_count += 1
            return response
        except Exception as e:
            # Log error with structured context
            ErrorLogger.log_error_with_context(
                logger,
                e,
                "LLM call with validation failed in agent",
                agent=self.__class__.__name__,
                model=self.model,
                phase=phase,
                request_id=request.request_id,
                required_tags=validation.required_tags,
            )
            raise
