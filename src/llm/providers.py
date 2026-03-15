"""
Concrete implementations of LLM providers.
"""

import logging
from typing import Any, Optional

import anthropic
import google.generativeai as genai
from openai import AsyncOpenAI

from src.llm.base import LLMMessage, LLMProvider, LLMResponse
from src.llm.exceptions import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
)
from src.llm.language_utils import apply_language_to_system_prompt

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider implementation with client pooling."""

    def __init__(
        self, api_key: str, model: Optional[str] = None, language: str = "en"
    ):
        """
        Initialize Claude provider with pooled client.

        Args:
            api_key: Anthropic API key
            model: Model name to use
            language: Language code for responses
        """
        super().__init__(api_key, model, language)
        self._client: anthropic.Optional[AsyncAnthropic] = None

    async def __aenter__(self) -> "ClaudeProvider":
        """
        Async context manager entry.

        Returns:
            Self for context manager usage
        """
        self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Async context manager exit with cleanup.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        if self._client is not None:
            await self._client.close()
            self._client = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        """
        Get or create the pooled client.

        Returns:
            AsyncAnthropic client instance

        Note:
            Creates client on first use if not initialized via context manager
        """
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    def get_default_model(self) -> str:
        """Get default Claude model."""
        return "claude-3-5-sonnet-20241022"

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "claude"

    async def generate_response(
        self,
        messages: list[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """
        Generate response using Claude API.

        Args:
            messages: Conversation messages
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            LLMResponse with generated content

        Raises:
            LLMProviderError: If generation fails
        """
        try:
            client = self._get_client()

            # Convert messages to Claude format
            claude_messages = []
            for msg in messages:
                if msg.role != "system":  # Claude handles system separately
                    claude_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })

            # Apply language instruction to system prompt
            final_system_prompt = apply_language_to_system_prompt(
                system_prompt, self.language
            )

            response = await client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=final_system_prompt if final_system_prompt else None,
                messages=claude_messages,
            )

            content = response.content[0].text if response.content else ""

            return LLMResponse(
                content=content,
                provider=self.get_provider_name(),
                model=self.model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                metadata={
                    "stop_reason": response.stop_reason,
                    "input_tokens": response.usage.input_tokens if response.usage else None,
                    "output_tokens": response.usage.output_tokens if response.usage else None,
                }
            )

        except anthropic.AuthenticationError as e:
            logger.error(f"Claude authentication error: {e}")
            raise LLMAuthenticationError(self.get_provider_name(), str(e), e)
        except anthropic.RateLimitError as e:
            logger.error(f"Claude rate limit error: {e}")
            raise LLMRateLimitError(self.get_provider_name(), str(e), e)
        except Exception as e:
            logger.error(f"Claude generation error: {e}")
            raise LLMProviderError(self.get_provider_name(), str(e), e)

    async def is_available(self) -> bool:
        """Check if Claude is available."""
        if not self.api_key:
            return False

        try:
            client = self._get_client()
            # Simple test to verify API key works
            await client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception as e:
            logger.debug(f"Claude availability check failed: {e}")
            return False


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation with client pooling."""

    def __init__(
        self, api_key: str, model: Optional[str] = None, language: str = "en"
    ):
        """
        Initialize Gemini provider with configuration.

        Args:
            api_key: Google AI API key
            model: Model name to use
            language: Language code for responses
        """
        super().__init__(api_key, model, language)
        self._configured = False
        self._model_cache: dict[str, genai.GenerativeModel] = {}

    async def __aenter__(self) -> "GeminiProvider":
        """
        Async context manager entry.

        Returns:
            Self for context manager usage
        """
        self._configure()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Async context manager exit with cleanup.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        self._model_cache.clear()
        self._configured = False

    def _configure(self) -> None:
        """
        Configure Gemini API with API key.

        Note:
            Only configures once per instance to avoid redundant calls
        """
        if not self._configured:
            genai.configure(api_key=self.api_key)
            self._configured = True

    def _get_model(self, temperature: float, max_tokens: int) -> genai.GenerativeModel:
        """
        Get or create cached model instance.

        Args:
            temperature: Sampling temperature
            max_tokens: Maximum output tokens

        Returns:
            GenerativeModel instance with specified configuration

        Note:
            Models are cached by configuration to avoid repeated instantiation
        """
        self._configure()

        # Create cache key from configuration
        cache_key = f"{self.model}_{temperature}_{max_tokens}"

        if cache_key not in self._model_cache:
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            self._model_cache[cache_key] = genai.GenerativeModel(
                model_name=self.model,
                generation_config=generation_config
            )

        return self._model_cache[cache_key]

    def get_default_model(self) -> str:
        """Get default Gemini model."""
        return "gemini-1.5-pro"

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "gemini"

    async def generate_response(
        self,
        messages: list[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """
        Generate response using Gemini API.

        Args:
            messages: Conversation messages
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            LLMResponse with generated content

        Raises:
            LLMProviderError: If generation fails
        """
        try:
            model = self._get_model(temperature, max_tokens)

            # Apply language instruction to system prompt
            final_system_prompt = apply_language_to_system_prompt(
                system_prompt, self.language
            )

            # Build full prompt with system and messages
            full_prompt = ""
            if final_system_prompt:
                full_prompt += f"System: {final_system_prompt}\n\n"

            # Add conversation history
            for msg in messages:
                role_label = "User" if msg.role == "user" else "Assistant"
                full_prompt += f"{role_label}: {msg.content}\n\n"

            full_prompt += "Assistant:"

            response = await model.generate_content_async(full_prompt)

            content = response.text if hasattr(response, 'text') else ""

            return LLMResponse(
                content=content,
                provider=self.get_provider_name(),
                model=self.model,
                tokens_used=None,  # Gemini doesn't always provide token counts
                metadata={
                    "candidates": len(response.candidates) if hasattr(response, 'candidates') else 0,
                }
            )

        except Exception as e:
            # Check for specific error types
            error_msg = str(e).lower()
            if "api key" in error_msg or "authentication" in error_msg or "unauthorized" in error_msg:
                logger.error(f"Gemini authentication error: {e}")
                raise LLMAuthenticationError(self.get_provider_name(), str(e), e)
            elif "quota" in error_msg or "rate limit" in error_msg:
                logger.error(f"Gemini rate limit error: {e}")
                raise LLMRateLimitError(self.get_provider_name(), str(e), e)
            else:
                logger.error(f"Gemini generation error: {e}")
                raise LLMProviderError(self.get_provider_name(), str(e), e)

    async def is_available(self) -> bool:
        """Check if Gemini is available."""
        if not self.api_key:
            return False

        try:
            model = self._get_model(temperature=0.7, max_tokens=10)
            await model.generate_content_async("test")
            return True
        except Exception as e:
            logger.debug(f"Gemini availability check failed: {e}")
            return False


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation with client pooling."""

    def __init__(
        self, api_key: str, model: Optional[str] = None, language: str = "en"
    ):
        """
        Initialize OpenAI provider with pooled client.

        Args:
            api_key: OpenAI API key
            model: Model name to use
            language: Language code for responses
        """
        super().__init__(api_key, model, language)
        self._client: Optional[AsyncOpenAI] = None

    async def __aenter__(self) -> "OpenAIProvider":
        """
        Async context manager entry.

        Returns:
            Self for context manager usage
        """
        self._client = AsyncOpenAI(api_key=self.api_key)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Async context manager exit with cleanup.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        if self._client is not None:
            await self._client.close()
            self._client = None

    def _get_client(self) -> AsyncOpenAI:
        """
        Get or create the pooled client.

        Returns:
            AsyncOpenAI client instance

        Note:
            Creates client on first use if not initialized via context manager
        """
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    def get_default_model(self) -> str:
        """Get default OpenAI model."""
        return "gpt-4o"

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "openai"

    async def generate_response(
        self,
        messages: list[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """
        Generate response using OpenAI API.

        Args:
            messages: Conversation messages
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            LLMResponse with generated content

        Raises:
            LLMProviderError: If generation fails
        """
        try:
            client = self._get_client()

            # Convert messages to OpenAI format
            openai_messages = []

            # Apply language instruction to system prompt
            final_system_prompt = apply_language_to_system_prompt(
                system_prompt, self.language
            )

            if final_system_prompt:
                openai_messages.append({
                    "role": "system",
                    "content": final_system_prompt
                })

            # Add conversation messages
            for msg in messages:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

            response = await client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content if response.choices else ""

            return LLMResponse(
                content=content or "",
                provider=self.get_provider_name(),
                model=self.model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                metadata={
                    "finish_reason": response.choices[0].finish_reason if response.choices else None,
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                }
            )

        except Exception as e:
            # Check for specific error types
            error_msg = str(e).lower()
            if "api key" in error_msg or "authentication" in error_msg or "unauthorized" in error_msg:
                logger.error(f"OpenAI authentication error: {e}")
                raise LLMAuthenticationError(self.get_provider_name(), str(e), e)
            elif "rate limit" in error_msg or "quota" in error_msg:
                logger.error(f"OpenAI rate limit error: {e}")
                raise LLMRateLimitError(self.get_provider_name(), str(e), e)
            else:
                logger.error(f"OpenAI generation error: {e}")
                raise LLMProviderError(self.get_provider_name(), str(e), e)

    async def is_available(self) -> bool:
        """Check if OpenAI is available."""
        if not self.api_key:
            return False

        try:
            client = self._get_client()
            await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10,
            )
            return True
        except Exception as e:
            logger.debug(f"OpenAI availability check failed: {e}")
            return False
