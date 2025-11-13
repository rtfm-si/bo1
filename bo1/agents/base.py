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
