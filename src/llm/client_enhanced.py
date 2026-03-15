"""
Enhanced unified LLM client with circuit breaker and advanced retry logic.

This module provides an improved version of the LLM client that integrates
circuit breaker pattern and sophisticated retry strategies for maximum reliability.
"""

import asyncio
import logging
from typing import Optional, Dict, List, Tuple

from src.llm.base import LLMMessage, LLMProvider, LLMResponse
from src.llm.providers import ClaudeProvider, GeminiProvider, OpenAIProvider
from src.llm.exceptions import (
    LLMAllProvidersFailedError,
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
)
from src.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerManager,
    CircuitState,
)
from src.llm.retry_strategy import (
    RetryHandler,
    RetryConfig,
    RetryStrategy,
)

logger = logging.getLogger(__name__)


class EnhancedLLMClient:
    """
    Enhanced unified LLM client with circuit breaker and advanced retry support.

    Features:
    - Multi-provider fallback (Claude -> Gemini -> OpenAI)
    - Circuit breaker per provider to prevent cascade failures
    - Advanced retry strategies with exponential backoff
    - Automatic Czech language support
    - Health monitoring and statistics
    - Proper resource lifecycle management via async context managers

    Usage:
        async with EnhancedLLMClient(
            anthropic_api_key="...",
            google_api_key="...",
        ) as client:
            response = await client.generate_response(messages)
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        enable_circuit_breaker: bool = True,
        circuit_failure_threshold: int = 5,
        circuit_timeout: float = 60.0,
        language: str = "en",
    ):
        """
        Initialize enhanced LLM client with provider credentials.

        Args:
            anthropic_api_key: Anthropic API key for Claude
            google_api_key: Google API key for Gemini
            openai_api_key: OpenAI API key
            max_retries: Maximum retry attempts per provider
            retry_delay: Base delay between retries in seconds
            enable_circuit_breaker: Whether to enable circuit breaker pattern
            circuit_failure_threshold: Failures before opening circuit
            circuit_timeout: Seconds to wait before attempting recovery
            language: Language code for responses (e.g., 'en', 'cs', 'de')
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_circuit_breaker = enable_circuit_breaker
        self.language = language
        self._initialized = False

        # Store API keys for deferred provider initialization
        self._anthropic_api_key = anthropic_api_key
        self._google_api_key = google_api_key
        self._openai_api_key = openai_api_key

        # Initialize providers with their names and instances
        self.providers: List[Tuple[str, LLMProvider]] = []

        # Initialize circuit breaker manager
        self.circuit_manager = CircuitBreakerManager()
        self.circuit_config = CircuitBreakerConfig(
            failure_threshold=circuit_failure_threshold,
            success_threshold=2,
            timeout=circuit_timeout,
            half_open_timeout=30.0,
        )

        # Initialize retry handler
        self.retry_handler = RetryHandler(
            RetryConfig(
                max_attempts=max_retries,
                base_delay=retry_delay,
                max_delay=60.0,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                jitter=True,
                jitter_range=0.1,
            )
        )

    async def __aenter__(self) -> "EnhancedLLMClient":
        """
        Async context manager entry.

        Initializes all provider resources with proper async context managers.

        Returns:
            Self for context manager usage

        Raises:
            LLMAllProvidersFailedError: If no providers can be initialized
        """
        await self._initialize_providers()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Async context manager exit.

        Cleans up all provider resources properly.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        await self._cleanup_providers()

    async def _initialize_providers(self) -> None:
        """
        Initialize all providers with their async context managers.

        Raises:
            LLMAllProvidersFailedError: If no providers can be initialized
        """
        if self._initialized:
            logger.warning("Providers already initialized, skipping")
            return

        # Initialize providers in priority order: Claude -> Gemini -> OpenAI
        if self._anthropic_api_key:
            try:
                provider = ClaudeProvider(self._anthropic_api_key, language=self.language)
                await provider.__aenter__()
                self.providers.append((provider.get_provider_name(), provider))
                logger.info(f"Initialized Claude provider with language: {self.language}")
            except Exception as e:
                logger.warning(f"Failed to initialize Claude provider: {e}")

        if self._google_api_key:
            try:
                provider = GeminiProvider(self._google_api_key, language=self.language)
                await provider.__aenter__()
                self.providers.append((provider.get_provider_name(), provider))
                logger.info(f"Initialized Gemini provider with language: {self.language}")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini provider: {e}")

        if self._openai_api_key:
            try:
                provider = OpenAIProvider(self._openai_api_key, language=self.language)
                await provider.__aenter__()
                self.providers.append((provider.get_provider_name(), provider))
                logger.info(f"Initialized OpenAI provider with language: {self.language}")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")

        if not self.providers:
            logger.error("No LLM providers available - at least one API key required")
            raise LLMAllProvidersFailedError({
                "initialization": Exception("No providers could be initialized")
            })

        self._initialized = True
        logger.info(f"Successfully initialized {len(self.providers)} provider(s)")

    async def _cleanup_providers(self) -> None:
        """
        Clean up all provider resources properly.

        Ensures all providers are closed even if some fail to close.
        """
        if not self._initialized:
            logger.debug("Providers not initialized, skipping cleanup")
            return

        errors = []

        for provider_name, provider in self.providers:
            try:
                await provider.__aexit__(None, None, None)
                logger.debug(f"Cleaned up {provider_name} provider")
            except Exception as e:
                logger.error(f"Error cleaning up {provider_name} provider: {e}")
                errors.append((provider_name, e))

        self.providers.clear()
        self._initialized = False

        if errors:
            logger.warning(f"Encountered {len(errors)} error(s) during cleanup")

    def _ensure_initialized(self) -> None:
        """
        Ensure providers are initialized before use.

        Raises:
            RuntimeError: If providers are not initialized
        """
        if not self._initialized:
            raise RuntimeError(
                "EnhancedLLMClient not initialized. "
                "Use 'async with EnhancedLLMClient(...) as client:' pattern "
                "or call await client._initialize_providers() manually."
            )

    async def _get_circuit_breaker(self, provider_name: str) -> Optional[CircuitBreaker]:
        """
        Get or create circuit breaker for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            CircuitBreaker instance or None if disabled
        """
        if not self.enable_circuit_breaker:
            return None

        return await self.circuit_manager.get_or_create(
            name=f"llm_{provider_name}",
            config=self.circuit_config,
            on_state_change=self._on_circuit_state_change,
        )

    def _on_circuit_state_change(
        self, old_state: CircuitState, new_state: CircuitState
    ) -> None:
        """
        Handle circuit breaker state changes.

        Args:
            old_state: Previous circuit state
            new_state: New circuit state
        """
        logger.warning(
            f"Circuit breaker state changed: {old_state.value} -> {new_state.value}"
        )

    async def _generate_with_provider(
        self,
        provider: LLMProvider,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """
        Generate response with a specific provider using circuit breaker.

        Args:
            provider: LLM provider instance
            messages: Conversation messages
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse from the provider

        Raises:
            CircuitBreakerError: If circuit is open
            LLMProviderError: If generation fails
        """
        provider_name = provider.get_provider_name()
        circuit = await self._get_circuit_breaker(provider_name)

        async def _generate():
            return await provider.generate_response(
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # Use circuit breaker if enabled
        if circuit:
            return await circuit.call(_generate)
        else:
            return await _generate()

    async def generate_response(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """
        Generate a response using available LLM providers with fallback.

        Tries each provider in order with retry logic and circuit breaker protection.
        Falls back to next provider if current one fails.

        Args:
            messages: Conversation messages
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse from the first successful provider

        Raises:
            RuntimeError: If client is not properly initialized
            LLMAllProvidersFailedError: If all providers fail
        """
        self._ensure_initialized()

        if not self.providers:
            raise LLMAllProvidersFailedError({
                "system": Exception("No LLM providers configured")
            })

        errors: Dict[str, Exception] = {}

        for provider_name, provider in self.providers:
            logger.info(f"Attempting to generate response with {provider_name}")

            try:
                # Use retry handler for this provider
                response = await self.retry_handler.execute_with_retry(
                    self._generate_with_provider,
                    provider=provider,
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    retry_on=(LLMRateLimitError, LLMProviderError),
                    do_not_retry_on=(LLMAuthenticationError,),
                    on_retry=lambda e, attempt: logger.warning(
                        f"{provider_name} retry {attempt + 1}/{self.max_retries}: {e}"
                    ),
                )

                logger.info(f"Successfully generated response with {provider_name}")
                return response

            except CircuitBreakerError as e:
                logger.warning(
                    f"{provider_name} circuit breaker is open, trying next provider"
                )
                errors[provider_name] = e
                continue

            except LLMAuthenticationError as e:
                logger.error(f"{provider_name} authentication failed: {e}")
                errors[provider_name] = e
                continue

            except (LLMRateLimitError, LLMProviderError) as e:
                logger.error(
                    f"{provider_name} failed after retries, trying next provider: {e}"
                )
                errors[provider_name] = e
                continue

            except Exception as e:
                logger.error(f"{provider_name} unexpected error: {e}")
                errors[provider_name] = e
                continue

        # All providers failed
        logger.error("All LLM providers failed")
        raise LLMAllProvidersFailedError(errors)

    async def check_availability(self) -> dict[str, bool]:
        """
        Check availability of all configured providers.

        Returns:
            Dictionary mapping provider names to availability status

        Raises:
            RuntimeError: If client is not properly initialized
        """
        self._ensure_initialized()

        availability = {}

        for provider_name, provider in self.providers:
            try:
                is_available = await provider.is_available()
                availability[provider_name] = is_available
                logger.info(f"{provider_name} availability: {is_available}")
            except Exception as e:
                logger.error(f"Error checking {provider_name} availability: {e}")
                availability[provider_name] = False

        return availability

    def get_available_providers(self) -> List[str]:
        """
        Get list of configured provider names.

        Returns:
            List of provider names
        """
        return [name for name, _ in self.providers]

    async def get_circuit_stats(self) -> dict[str, dict]:
        """
        Get circuit breaker statistics for all providers.

        Returns:
            Dictionary mapping provider names to their circuit stats
        """
        if not self.enable_circuit_breaker:
            return {}

        return await self.circuit_manager.get_all_stats()

    async def reset_circuits(self) -> None:
        """Reset all circuit breakers to closed state."""
        if self.enable_circuit_breaker:
            await self.circuit_manager.reset_all()
            logger.info("All circuit breakers reset")

    async def generate_simple_response(self, user_message: str) -> str:
        """
        Generate a simple response from a single user message.

        Convenience method for simple interactions.

        Args:
            user_message: User message content

        Returns:
            Generated response content as string

        Raises:
            RuntimeError: If client is not properly initialized
            LLMAllProvidersFailedError: If all providers fail
        """
        self._ensure_initialized()

        messages = [LLMMessage(role="user", content=user_message)]
        response = await self.generate_response(messages)
        return response.content

    async def health_check(self) -> dict[str, any]:
        """
        Perform comprehensive health check of the LLM client.

        Returns:
            Dictionary with health status information

        Raises:
            RuntimeError: If client is not properly initialized
        """
        self._ensure_initialized()

        availability = await self.check_availability()
        circuit_stats = await self.get_circuit_stats()

        healthy_providers = [name for name, is_avail in availability.items() if is_avail]

        return {
            "healthy": len(healthy_providers) > 0,
            "total_providers": len(self.providers),
            "healthy_providers": len(healthy_providers),
            "provider_availability": availability,
            "circuit_breaker_enabled": self.enable_circuit_breaker,
            "circuit_stats": circuit_stats,
            "retry_config": {
                "max_attempts": self.retry_handler.config.max_attempts,
                "strategy": self.retry_handler.config.strategy.value,
                "base_delay": self.retry_handler.config.base_delay,
            },
            "initialized": self._initialized,
        }
