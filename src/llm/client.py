"""
Unified LLM client with multi-provider fallback support.
"""

import asyncio
import logging
from typing import Optional

from src.llm.base import LLMMessage, LLMProvider, LLMResponse
from src.llm.providers import ClaudeProvider, GeminiProvider, OpenAIProvider
from src.llm.exceptions import (
    LLMAllProvidersFailedError,
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
)

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM client with automatic fallback between providers.

    This client manages multiple LLM providers and automatically falls back
    to alternative providers if the primary one fails.
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        language: str = "en",
    ):
        """
        Initialize LLM client with provider credentials.

        Args:
            anthropic_api_key: Anthropic API key for Claude
            google_api_key: Google API key for Gemini
            openai_api_key: OpenAI API key
            max_retries: Maximum retry attempts per provider
            retry_delay: Delay between retries in seconds
            language: Language code for responses (e.g., 'en', 'cs', 'de')
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.language = language
        self.providers: list[LLMProvider] = []

        # Initialize providers in priority order: Claude -> Gemini -> OpenAI
        if anthropic_api_key:
            try:
                self.providers.append(ClaudeProvider(anthropic_api_key, language=language))
                logger.info(f"Initialized Claude provider with language: {language}")
            except Exception as e:
                logger.warning(f"Failed to initialize Claude provider: {e}")

        if google_api_key:
            try:
                self.providers.append(GeminiProvider(google_api_key, language=language))
                logger.info(f"Initialized Gemini provider with language: {language}")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini provider: {e}")

        if openai_api_key:
            try:
                self.providers.append(OpenAIProvider(openai_api_key, language=language))
                logger.info(f"Initialized OpenAI provider with language: {language}")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")

        if not self.providers:
            logger.error("No LLM providers available - at least one API key required")

    async def generate_response(
        self,
        messages: list[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """
        Generate a response using available LLM providers with fallback.

        Tries each provider in order until one succeeds. Implements retry logic
        for each provider before moving to the next one.

        Args:
            messages: Conversation messages
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse from the first successful provider

        Raises:
            LLMAllProvidersFailedError: If all providers fail
        """
        if not self.providers:
            raise LLMAllProvidersFailedError({
                "system": Exception("No LLM providers configured")
            })

        errors: dict[str, Exception] = {}

        for provider in self.providers:
            provider_name = provider.get_provider_name()
            logger.info(f"Attempting to generate response with {provider_name}")

            for attempt in range(self.max_retries):
                try:
                    response = await provider.generate_response(
                        messages=messages,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    logger.info(
                        f"Successfully generated response with {provider_name} "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    return response

                except LLMAuthenticationError as e:
                    # Authentication errors won't be fixed by retrying
                    logger.error(f"{provider_name} authentication failed: {e}")
                    errors[provider_name] = e
                    break

                except LLMRateLimitError as e:
                    logger.warning(
                        f"{provider_name} rate limit hit (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    errors[provider_name] = e

                    if attempt < self.max_retries - 1:
                        # Exponential backoff for rate limits
                        delay = self.retry_delay * (2 ** attempt)
                        logger.info(f"Waiting {delay}s before retry...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"{provider_name} max retries exceeded")
                        break

                except LLMProviderError as e:
                    logger.warning(
                        f"{provider_name} provider error (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    errors[provider_name] = e

                    if attempt < self.max_retries - 1:
                        logger.info(f"Waiting {self.retry_delay}s before retry...")
                        await asyncio.sleep(self.retry_delay)
                    else:
                        logger.error(f"{provider_name} max retries exceeded")
                        break

                except Exception as e:
                    logger.error(f"{provider_name} unexpected error: {e}")
                    errors[provider_name] = e
                    break

        # All providers failed
        logger.error("All LLM providers failed")
        raise LLMAllProvidersFailedError(errors)

    async def check_availability(self) -> dict[str, bool]:
        """
        Check availability of all configured providers.

        Returns:
            Dictionary mapping provider names to availability status
        """
        availability = {}

        for provider in self.providers:
            provider_name = provider.get_provider_name()
            try:
                is_available = await provider.is_available()
                availability[provider_name] = is_available
                logger.info(f"{provider_name} availability: {is_available}")
            except Exception as e:
                logger.error(f"Error checking {provider_name} availability: {e}")
                availability[provider_name] = False

        return availability

    def get_available_providers(self) -> list[str]:
        """
        Get list of configured provider names.

        Returns:
            List of provider names
        """
        return [provider.get_provider_name() for provider in self.providers]

    async def generate_simple_response(self, user_message: str) -> str:
        """
        Generate a simple response from a single user message.

        Convenience method for simple interactions.

        Args:
            user_message: User message content

        Returns:
            Generated response content as string

        Raises:
            LLMAllProvidersFailedError: If all providers fail
        """
        messages = [LLMMessage(role="user", content=user_message)]
        response = await self.generate_response(messages)
        return response.content
