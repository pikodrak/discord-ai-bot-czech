"""
Comprehensive tests for LLM provider implementations.

Tests all three providers (Claude, Gemini, OpenAI) for:
- Initialization and configuration
- Message generation with various parameters
- Error handling (authentication, rate limits, general errors)
- Availability checks
- Context manager usage
- Language support
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import anthropic
import google.generativeai as genai
from openai import AsyncOpenAI

from src.llm.providers import ClaudeProvider, GeminiProvider, OpenAIProvider
from src.llm.base import LLMMessage, LLMResponse
from src.llm.exceptions import (
    LLMProviderError,
    LLMAuthenticationError,
    LLMRateLimitError,
)


class TestClaudeProvider:
    """Test suite for ClaudeProvider."""

    @pytest.fixture
    def claude_provider(self):
        """Create a Claude provider instance."""
        return ClaudeProvider(api_key="test_key", model="claude-3-5-sonnet-20241022")

    def test_initialization(self, claude_provider):
        """Test Claude provider initialization."""
        assert claude_provider.api_key == "test_key"
        assert claude_provider.model == "claude-3-5-sonnet-20241022"
        assert claude_provider.language == "en"
        assert claude_provider.get_provider_name() == "claude"

    def test_initialization_with_language(self):
        """Test Claude provider initialization with custom language."""
        provider = ClaudeProvider(api_key="test_key", language="cs")
        assert provider.language == "cs"
        assert provider.model == provider.get_default_model()

    def test_default_model(self, claude_provider):
        """Test default model selection."""
        assert claude_provider.get_default_model() == "claude-3-5-sonnet-20241022"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager protocol."""
        provider = ClaudeProvider(api_key="test_key")
        
        async with provider as p:
            assert p._client is not None
            assert isinstance(p._client, anthropic.AsyncAnthropic)
        
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_generate_response_success(self, claude_provider):
        """Test successful response generation."""
        # Mock the Anthropic client
        mock_client = AsyncMock(spec=anthropic.AsyncAnthropic)
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.usage = Mock(total_tokens=100, input_tokens=20, output_tokens=80)
        mock_response.stop_reason = "end_turn"
        
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        claude_provider._client = mock_client
        
        messages = [LLMMessage(role="user", content="Hello")]
        response = await claude_provider.generate_response(
            messages=messages,
            system_prompt="You are helpful.",
            temperature=0.7,
            max_tokens=1000
        )
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Test response"
        assert response.provider == "claude"
        assert response.tokens_used == 100
        assert response.metadata["stop_reason"] == "end_turn"
        assert response.metadata["input_tokens"] == 20
        assert response.metadata["output_tokens"] == 80

    @pytest.mark.asyncio
    async def test_generate_response_with_language(self, claude_provider):
        """Test response generation with non-English language."""
        claude_provider.language = "cs"
        mock_client = AsyncMock(spec=anthropic.AsyncAnthropic)
        mock_response = Mock()
        mock_response.content = [Mock(text="Ahoj")]
        mock_response.usage = Mock(total_tokens=50, input_tokens=10, output_tokens=40)
        mock_response.stop_reason = "end_turn"
        
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        claude_provider._client = mock_client
        
        messages = [LLMMessage(role="user", content="Hello")]
        response = await claude_provider.generate_response(messages)
        
        # Verify language instruction was added to system prompt
        call_args = mock_client.messages.create.call_args
        assert "Czech" in call_args.kwargs["system"]

    @pytest.mark.asyncio
    async def test_generate_response_authentication_error(self, claude_provider):
        """Test authentication error handling."""
        mock_client = AsyncMock(spec=anthropic.AsyncAnthropic)
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.AuthenticationError("Invalid API key")
        )
        claude_provider._client = mock_client
        
        messages = [LLMMessage(role="user", content="Hello")]
        
        with pytest.raises(LLMAuthenticationError) as exc_info:
            await claude_provider.generate_response(messages)
        
        assert "claude" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_response_rate_limit_error(self, claude_provider):
        """Test rate limit error handling."""
        mock_client = AsyncMock(spec=anthropic.AsyncAnthropic)
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.RateLimitError("Rate limit exceeded")
        )
        claude_provider._client = mock_client
        
        messages = [LLMMessage(role="user", content="Hello")]
        
        with pytest.raises(LLMRateLimitError) as exc_info:
            await claude_provider.generate_response(messages)
        
        assert "claude" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_response_general_error(self, claude_provider):
        """Test general error handling."""
        mock_client = AsyncMock(spec=anthropic.AsyncAnthropic)
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("Unknown error")
        )
        claude_provider._client = mock_client
        
        messages = [LLMMessage(role="user", content="Hello")]
        
        with pytest.raises(LLMProviderError) as exc_info:
            await claude_provider.generate_response(messages)
        
        assert "claude" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_is_available_success(self, claude_provider):
        """Test availability check when API is accessible."""
        mock_client = AsyncMock(spec=anthropic.AsyncAnthropic)
        mock_response = Mock()
        mock_response.content = [Mock(text="test")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        claude_provider._client = mock_client
        
        available = await claude_provider.is_available()
        assert available is True

    @pytest.mark.asyncio
    async def test_is_available_failure(self, claude_provider):
        """Test availability check when API is not accessible."""
        mock_client = AsyncMock(spec=anthropic.AsyncAnthropic)
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("API error")
        )
        claude_provider._client = mock_client
        
        available = await claude_provider.is_available()
        assert available is False

    @pytest.mark.asyncio
    async def test_is_available_no_api_key(self):
        """Test availability check with no API key."""
        provider = ClaudeProvider(api_key="")
        available = await provider.is_available()
        assert available is False


class TestGeminiProvider:
    """Test suite for GeminiProvider."""

    @pytest.fixture
    def gemini_provider(self):
        """Create a Gemini provider instance."""
        return GeminiProvider(api_key="test_key", model="gemini-1.5-pro")

    def test_initialization(self, gemini_provider):
        """Test Gemini provider initialization."""
        assert gemini_provider.api_key == "test_key"
        assert gemini_provider.model == "gemini-1.5-pro"
        assert gemini_provider.language == "en"
        assert gemini_provider.get_provider_name() == "gemini"

    def test_default_model(self, gemini_provider):
        """Test default model selection."""
        assert gemini_provider.get_default_model() == "gemini-1.5-pro"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager protocol."""
        provider = GeminiProvider(api_key="test_key")
        
        with patch('google.generativeai.configure') as mock_configure:
            async with provider as p:
                assert p._configured is True
                mock_configure.assert_called_once_with(api_key="test_key")
            
            assert provider._configured is False
            assert len(provider._model_cache) == 0

    @pytest.mark.asyncio
    async def test_generate_response_success(self, gemini_provider):
        """Test successful response generation."""
        mock_model = AsyncMock()
        mock_response = Mock()
        mock_response.text = "Test response"
        mock_response.candidates = [Mock(), Mock()]
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        
        with patch.object(gemini_provider, '_get_model', return_value=mock_model):
            messages = [LLMMessage(role="user", content="Hello")]
            response = await gemini_provider.generate_response(
                messages=messages,
                system_prompt="You are helpful.",
                temperature=0.7,
                max_tokens=1000
            )
            
            assert isinstance(response, LLMResponse)
            assert response.content == "Test response"
            assert response.provider == "gemini"
            assert response.metadata["candidates"] == 2

    @pytest.mark.asyncio
    async def test_generate_response_authentication_error(self, gemini_provider):
        """Test authentication error handling."""
        mock_model = AsyncMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=Exception("API key is invalid")
        )
        
        with patch.object(gemini_provider, '_get_model', return_value=mock_model):
            messages = [LLMMessage(role="user", content="Hello")]
            
            with pytest.raises(LLMAuthenticationError) as exc_info:
                await gemini_provider.generate_response(messages)
            
            assert "gemini" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_response_rate_limit_error(self, gemini_provider):
        """Test rate limit error handling."""
        mock_model = AsyncMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )
        
        with patch.object(gemini_provider, '_get_model', return_value=mock_model):
            messages = [LLMMessage(role="user", content="Hello")]
            
            with pytest.raises(LLMRateLimitError) as exc_info:
                await gemini_provider.generate_response(messages)
            
            assert "gemini" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_model_caching(self, gemini_provider):
        """Test that models are cached by configuration."""
        with patch('google.generativeai.GenerativeModel') as mock_gen_model:
            mock_model = Mock()
            mock_gen_model.return_value = mock_model
            
            # First call should create the model
            model1 = gemini_provider._get_model(temperature=0.7, max_tokens=1000)
            assert mock_gen_model.call_count == 1
            
            # Second call with same params should return cached model
            model2 = gemini_provider._get_model(temperature=0.7, max_tokens=1000)
            assert mock_gen_model.call_count == 1  # Still 1, not 2
            assert model1 is model2
            
            # Call with different params should create new model
            model3 = gemini_provider._get_model(temperature=0.5, max_tokens=500)
            assert mock_gen_model.call_count == 2


class TestOpenAIProvider:
    """Test suite for OpenAIProvider."""

    @pytest.fixture
    def openai_provider(self):
        """Create an OpenAI provider instance."""
        return OpenAIProvider(api_key="test_key", model="gpt-4o")

    def test_initialization(self, openai_provider):
        """Test OpenAI provider initialization."""
        assert openai_provider.api_key == "test_key"
        assert openai_provider.model == "gpt-4o"
        assert openai_provider.language == "en"
        assert openai_provider.get_provider_name() == "openai"

    def test_default_model(self, openai_provider):
        """Test default model selection."""
        assert openai_provider.get_default_model() == "gpt-4o"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager protocol."""
        provider = OpenAIProvider(api_key="test_key")
        
        with patch('openai.AsyncOpenAI') as mock_openai_class:
            mock_client = AsyncMock()
            mock_openai_class.return_value = mock_client
            
            async with provider as p:
                assert p._client is not None
            
            mock_client.close.assert_called_once()
            assert provider._client is None

    @pytest.mark.asyncio
    async def test_generate_response_success(self, openai_provider):
        """Test successful response generation."""
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_choice = Mock()
        mock_choice.message.content = "Test response"
        mock_choice.finish_reason = "stop"
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = Mock(
            total_tokens=100,
            prompt_tokens=20,
            completion_tokens=80
        )
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        openai_provider._client = mock_client
        
        messages = [LLMMessage(role="user", content="Hello")]
        response = await openai_provider.generate_response(
            messages=messages,
            system_prompt="You are helpful.",
            temperature=0.7,
            max_tokens=1000
        )
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Test response"
        assert response.provider == "openai"
        assert response.tokens_used == 100
        assert response.metadata["finish_reason"] == "stop"
        assert response.metadata["prompt_tokens"] == 20
        assert response.metadata["completion_tokens"] == 80

    @pytest.mark.asyncio
    async def test_generate_response_authentication_error(self, openai_provider):
        """Test authentication error handling."""
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Invalid API key")
        )
        openai_provider._client = mock_client
        
        messages = [LLMMessage(role="user", content="Hello")]
        
        with pytest.raises(LLMAuthenticationError) as exc_info:
            await openai_provider.generate_response(messages)
        
        assert "openai" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_response_rate_limit_error(self, openai_provider):
        """Test rate limit error handling."""
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )
        openai_provider._client = mock_client
        
        messages = [LLMMessage(role="user", content="Hello")]
        
        with pytest.raises(LLMRateLimitError) as exc_info:
            await openai_provider.generate_response(messages)
        
        assert "openai" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_is_available_success(self, openai_provider):
        """Test availability check when API is accessible."""
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        openai_provider._client = mock_client
        
        available = await openai_provider.is_available()
        assert available is True

    @pytest.mark.asyncio
    async def test_is_available_failure(self, openai_provider):
        """Test availability check when API is not accessible."""
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )
        openai_provider._client = mock_client
        
        available = await openai_provider.is_available()
        assert available is False
