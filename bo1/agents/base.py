"""Base agent class for all Board of One deliberation agents.

Provides common initialization, LLM interaction patterns, and error handling
to eliminate duplication across agent implementations.
"""

from abc import ABC, abstractmethod

from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.response import LLMResponse


class BaseAgent(ABC):
    """Abstract base class for all deliberation agents.

    Consolidates common patterns:
    - Broker initialization with dependency injection
    - Model selection via abstract method
    - Standardized LLM call pattern

    Subclasses must implement get_default_model() to specify their default model.
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

    @abstractmethod
    def get_default_model(self) -> str:
        """Return the default model name for this agent.

        Returns:
            Model name (e.g., "sonnet-4.5", "haiku-4.5")
        """
        pass

    async def _call_llm(self, request: PromptRequest) -> LLMResponse:
        """Call LLM via broker with standardized error handling.

        Args:
            request: PromptRequest to execute

        Returns:
            LLMResponse from the model

        Raises:
            Any exceptions from the broker.call() method
        """
        return await self.broker.call(request)

    async def _create_and_call_prompt(
        self,
        system: str,
        user_message: str,
        phase: str,
        *,
        prefill: str = "",
        temperature: float = 1.0,
        max_tokens: int = 2048,
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
            temperature: LLM temperature (0.0-2.0, default 1.0)
            max_tokens: Maximum tokens in response (default 2048)
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
        return await self.broker.call(request)
