"""
Base interface for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """Represents a message in the conversation."""

    role: str  # "user", "assistant", or "system"
    content: str


@dataclass
class LLMResponse:
    """Represents a response from an LLM provider."""

    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    metadata: Optional[dict[str, Any]] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers with async context manager support."""

    def __init__(
        self, api_key: str, model: Optional[str] = None, language: str = "en"
    ):
        """
        Initialize LLM provider.

        Args:
            api_key: API key for the provider
            model: Model name to use (provider-specific)
            language: Language code for responses (e.g., 'en', 'cs', 'de')
        """
        self.api_key = api_key
        self.model = model or self.get_default_model()
        self.language = language

    @abstractmethod
    async def __aenter__(self) -> "LLMProvider":
        """
        Async context manager entry point.

        Implementations should initialize and return their client resources here.
        This ensures proper resource setup before use.

        Returns:
            Self for context manager usage

        Example:
            async with provider:
                response = await provider.generate_response(...)
        """
        pass

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Async context manager exit point.

        Implementations should clean up and close client resources here.
        This ensures proper resource cleanup even when exceptions occur.

        Args:
            exc_type: Exception type if raised during context
            exc_val: Exception value if raised during context
            exc_tb: Exception traceback if raised during context
        """
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """
        Get the default model name for this provider.

        Returns:
            Default model name
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this provider.

        Returns:
            Provider name
        """
        pass

    @abstractmethod
    async def generate_response(
        self,
        messages: list[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse object containing the generated response

        Raises:
            LLMProviderError: If the provider fails to generate a response
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the provider is available and properly configured.

        Returns:
            True if the provider is available, False otherwise
        """
        pass
