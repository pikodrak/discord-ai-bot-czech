"""
LLM client module for multi-provider AI integration.

This module provides a unified interface for interacting with multiple LLM providers
(Claude, Gemini, OpenAI) with automatic fallback and retry logic.
"""

from src.llm.base import LLMMessage, LLMResponse
from src.llm.client import LLMClient
from src.llm.client_enhanced import EnhancedLLMClient
from src.llm.providers import LLMProvider, ClaudeProvider, GeminiProvider, OpenAIProvider
from src.llm.exceptions import (
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMAllProvidersFailedError,
)
from src.llm.factory import create_llm_client, get_default_system_prompt
from src.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
)
from src.llm.retry_strategy import (
    RetryHandler,
    RetryConfig,
    RetryStrategy,
)

__all__ = [
    "LLMClient",
    "EnhancedLLMClient",
    "LLMMessage",
    "LLMResponse",
    "LLMProvider",
    "ClaudeProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "LLMError",
    "LLMProviderError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    "LLMAllProvidersFailedError",
    "create_llm_client",
    "get_default_system_prompt",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerError",
    "CircuitState",
    "RetryHandler",
    "RetryConfig",
    "RetryStrategy",
]
